"""IPInsight 글로벌 기술사업화 Agent OS — FastAPI 엔드포인트"""
from __future__ import annotations
import sys
import os
import uuid
import time as _t
from pathlib import Path
from typing import Any

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

# .env 자동 로드 (python-dotenv 있으면 사용, 없으면 직접 파싱)
def _load_dotenv():
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)
        return
    except ImportError:
        pass
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v

_load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.schemas import (
    StageRequest, PipelineRequest, FundingMatchRequest,
    IPAnalysisRequest, GapRequest, ExecutionRequest,
    ValuationRequest, RegulationRequest, RoadmapRequest,
    PCMLRequest,
    TokenRequest, TokenResponse, JobStatus, ErrorResponse,
)
from api.auth import require_auth, create_access_token, authenticate_user
from api.middleware import logging_middleware, get_metrics, post_auth_gate
from pipeline.phase_gate_pipeline import PhaseGatePipeline, STAGE_NAMES
from pipeline.funding_matcher import match_funding, recommend_funding_sequence
from api.report_builder import build_report
from agents import (
    IDFGenerator, PatentPortfolioStrategist, WhitespaceAnalyzer,
    PatentabilityAssessor,
    GlobalIPStrategist, CompetitiveMonitor, PortfolioOptimizer,
    TeamAssessor, UnitEconomicsAssessor, FundingPlanner, RegulatoryRoadmapAgent,
    IRDeckGenerator, ESGImpactAssessor, TradeSecretAnalyzer, EcosystemMatcher,
    ExitStrategyDesigner, PatentMaintenanceOptimizer,
    DemandSurveyGenerator, SMKGenerator,
)
from pipeline.roadmap_builder import build_roadmap
from api.routers.reports import router as reports_router

app = FastAPI(
    title="IPInsight IP Lifecycle × 글로벌 기술사업화 OS",
    description="G0~G10 전주기 + 4단계 IP 라이프사이클 통합 — WIPO·TRL·I-Corps·ARL·MRL·포트폴리오",
    version="2.0.0",
)

# CORS origins — ALLOWED_ORIGINS 환경변수로 운영 도메인 설정 가능
_cors_origins = [o.strip() for o in os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:8100,http://127.0.0.1:8100,http://localhost:3000,http://127.0.0.1:3000",
).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── 미들웨어 등록 순서: POST 인증 게이트 → 로깅 ─────────────
# FastAPI 미들웨어는 역순 실행 (마지막 등록이 첫 번째 실행)
# 로깅을 먼저 등록 → 인증 게이트를 나중 등록 → 인증이 로깅보다 먼저 실행
app.include_router(reports_router)

app.middleware("http")(logging_middleware)
app.middleware("http")(post_auth_gate)

# ── 전역 예외 핸들러 ──────────────────────────────────────────
@app.exception_handler(HTTPException)
async def http_exc_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(code=exc.status_code, message=str(exc.detail)).model_dump(),
    )

@app.exception_handler(Exception)
async def generic_exc_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(code=500, message="내부 서버 오류", detail=str(exc)).model_dump(),
    )

# ── 비동기 Job 저장소 (인메모리) ──────────────────────────────
_jobs: dict[str, dict[str, Any]] = {}


def _run_job(job_id: str, fn, *args, **kwargs):
    _jobs[job_id]["status"] = "running"
    try:
        result = fn(*args, **kwargs)
        _jobs[job_id].update({"status": "completed", "result": result, "completed_at": _t.time()})
    except Exception as e:
        _jobs[job_id].update({"status": "failed", "error": str(e), "completed_at": _t.time()})


_anthropic_status: dict = {"ok": None}  # None=미확인, True=정상, False=불가


def _check_pcml_scr_consistency(pcml_sr, scr_sr) -> dict:
    """PCML(구조 분석)과 SCR(신규성 스크리닝) 점수 괴리 감지."""
    pcml_score = pcml_sr.score if pcml_sr else 0
    scr_score = scr_sr.score if scr_sr else 0
    gap = abs(pcml_score - scr_score)
    pcml_gate = pcml_sr.gate if pcml_sr else ""
    scr_gate = scr_sr.gate if scr_sr else ""
    consistent = gap < 30 and not (pcml_gate == "Go" and scr_gate in ("G3", "G4"))
    reason = ""
    if not consistent:
        if gap >= 30:
            reason = (
                f"PCML({pcml_score:.0f}점·{pcml_gate})과 SCR({scr_score:.0f}점·{scr_gate}) "
                f"점수 차이 {gap:.0f}점. "
                "LLM 미사용 시 PCML은 구조 신뢰도만 평가(상한 60), "
                "SCR은 선행기술 부재 가정으로 보수적 판정합니다. "
                "크레딧 충전 후 LLM 재분석을 권장합니다."
            )
        if pcml_gate == "Go" and scr_gate in ("G3", "G4"):
            reason = (
                f"PCML은 IP 구조 완성도 기준 {pcml_gate}이지만 "
                f"SCR은 선행기술 대비 신규성 기준 {scr_gate}입니다. "
                "두 지표는 독립적이며, 사업화 진행에는 SCR Gate가 더 중요합니다."
            )
    return {
        "consistent": consistent,
        "pcml_score": pcml_score,
        "scr_score": scr_score,
        "gap": round(gap, 1),
        "llm_active": _anthropic_status.get("ok") is True,
        "reason": reason,
        "action": "" if consistent else "Anthropic 크레딧 충전 후 /ip/analyze-chain 재실행 권장" if not _anthropic_status.get("ok") else "SCR 전문가 검토 권장",
    }


def _check_anthropic() -> bool | str:
    """API 키 존재 + 실제 호출 가능 여부 캐시 (서버 기동 후 첫 요청에만 ping)."""
    if _anthropic_status["ok"] is not None:
        return _anthropic_status["ok"]
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        _anthropic_status["ok"] = False
        return False
    try:
        import anthropic as _ant
        _ant.Anthropic(api_key=key).messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=1,
            messages=[{"role": "user", "content": "ping"}]
        )
        _anthropic_status["ok"] = True
    except Exception as e:
        err = str(e)
        if "credit" in err.lower() or "balance" in err.lower():
            _anthropic_status["ok"] = "key_ok_no_credit"
        elif "invalid" in err.lower() or "authentication" in err.lower():
            _anthropic_status["ok"] = "invalid_key"
        else:
            _anthropic_status["ok"] = False
    return _anthropic_status["ok"]


@app.get("/health")
def health():
    import time as _time
    return {
        "status":  "ok",
        "service": "IPInsight Agent OS",
        "version": os.environ.get("APP_VERSION", "2.0.0"),
        "connectors": {
            "epo_ops":       bool(os.environ.get("EPO_CLIENT_ID")),
            "fda":           bool(os.environ.get("FDA_API_KEY")),
            "anthropic":     _check_anthropic(),
            "groq":          bool(os.environ.get("GROQ_API_KEY")),
            "ntis":          bool(os.environ.get("NTIS_API_KEY")),
            "slack":         bool(os.environ.get("SLACK_WEBHOOK_URL")),
            "kipris":        bool(os.environ.get("KIPRIS_API_KEY")),
            "google_patents": True,  # 키 불필요
        },
        "llm_backend":   "groq" if os.environ.get("GROQ_API_KEY") and _anthropic_status.get("ok") != True else ("anthropic" if _anthropic_status.get("ok") is True else "rule_fallback"),
        "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
    }


@app.get("/stages")
def list_stages():
    """G0~G10 단계 목록 조회"""
    return {
        "stages": [
            {"stage_num": k, "stage_id": f"G{k}", "name": v}
            for k, v in STAGE_NAMES.items()
        ]
    }


@app.post("/stage/{stage_num}")
def run_single_stage(stage_num: int, req: StageRequest):
    """단일 단계(G0~G10) 실행"""
    if stage_num not in range(0, 11):
        raise HTTPException(status_code=400, detail="stage_num은 0~10 사이여야 합니다.")

    pipeline = PhaseGatePipeline(tech_id=req.tech_id)
    try:
        result = pipeline.run_stage(stage_num, req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "tech_id": req.tech_id,
        "stage_num": stage_num,
        "stage_name": STAGE_NAMES[stage_num],
        "result": result.to_dict(),
    }


@app.post("/analyze")
def run_full_pipeline(req: PipelineRequest):
    """G0~G10 전체 파이프라인 실행"""
    pipeline = PhaseGatePipeline(tech_id=req.tech_id)
    try:
        summary = pipeline.run_pipeline(
            stage_inputs=req.stage_inputs,
            stop_on_kill=req.stop_on_kill,
            auto_chain=req.auto_chain,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "tech_id": req.tech_id,
        "summary": summary,
        "all_results": pipeline.get_all_results(),
        "output_dir": str(pipeline.output_dir),
    }


@app.get("/result/{tech_id}")
def get_result(tech_id: str):
    """저장된 파이프라인 결과 조회"""
    from pathlib import Path
    import json

    output_dir = Path(__file__).parent.parent / "outputs" / tech_id
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail=f"tech_id '{tech_id}'의 결과가 없습니다.")

    summary_path = output_dir / "pipeline_summary.json"
    results = {}

    if summary_path.exists():
        results["summary"] = json.loads(summary_path.read_text(encoding="utf-8"))

    for f in sorted(output_dir.glob("G*_result.json")):
        results[f.stem] = json.loads(f.read_text(encoding="utf-8"))

    return {"tech_id": tech_id, "results": results}


@app.post("/funding/match")
def funding_match(req: FundingMatchRequest):
    """TRL·국가·분야 기반 정부지원 프로그램 매칭"""
    programs = match_funding(
        trl=req.trl,
        country=req.country,
        sector=req.sector,
        stage_id=req.stage_id,
    )
    return {"trl": req.trl, "matched_programs": programs}


@app.get("/funding/sequence")
def funding_sequence(trl_current: int, trl_target: int, country: str = ""):
    """TRL 현재→목표 달성을 위한 단계별 자금조달 시퀀스"""
    sequence = recommend_funding_sequence(trl_current, trl_target, country)
    return {"trl_current": trl_current, "trl_target": trl_target, "sequence": sequence}


@app.post("/ip/idf")
def generate_idf(req: StageRequest):
    """발명공개서(IDF) 생성 — 1단계 IP개발"""
    try:
        result = IDFGenerator().assess(req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "G0-IDF", "result": result.to_dict()}


@app.post("/ip/portfolio")
def build_portfolio_strategy(req: StageRequest):
    """특허 포트폴리오 구성 전략 — 1단계 IP개발"""
    try:
        result = PatentPortfolioStrategist().assess(req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "G1-Portfolio", "result": result.to_dict()}


@app.post("/ip/whitespace")
def analyze_whitespace(req: StageRequest):
    """특허 화이트스페이스 분석 — WIPO 특허 지형 분석 표준 (FTO 보완)"""
    try:
        result = WhitespaceAnalyzer().assess(req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "G1-Whitespace", "result": result.to_dict()}


@app.post("/ip/patentability")
def assess_patentability(req: StageRequest):
    """권리성 심화 평가 — 2단계 IP평가"""
    try:
        result = PatentabilityAssessor().assess(req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "G2-Patent", "result": result.to_dict()}


@app.post("/ip/pcml")
def run_pcml_analysis(req: PCMLRequest, _: dict = Depends(require_auth)):
    """PCML v2.0 청구항 구조 분석 — New PCML v2.0 전용 구조화·검증 엔진
    6계층(L1~L6) 출력: patent_layer, claim_graph_layer, support_layer,
    metadata_layer, legal_family_layer, evidence_layer + shared_variables + governance + qc.
    LLM 키(ANTHROPIC_API_KEY) 없으면 규칙기반 분석으로 폴백.
    input_mode: claim_only | full_spec | enriched
    """
    from agents.pcml_agent import PCMLAgent
    try:
        agent = PCMLAgent()
        input_data = {
            "tech_id": req.tech_id,
            "patent_id": req.patent_id or req.tech_id,
            "patent_text": req.patent_text,
            "input_mode": req.input_mode if req.patent_text else "claim_only",
            **req.input_data,
        }
        result = agent.assess(input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    out = result.output_doc
    kpi_inputs = agent.extract_kpi_inputs(out)
    return {
        "tech_id": req.tech_id,
        "stage": "G1.5-PCML",
        "pcml_version": "3.0",
        "gate": result.gate,
        "score": result.score,
        # ── v3.0 4도메인 계층 ──────────────
        "tech_graph_layer":       out.get("tech_graph_layer", {}),
        "market_graph_layer":     out.get("market_graph_layer", {}),
        "business_graph_layer":   out.get("business_graph_layer", {}),
        "regulatory_graph_layer": out.get("regulatory_graph_layer", {}),
        "cross_domain_links":     out.get("cross_domain_links", []),
        # ── 공통 계층 ──────────────────────
        "support_layer":     out.get("support_layer", []),
        "metadata_layer":    out.get("metadata_layer", {}),
        "legal_family_layer":out.get("legal_family_layer", {}),
        "evidence_layer":    out.get("evidence_layer", []),
        "shared_variables":  out.get("shared_variables", {}),
        "governance":        out.get("governance", {}),
        "qc":                out.get("qc", {}),
        "analysis_limits":   out.get("analysis_limits", []),
        "next_actions":      out.get("next_actions", result.next_actions),
        # ── v2 호환 (screening_agent 등이 claim_graph_layer 참조) ──
        "claim_graph_layer": out.get("claim_graph_layer") or
                             out.get("tech_graph_layer", {}),
        # ── KPI 연계 & 요약 ────────────────
        "kpi_inputs": kpi_inputs,
        "summary": out.get("_part_a_summary") or out.get("_summary", ""),
    }


@app.post("/ip/screening")
def run_screening(req: PCMLRequest, _: dict = Depends(require_auth)):
    """G1.6 — 3단계 신규성 스크리닝 (PQE-SCR v4.0)

    pcml_result를 input_data에 담아 전달하거나 patent_text로 PCML을 먼저 실행하세요.
    """
    from agents.screening_agent import ScreeningAgent
    from agents.pcml_agent import PCMLAgent

    # store_a(PCML 결과)가 없으면 먼저 PCML 실행
    pcml_result = req.input_data.get("pcml_result")
    if not pcml_result and req.patent_text:
        pcml_agent = PCMLAgent()
        pcml_sr = pcml_agent.assess({
            "tech_id": req.tech_id,
            "patent_id": req.patent_id or req.tech_id,
            "patent_text": req.patent_text,
            "input_mode": req.input_mode,
        })
        pcml_result = pcml_sr.output_doc

    scope = req.input_data.get("scope", "basic")
    agent = ScreeningAgent()
    result = agent.assess({
        "tech_id": req.tech_id,
        "pcml_result": pcml_result or {},
        "scope": scope,
    })
    out = result.output_doc
    return {
        "tech_id": req.tech_id,
        "stage": "G1.6-SCR",
        "gate": result.gate,
        "score": result.score,
        "scope": scope,
        "noveltyAnalysis": out.get("noveltyAnalysis", {}),
        "inventiveStep": out.get("inventiveStep", {}),
        "scrReport": out.get("scrReport", {}),
        "priorArt": out.get("priorArt", {}),
        "whiteSpace": out.get("whiteSpace", []),
        "warnings": result.warnings,
    }


class _PatentFetchRequest(BaseModel):
    patent_id: str

@app.post("/ip/fetch-patent")
def fetch_patent(req: _PatentFetchRequest, _: dict = Depends(require_auth)):
    """특허 원문 조회 — KIPRIS(KR) 우선, Google Patents 폴백.

    요청: {"patent_id": "KR10-2021-0123456"}
    """
    patent_id: str = req.patent_id

    from pipeline.connectors.kipris_connector import fetch_from_kipris
    from pipeline.connectors.google_patents_connector import fetch_from_google_patents

    result = fetch_from_kipris(patent_id)
    if result:
        return {"patent_id": patent_id, "source": "kipris", **result}

    result = fetch_from_google_patents(patent_id)
    if result:
        return {"patent_id": patent_id, "source": "google_patents", **result}

    raise HTTPException(status_code=404, detail=f"특허를 찾을 수 없음: {patent_id}")


@app.post("/ip/global-strategy")
def global_ip_strategy(req: StageRequest):
    """글로벌 IP 출원 전략 — 4단계 IP전략"""
    try:
        result = GlobalIPStrategist().assess(req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "G10-Global", "result": result.to_dict()}


@app.post("/ip/competitive")
def competitive_response(req: StageRequest):
    """경쟁대응 전략 — 4단계 IP전략"""
    try:
        result = CompetitiveMonitor().assess(req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "G10-Competitive", "result": result.to_dict()}


@app.post("/ip/portfolio-optimize")
def optimize_portfolio(req: StageRequest):
    """IP 포트폴리오 최적화 — 4단계 IP전략"""
    try:
        result = PortfolioOptimizer().assess(req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "G10-Portfolio", "result": result.to_dict()}


@app.get("/ip/stages")
def list_ip_stages():
    """IP Lifecycle 확장 단계 목록"""
    return {
        "ip_lifecycle_phases": [
            {"phase": 1, "name": "IP개발", "stages": ["G0", "G0-IDF", "G1", "G1-Portfolio"]},
            {"phase": 2, "name": "IP평가", "stages": ["G2", "G2-Patent", "G3", "G6", "G8"]},
            {"phase": 3, "name": "IP활용", "stages": ["G4", "G5", "G7", "G9"]},
            {"phase": 4, "name": "IP전략", "stages": ["G10", "G10-Global", "G10-Competitive", "G10-Portfolio"]},
        ]
    }


@app.post("/ip/report")
def generate_report(req: PipelineRequest):
    """파이프라인 결과 → 투자자용 종합 진단 리포트

    두 가지 사용 방법:
    1) tech_id만 입력 → 기존 저장 결과(outputs/{tech_id}/) 로드 후 리포트
    2) stage_inputs 포함 → 즉시 파이프라인 실행 + 리포트 생성
    """
    pipeline = PhaseGatePipeline(tech_id=req.tech_id)

    # stage_inputs가 있으면 파이프라인 실행
    if req.stage_inputs:
        try:
            pipeline.run_pipeline(stage_inputs=req.stage_inputs, stop_on_kill=False)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    all_results = pipeline.get_all_results()

    # 저장된 결과도 없으면 에러
    if not all_results:
        import json
        from pathlib import Path
        output_dir = Path(__file__).parent.parent / "outputs" / req.tech_id
        if not output_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"'{req.tech_id}' 결과 없음. stage_inputs를 포함해 파이프라인을 먼저 실행하세요.",
            )
        for f in sorted(output_dir.glob("G*_result.json")):
            stage_num = f.stem.split("_")[0].replace("G", "")
            all_results[stage_num] = json.loads(f.read_text(encoding="utf-8"))

    try:
        report = build_report(req.tech_id, all_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리포트 생성 실패: {e}")

    return {"tech_id": req.tech_id, "report": report}


@app.get("/ip/db-status")
def db_status():
    """전체 연결 DB 가용성 실시간 점검 — Phase 1~3 11+4개 DB ping"""
    import urllib.request
    import urllib.error

    DB_LIST = [
        # Phase 1 — 즉시연결 (키 불필요)
        {"name": "OpenAlex",         "url": "https://api.openalex.org/works?filter=title.search:test&per-page=1", "phase": 1, "auth": False},
        {"name": "World Bank",        "url": "https://api.worldbank.org/v2/country/KR/indicator/NY.GDP.MKTP.CD?format=json&mrv=1", "phase": 1, "auth": False},
        {"name": "ClinicalTrials.gov","url": "https://clinicaltrials.gov/api/v2/studies?query.term=test&pageSize=1", "phase": 1, "auth": False},
        {"name": "PubMed/NCBI",       "url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=test&retmax=1&retmode=json", "phase": 1, "auth": False},
        {"name": "Europe PMC",        "url": "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=test&format=json&pageSize=1", "phase": 1, "auth": False},
        {"name": "OECD.Stat",         "url": "https://stats.oecd.org/sdmx-json/data/MSTI_PUB/KOR.TOT_GERD.REAL_PPP.USD_MIO/all?startTime=2020&endTime=2022&format=jsondata", "phase": 1, "auth": False},
        {"name": "Climate TRACE",     "url": "https://api.climatetrace.org/v6/definitions/sectors", "phase": 1, "auth": False},
        {"name": "EUDAMED",           "url": "https://ec.europa.eu/tools/eudamed/api/actors?page=0&size=1", "phase": 1, "auth": False},
        {"name": "ROR",               "url": "https://api.ror.org/organizations?query=KAIST", "phase": 1, "auth": False},
        {"name": "Our World in Data", "url": "https://ourworldindata.org/grapher/share-of-electricity-low-carbon.csv", "phase": 1, "auth": False},
        # Phase 2 — 키 등록 후
        {"name": "GLEIF LEI",         "url": "https://api.gleif.org/api/v1/lei-records?filter[entity.legalName]=Samsung", "phase": 2, "auth": True},
        {"name": "Open Supply Hub",   "url": "https://opensupplyhub.org/api/facilities/?page=1&pageSize=1", "phase": 2, "auth": True},
        {"name": "UN Comtrade v2",    "url": "https://comtradeapi.un.org/public/v1/preview/C/A/HS/528", "phase": 2, "auth": True},
        {"name": "NTIS",              "url": "https://www.ntis.go.kr/rndopen/api/v1/project?serviceKey=TEST&numOfRows=1", "phase": 2, "auth": True},
    ]

    results = []
    for db in DB_LIST:
        try:
            req = urllib.request.Request(db["url"], headers={"Accept": "application/json", "User-Agent": "IPInsight/1.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                results.append({"name": db["name"], "status": "ok", "http": r.status, "phase": db["phase"], "auth_required": db["auth"]})
        except urllib.error.HTTPError as e:
            results.append({"name": db["name"], "status": "auth_error" if e.code in (401, 403) else "error", "http": e.code, "phase": db["phase"], "auth_required": db["auth"]})
        except Exception as e:
            results.append({"name": db["name"], "status": "unreachable", "http": None, "phase": db["phase"], "auth_required": db["auth"], "detail": str(e)[:60]})

    ok_count   = sum(1 for r in results if r["status"] == "ok")
    return {
        "checked": len(results),
        "available": ok_count,
        "unavailable": len(results) - ok_count,
        "databases": results,
    }


@app.get("/ip/pipeline-ops")
def pipeline_ops():
    """파이프라인 운영 현황 — 캐시 신선도·커넥터 상태·라우팅 계획"""
    import time
    from pipeline.query_router import QueryRouter, CACHE_TTL, BULK_SCHEDULE, EFFICIENCY_MATRIX

    router    = QueryRouter()
    cache_dir = Path(__file__).parent.parent / ".rag_cache"
    knowledge_dir = Path(__file__).parent.parent / "knowledge"

    # ① 캐시 파일 신선도 분석
    cache_files    = list(cache_dir.glob("*.json")) if cache_dir.exists() else []
    now            = time.time()
    cache_stats    = []
    stale_count    = 0
    for cf in cache_files[:50]:          # 최대 50개 표시
        age_h  = (now - cf.stat().st_mtime) / 3600
        # 파일명에서 커넥터 타입 추론
        prefix = cf.name.split("_")[0]
        ttl    = CACHE_TTL.get(prefix, 168)
        fresh  = age_h < ttl
        if not fresh:
            stale_count += 1
        cache_stats.append({"file": cf.name[:40], "age_hours": round(age_h, 1),
                             "ttl": ttl, "fresh": fresh})

    # ② 지식 파일 신선도
    knowledge_files = ["global_markets.json", "country_programs.json",
                       "royalty_benchmarks.json", "global_tax_treaties.json"]
    knowledge_status = []
    for kf in knowledge_files:
        kpath = knowledge_dir / kf
        if kpath.exists():
            age_h = (now - kpath.stat().st_mtime) / 3600
            knowledge_status.append({"file": kf, "age_hours": round(age_h, 1),
                                     "size_kb": round(kpath.stat().st_size / 1024, 1)})
        else:
            knowledge_status.append({"file": kf, "missing": True})

    # ③ 스테이지별 라우팅 계획 미리보기
    sample_routes = {}
    for stage in ["G0", "G2", "G5", "G10"]:
        rd = router.route(stage, "agritech", ["KR", "US", "JP"])
        sample_routes[stage] = {
            "connectors": rd.connectors,
            "skipped":    rd.skipped,
            "api_calls":  rd.estimated_api_calls,
        }

    # ④ 비용 모델 요약
    cost_model = EFFICIENCY_MATRIX["cost_model"]

    return {
        "cache": {
            "total_files":  len(cache_files),
            "stale_files":  stale_count,
            "fresh_files":  len(cache_files) - stale_count,
            "details":      sorted(cache_stats, key=lambda x: x["age_hours"], reverse=True)[:10],
        },
        "knowledge": knowledge_status,
        "routing_preview": sample_routes,
        "cost_model": {
            "phase1_free_connectors": len(cost_model["free_connectors"]),
            "monthly_cost_usd":       cost_model["monthly_cost_usd"],
        },
        "bulk_schedule": BULK_SCHEDULE,
        "efficiency_modes": list(EFFICIENCY_MATRIX["pipeline_modes"].keys()),
    }


@app.get("/ip/route-plan")
def route_plan(
    stage:     str = "G2",
    tech_type: str = "agritech",
    regions:   str = "KR,US,JP",
):
    """특정 G-Stage × 기술 유형 × 지역의 최소 커넥터 라우팅 계획 반환"""
    from pipeline.query_router import QueryRouter
    router = QueryRouter()
    region_list = [r.strip() for r in regions.split(",") if r.strip()]
    decision    = router.route(stage, tech_type, region_list)
    priority    = router.connector_priority(stage)
    return {
        "decision":        {
            "stage":       decision.stage,
            "tech_type":   decision.tech_type,
            "regions":     decision.regions,
            "connectors":  decision.connectors,
            "skipped":     decision.skipped,
            "api_calls":   decision.estimated_api_calls,
            "summary":     decision.summary(),
            "rationale":   decision.rationale,
        },
        "execution_order": priority,
        "ttl_policy":      decision.ttl_policy,
    }


@app.post("/execution/team")
def assess_team(req: StageRequest):
    """팀·실행 역량 평가 — I-Corps 5차원 + 채용 우선순위"""
    try:
        result = TeamAssessor().assess(req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "G4-Team", "result": result.to_dict()}


@app.post("/execution/unit-economics")
def assess_unit_economics(req: StageRequest):
    """단위경제성 평가 — CAC·LTV·Burn Rate·손익분기"""
    try:
        result = UnitEconomicsAssessor().assess(req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "G5-UE", "result": result.to_dict()}


@app.post("/execution/funding")
def plan_funding(req: StageRequest):
    """자금조달 시나리오 플래너 — Bootstrap→Series A 지분 희석 시뮬레이션"""
    try:
        result = FundingPlanner().assess(req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "G2-Funding", "result": result.to_dict()}


@app.post("/execution/regulatory")
def regulatory_roadmap(req: StageRequest):
    """도메인별 규제·인증 로드맵 — 의료기기·SaMD·바이오·하드웨어·소프트웨어"""
    try:
        result = RegulatoryRoadmapAgent().assess(req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "G8-Reg", "result": result.to_dict()}


@app.get("/execution/stages")
def list_execution_stages():
    """실행전략 모듈 목록"""
    return {
        "execution_modules": [
            {"endpoint": "/execution/team",           "stage": "G4-Team",    "name": "팀·실행 역량 평가",        "gap": "팀 역량"},
            {"endpoint": "/execution/unit-economics", "stage": "G5-UE",      "name": "CAC·LTV·Burn Rate",       "gap": "단위경제성"},
            {"endpoint": "/execution/funding",        "stage": "G2-Funding", "name": "자금조달 시나리오 플래너", "gap": "자금조달"},
            {"endpoint": "/execution/regulatory",     "stage": "G8-Reg",     "name": "규제·인증 로드맵",         "gap": "규제 경로"},
        ]
    }


# ─────────────────────────────────────────────────────────
# ② 중기 Gap 보완 모듈 (Medium-term Gaps)
# ─────────────────────────────────────────────────────────

@app.post("/gap/ir-deck")
def generate_ir_deck(req: StageRequest):
    """IR Deck 자동 생성 — 투자자 유형별 12슬라이드 구조 + 피치 스크립트
    investor_type: vc/cvc/angel/government/strategic"""
    try:
        result = IRDeckGenerator().assess(req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "G6-IR", "result": result.to_dict()}


@app.post("/gap/esg-impact")
def assess_esg_impact(req: StageRequest):
    """ESG·사회임팩트 평가 — UN SDG 17개 매핑 + E·S·G 3축 점수 + SROI"""
    try:
        result = ESGImpactAssessor().assess(req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "G10-ESG", "result": result.to_dict()}


@app.post("/gap/trade-secret")
def analyze_trade_secret(req: StageRequest):
    """트레이드시크릿 vs 특허 경제성 비교 — 최적 IP 보호 전략 추천
    tech_type: process/product/software/algorithm/formula"""
    try:
        result = TradeSecretAnalyzer().assess(req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "G1-TS", "result": result.to_dict()}


@app.post("/gap/ecosystem-match")
def match_ecosystem(req: StageRequest):
    """생태계 파트너 매칭 — 기업·대학·연구소·VC·AC·정부 6개 카테고리
    industry_sector: AgriTech/HealthTech/Manufacturing/AI_Software/Energy_CleanTech/BioTech/SmartFarm"""
    try:
        result = EcosystemMatcher().assess(req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "G3-Eco", "result": result.to_dict()}


# ─────────────────────────────────────────────────────────
# ③ 장기 Gap 보완 모듈 (Long-term Gaps)
# ─────────────────────────────────────────────────────────

@app.post("/gap/exit-strategy")
def design_exit_strategy(req: StageRequest):
    """엑시트 전략 설계 — M&A·IPO·세컨더리·라이선스 5개 시나리오 + MOIC 계산
    preferred_exit: strategic_ma/financial_ma/ipo/secondary_sale/license_exit"""
    try:
        result = ExitStrategyDesigner().assess(req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "G10-Exit", "result": result.to_dict()}


@app.post("/gap/patent-maintenance")
def optimize_patent_maintenance(req: StageRequest):
    """특허 유지비 최적화 — 국가별 갱신료 vs 기술 가치 분석 → 유지·이전·포기 결정
    input: portfolio (list of patent objects) + annual_budget_usd"""
    try:
        result = PatentMaintenanceOptimizer().assess(req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "G1-Maint", "result": result.to_dict()}


@app.get("/gap/stages")
def list_gap_stages():
    """3등급 Gap 보완 모듈 전체 목록"""
    return {
        "gap_modules": {
            "critical_gap_1": [
                {"endpoint": "/execution/team",           "stage": "G4-Team",    "name": "팀·실행 역량 평가"},
                {"endpoint": "/execution/unit-economics", "stage": "G5-UE",      "name": "CAC·LTV·Burn Rate"},
                {"endpoint": "/execution/funding",        "stage": "G2-Funding", "name": "자금조달 시나리오"},
                {"endpoint": "/execution/regulatory",     "stage": "G8-Reg",     "name": "규제·인증 로드맵"},
            ],
            "medium_gap_2": [
                {"endpoint": "/gap/ir-deck",        "stage": "G6-IR",    "name": "IR Deck 자동 생성"},
                {"endpoint": "/gap/esg-impact",     "stage": "G10-ESG",  "name": "ESG·SDG 임팩트 평가"},
                {"endpoint": "/gap/trade-secret",   "stage": "G1-TS",    "name": "트레이드시크릿 vs 특허"},
                {"endpoint": "/gap/ecosystem-match","stage": "G3-Eco",   "name": "생태계 파트너 매칭"},
            ],
            "long_term_gap_3": [
                {"endpoint": "/gap/exit-strategy",       "stage": "G10-Exit",  "name": "M&A·IPO 엑시트 전략"},
                {"endpoint": "/gap/patent-maintenance",  "stage": "G1-Maint",  "name": "특허 유지비 최적화"},
            ],
        }
    }


# ─────────────────────────────────────────────────────────
# Layer 3 — 서비스: 수요조사서·SMK·로드맵 자동 생성
# ─────────────────────────────────────────────────────────

@app.post("/service/demand-survey")
def generate_demand_survey(req: StageRequest):
    """수요조사서 자동 생성 — RAG 기반 수요처·도입장벽·파일럿 로드맵 산출
    industry_sector: AgriTech/HealthTech/Manufacturing/AI_Software/Energy_CleanTech/BioTech"""
    try:
        result = DemandSurveyGenerator().assess(req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "G0-DS", "result": result.to_dict()}


@app.post("/service/smk")
def generate_smk(req: StageRequest):
    """SMK(사업화시장키트) 자동 생성 — 경쟁사 비교·GTM 전략·가격·포지셔닝 산출
    gtm_motion: direct_sales/product_led/partner_led/channel_reseller/community_led"""
    try:
        result = SMKGenerator().assess(req.input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "SMK", "result": result.to_dict()}


@app.post("/service/roadmap")
def generate_roadmap(req: StageRequest):
    """기술사업화 로드맵 자동 생성 — TRL 단계별 마일스톤·자금·KPI·리스크 타임라인"""
    d = req.input_data
    try:
        roadmap = build_roadmap(
            tech_id      = req.tech_id,
            tech_name    = d.get("tech_name", req.tech_id),
            current_trl  = d.get("current_trl", 3),
            target_trl   = d.get("target_trl", 9),
            pipeline_results = d.get("pipeline_results", {}),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "Roadmap", "roadmap": roadmap}


@app.get("/service/stages")
def list_service_stages():
    """Layer 3 서비스 단계 목록"""
    return {
        "service_modules": [
            {"endpoint": "/service/demand-survey", "stage": "G0-DS", "output": "수요조사서"},
            {"endpoint": "/service/smk",           "stage": "SMK",   "output": "사업화시장키트(SMK)"},
            {"endpoint": "/service/roadmap",        "stage": "Roadmap","output": "기술사업화 로드맵"},
        ]
    }


# ─────────────────────────────────────────────────────────
# Layer 4 — 검증: PoC 체크리스트 실행
# ─────────────────────────────────────────────────────────

@app.get("/verify/poc")
def run_poc_verification():
    """PoC 검증 체크리스트 실행 — 14개 항목 자동 검증 + 결과 JSON 반환"""
    try:
        from deploy.poc_checklist import PoCVerifier
        verifier = PoCVerifier(base_url="http://localhost:8100")
        report   = verifier.run_all()
        verifier.save_report()
        return {
            "poc_summary": {
                "total":     report.total,
                "passed":    report.passed,
                "failed":    report.failed,
                "warned":    report.warned,
                "pass_rate": report.pass_rate,
            },
            "items": [
                {"category": i.category, "name": i.name, "status": i.status,
                 "detail": i.detail, "ms": i.duration_ms}
                for i in report.items
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/demo/sample-input")
def sample_input():
    """샘플 파이프라인 입력 데이터 반환 (테스트용)"""
    return {
        "tech_id": "demo_tech_001",
        "stage_inputs": {
            0: {
                "tech_name": "AI 기반 스마트팜 수확량 예측 시스템",
                "owner": "KAASA 연구팀",
                "tech_description": "딥러닝과 IoT 센서를 결합하여 온실 작물의 수확량을 7일 전 예측하는 AI 시스템",
                "problem_statement": "온실 농가는 수확량 예측 불확실성으로 인해 과잉생산 또는 공급부족이 발생",
                "field_keywords": ["스마트팜", "AI", "IoT", "농업기술"],
                "ipc_codes": ["G06N", "A01G"],
                "existing_solutions": "기상청 예보 기반 단순 추정, 경험적 판단",
            },
            2: {
                "tech_description": "딥러닝 수확량 예측",
                "claimed_trl": 5,
                "evidence_list": [
                    {"type": "성능평가 보고서", "description": "MAPE 17.8% 달성", "date": "2026-03"},
                    {"type": "시제품 보고서", "description": "딸기 5농가 실증 완료", "date": "2026-04"},
                ],
                "target_trl": 8,
            },
            3: {
                "tech_name": "스마트팜 수확량 예측 AI",
                "target_market": "국내외 온실 농가 및 스마트팜 기업",
                "tam_usd": 5_000_000_000,
                "sam_usd": 500_000_000,
                "som_usd": 10_000_000,
                "growth_rate_pct": 15,
                "competitors": ["Priva", "Ridder", "LetsGrow.com"],
                "entry_barriers": ["데이터 축적 필요", "농가 신뢰 확보"],
                "substitute_technologies": ["기상청 예보", "전문가 컨설팅"],
            },
            6: {
                "tech_name": "스마트팜 AI",
                "industry_sector": "스마트팜·농업기술",
                "revenue_forecast": [500_000, 2_000_000, 5_000_000, 10_000_000, 15_000_000],
                "discount_rate_pct": 15,
                "royalty_rate_pct": 4,
                "tech_contribution_pct": 35,
                "patent_remaining_years": 18,
                "risk_adjustment_pct": 25,
                "monte_carlo_runs": 1000,
            },
        },
        "stop_on_kill": True,
    }


# ═══════════════════════════════════════════════════════════════
# Phase 1 — 인증 엔드포인트
# ═══════════════════════════════════════════════════════════════

@app.post(
    "/auth/token",
    response_model=TokenResponse,
    tags=["인증"],
    summary="JWT 액세스 토큰 발급",
)
def auth_token(req: TokenRequest):
    """username + password → Bearer JWT (30분 유효)."""
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호 오류")
    token = create_access_token(sub=user["sub"], role=user.get("role", "user"))
    return TokenResponse(access_token=token)


# ═══════════════════════════════════════════════════════════════
# Phase 3 — 운영 인프라 엔드포인트
# ═══════════════════════════════════════════════════════════════

@app.get("/metrics", tags=["운영"], summary="요청 메트릭 (인메모리)")
def metrics(_user: dict = Depends(require_auth)):
    return get_metrics()


@app.get("/jobs/{job_id}", response_model=JobStatus, tags=["비동기 Job"], summary="Job 상태 조회")
def get_job(job_id: str, _user: dict = Depends(require_auth)):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} 없음")
    return JobStatus(**job)


# ═══════════════════════════════════════════════════════════════
# ★ A급 강화 엔드포인트 — 고객검증·성과관리·자동체인
# ═══════════════════════════════════════════════════════════════

# ── 인터뷰 요청 모델 ──────────────────────────────────────────
class _InterviewRecord(BaseModel):
    customer_type: str
    pain_point: str
    willingness_to_pay: float = 0
    alternative_used: str = ""
    urgency_1to5: int = 3
    jtbd_functional: str = ""
    jtbd_emotional: str = ""
    jtbd_social: str = ""

class _InterviewBatch(BaseModel):
    tech_id: str
    interviews: list[_InterviewRecord]
    loi_count: int = 0
    poc_requests: int = 0

# 인메모리 인터뷰 스토어 (재시작 시 초기화 — SQLite 전환 시 영속화)
_interview_store: dict[str, list[dict]] = {}
_interview_meta: dict[str, dict]        = {}


@app.post("/g4/interviews", tags=["G4 고객검증"], summary="인터뷰 기록 저장 (NSF I-Corps)")
def save_interviews(req: _InterviewBatch, _: dict = Depends(require_auth)):
    """고객 인터뷰 일괄 저장.
    누적 방식 — 동일 tech_id로 여러 번 호출하면 인터뷰가 합산됩니다.
    목표: 100건 (NSF I-Corps National 기준)
    """
    existing = _interview_store.get(req.tech_id, [])
    new_records = [i.model_dump() for i in req.interviews]
    merged = existing + new_records
    _interview_store[req.tech_id] = merged
    _interview_meta[req.tech_id] = {
        "loi_count":    req.loi_count,
        "poc_requests": req.poc_requests,
    }
    total = len(merged)
    return {
        "tech_id":       req.tech_id,
        "added":         len(new_records),
        "total":         total,
        "icorps_target": 100,
        "progress_pct":  round(total / 100 * 100, 1),
        "status":        "달성" if total >= 100 else "진행중" if total >= 30 else "초기단계",
    }


@app.get("/g4/interviews/{tech_id}", tags=["G4 고객검증"], summary="인터뷰 현황 조회")
def get_interviews(tech_id: str, _: dict = Depends(require_auth)):
    """저장된 인터뷰 목록 + NSF I-Corps 달성률 + JTBD 분석 요약"""
    records = _interview_store.get(tech_id, [])
    meta    = _interview_meta.get(tech_id, {})
    total   = len(records)
    jtbd_covered = sum(1 for r in records if r.get("jtbd_functional"))
    wtp_confirmed = sum(1 for r in records if r.get("willingness_to_pay", 0) > 0)
    avg_urgency = round(
        sum(r.get("urgency_1to5", 0) for r in records) / max(total, 1), 1
    )
    customer_types: dict = {}
    for r in records:
        ct = r.get("customer_type", "미분류")
        customer_types[ct] = customer_types.get(ct, 0) + 1

    return {
        "tech_id":        tech_id,
        "total_interviews": total,
        "icorps": {
            "phase1_min":       30,
            "national_target":  100,
            "achieved_phase1":  total >= 30,
            "achieved_national": total >= 100,
            "progress_pct":     round(total / 100 * 100, 1),
        },
        "jtbd_coverage_pct":   round(jtbd_covered / max(total, 1) * 100, 1),
        "wtp_confirmed_pct":   round(wtp_confirmed / max(total, 1) * 100, 1),
        "avg_urgency":         avg_urgency,
        "customer_type_dist":  customer_types,
        "loi_count":           meta.get("loi_count", 0),
        "poc_requests":        meta.get("poc_requests", 0),
        "interviews":          records[-20:],  # 최근 20건
    }


@app.post("/g4/assess", tags=["G4 고객검증"], summary="G4 고객검증 평가 실행")
def assess_g4(req: StageRequest, _: dict = Depends(require_auth)):
    """저장된 인터뷰 + 입력 데이터로 G4 CustomerValidator 평가 실행"""
    from agents.g4_customer_validator import CustomerValidator
    tech_id = req.tech_id
    stored  = _interview_store.get(tech_id, [])
    meta    = _interview_meta.get(tech_id, {})

    input_data = dict(req.input_data)
    # 저장 인터뷰 자동 병합
    if stored and not input_data.get("interviews"):
        input_data["interviews"] = stored
    if meta:
        input_data.setdefault("loi_count", meta.get("loi_count", 0))
        input_data.setdefault("poc_requests", meta.get("poc_requests", 0))

    try:
        result = CustomerValidator().assess(input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"tech_id": tech_id, "stage": "G4", "result": result.to_dict()}


# ── G10 KPI 실시간 피드 ──────────────────────────────────────

class _KpiEvent(BaseModel):
    tech_id: str
    kpi_key: str
    value: float
    source: str = "api"
    note: str = ""

class _KpiBatch(BaseModel):
    tech_id: str
    actuals: dict
    source: str = "api"


@app.post("/g10/kpi", tags=["G10 성과관리"], summary="KPI 이벤트 단건 기록")
def record_kpi(req: _KpiEvent, _: dict = Depends(require_auth)):
    """실시간 KPI 단건 push — CRM/ERP 웹훅에서 직접 호출 가능."""
    from agents.g10_performance_tracker import record_kpi_event
    row_id = record_kpi_event(req.tech_id, req.kpi_key, req.value, req.source, req.note)
    return {"recorded": True, "row_id": row_id,
            "tech_id": req.tech_id, "kpi_key": req.kpi_key, "value": req.value}


@app.post("/g10/kpi/batch", tags=["G10 성과관리"], summary="KPI 일괄 기록")
def record_kpi_batch(req: _KpiBatch, _: dict = Depends(require_auth)):
    """actuals 딕셔너리 전체를 한번에 KPI 스토어에 기록."""
    from agents.g10_performance_tracker import record_kpi_event
    recorded = []
    for kpi_key, value in req.actuals.items():
        try:
            row_id = record_kpi_event(req.tech_id, kpi_key, float(value), req.source)
            recorded.append({"kpi_key": kpi_key, "value": value, "row_id": row_id})
        except Exception as e:
            recorded.append({"kpi_key": kpi_key, "error": str(e)})
    return {"tech_id": req.tech_id, "recorded": len(recorded), "events": recorded}


@app.get("/g10/kpi/{tech_id}", tags=["G10 성과관리"], summary="KPI 피드 조회")
def get_kpi_feed_endpoint(tech_id: str, limit: int = 50, _: dict = Depends(require_auth)):
    """tech_id의 KPI 이벤트 이력 (최신순). 실시간 대시보드 폴링에 사용."""
    from agents.g10_performance_tracker import get_kpi_feed, get_latest_kpis
    feed    = get_kpi_feed(tech_id, limit=limit)
    latest  = get_latest_kpis(tech_id)
    return {
        "tech_id":    tech_id,
        "latest_kpis": latest,
        "event_count": len(feed),
        "events":      feed,
    }


@app.get("/g10/kpi/{tech_id}/alerts", tags=["G10 성과관리"], summary="KPI 알림 조회")
def get_kpi_alerts(tech_id: str, _: dict = Depends(require_auth)):
    """tech_id의 최신 KPI 값을 임계값과 비교해 danger/warn 알림 반환."""
    from agents.g10_performance_tracker import check_kpi_alerts
    alerts = check_kpi_alerts(tech_id)
    return {
        "tech_id": tech_id,
        "alert_count": len(alerts),
        "has_danger": any(a["level"] == "danger" for a in alerts),
        "alerts": alerts,
    }


@app.post("/g10/assess", tags=["G10 성과관리"], summary="G10 성과평가 실행 (KPI 스토어 통합)")
def assess_g10(req: StageRequest, _: dict = Depends(require_auth)):
    """KPI 스토어 자동 참조 + 입력 actuals 병합 후 G10 PerformanceTracker 실행."""
    from agents.g10_performance_tracker import PerformanceTracker
    input_data = dict(req.input_data)
    input_data["tech_id"]       = req.tech_id
    input_data["use_kpi_store"] = True
    try:
        result = PerformanceTracker().assess(input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"tech_id": req.tech_id, "stage": "G10", "result": result.to_dict()}


# ── 특허→PCML→SCR 자동 체인 ──────────────────────────────────

class _ChainRequest(BaseModel):
    patent_id: str = ""
    patent_text: str = ""  # patent_id 없이 원문 직접 입력 가능
    tech_id: str = ""
    scope: str = "basic"
    include_report_recommendations: bool = True


@app.post("/ip/analyze-chain", tags=["IP 자동체인"], summary="특허→PCML→SCR 일괄 실행")
def analyze_chain(req: _ChainRequest, _: dict = Depends(require_auth)):
    """patent_id 하나로 KIPRIS 조회→PCML 분석→SCR 스크리닝을 순서대로 실행.

    결과: patent_raw, pcml(6계층), scr(게이트·권장보고서), recommended_next_steps
    """
    from pipeline.connectors.kipris_connector import fetch_from_kipris
    from pipeline.connectors.google_patents_connector import fetch_from_google_patents
    from agents.pcml_agent import PCMLAgent
    from agents.screening_agent import ScreeningAgent

    tech_id = req.tech_id or req.patent_id or "unknown"

    # Step 1: 특허 원문 확보 (직접 입력 우선, 없으면 patent_id로 조회)
    patent_text = req.patent_text.strip()
    patent_raw = None
    if not patent_text and req.patent_id:
        try:
            patent_raw = fetch_from_kipris(req.patent_id)
        except Exception:
            patent_raw = None
        if not patent_raw:
            try:
                patent_raw = fetch_from_google_patents(req.patent_id)
            except Exception:
                patent_raw = None
        if patent_raw:
            patent_text = " ".join(filter(None, [
                patent_raw.get("title", ""),
                patent_raw.get("abstract", ""),
                " ".join(patent_raw.get("claims", [])),
            ]))

    if not patent_text and not req.patent_id:
        raise HTTPException(status_code=422, detail="patent_text 또는 patent_id 중 하나는 필수입니다.")
    if not patent_text:
        patent_text = f"Patent: {req.patent_id}"  # 폴백 — 규칙기반으로 처리

    # Step 2: PCML v2.0
    try:
        pcml_agent = PCMLAgent()
        pcml_result_sr = pcml_agent.assess({
        "tech_id":    tech_id,
        "patent_id":  req.patent_id,
        "patent_text": patent_text,
            "input_mode": "full_spec" if patent_text and len(patent_text) > 200 else "claim_only",
        })
        pcml_out = pcml_result_sr.output_doc
        kpi_inputs = pcml_agent.extract_kpi_inputs(pcml_out)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PCML 분석 실패: {e}")

    # Step 3: SCR 신규성 스크리닝
    try:
        scr_agent = ScreeningAgent()
        scr_result_sr = scr_agent.assess({
            "tech_id":    tech_id,
            "pcml_result": pcml_out,
            "scope":       req.scope,
        })
        scr_out = scr_result_sr.output_doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SCR 스크리닝 실패: {e}")
    gate_routing = scr_out.get("scrReport", {}).get("gateRouting", {})

    # Step 4: 권장 보고서 + 다음 단계
    recommended_reports = gate_routing.get("recommendedReports", ["R1_investment"])
    next_steps = []
    gate = gate_routing.get("gate", "G3")
    if gate in ("G1", "G2"):
        next_steps += [f"권장 보고서 생성: {r}" for r in recommended_reports[:3]]
        next_steps.append("POST /reports/generate로 보고서 생성 시작")
    else:
        rescreen = gate_routing.get("rescreenConditions", [])
        next_steps = rescreen or ["재스크리닝 후 G2 이상 목표"]

    return {
        "tech_id":     tech_id,
        "patent_id":   req.patent_id,
        "chain": {
            "step1_patent_fetch": {
                "success":     bool(patent_raw),
                "source":      patent_raw.get("source", "없음") if patent_raw else "없음",
                "title":       patent_raw.get("title", "") if patent_raw else "",
            },
            "step2_pcml": {
                "gate":        pcml_result_sr.gate,
                "score":       pcml_result_sr.score,
                "qc_grade":    pcml_out.get("qc", {}).get("qc_grade", ""),
                "core_nodes":  pcml_out.get("shared_variables", {}).get("self_core_nodes", 0),
                "release_status": pcml_out.get("governance", {}).get("release_status", ""),
                "kpi_inputs":  kpi_inputs,
            },
            "step3_scr": {
                "gate":        scr_result_sr.gate,
                "score":       scr_result_sr.score,
                "novelty":     scr_out.get("noveltyAnalysis", {}).get("status", ""),
                "inventive":   scr_out.get("inventiveStep", {}).get("status", ""),
                "white_space": scr_out.get("whiteSpace", []),
                "hard_stops":  [
                    h for h in scr_out.get("scrReport", {}).get("hardStops", [])
                    if h.get("detected")
                ],
            },
        },
        "overall_gate":          gate,
        "recommended_reports":   recommended_reports if req.include_report_recommendations else [],
        "next_steps":            next_steps,
        "warnings":              scr_result_sr.warnings,
        "consistency_check":     _check_pcml_scr_consistency(pcml_result_sr, scr_result_sr),
    }


class _ChainExtRequest(BaseModel):
    patent_id: str = ""
    patent_text: str = ""
    tech_id: str = ""
    tech_name: str = ""
    scope: str = "basic"
    # G3 보조 입력 — 없으면 SCR 결과에서 자동 추정
    tam_usd: float = 0.0
    sam_usd: float = 0.0
    som_usd: float = 0.0
    growth_rate_pct: float = 0.0
    target_market: str = ""


@app.post("/ip/analyze-chain-extended", tags=["IP 자동체인"],
          summary="특허→PCML→SCR→G3(시장성) 연속 실행")
def analyze_chain_extended(req: _ChainExtRequest, _: dict = Depends(require_auth)):
    """PCML(G1)→SCR(G2)→MarketScanner(G3) 3단 연속 파이프라인.

    G3 입력값을 직접 주지 않으면 SCR 화이트스페이스·경쟁자 결과를 자동 활용.
    """
    from pipeline.connectors.kipris_connector import fetch_from_kipris
    from pipeline.connectors.google_patents_connector import fetch_from_google_patents
    from agents.pcml_agent import PCMLAgent
    from agents.screening_agent import ScreeningAgent
    from agents.g3_market_scanner import MarketScanner

    tech_id = req.tech_id or req.patent_id or "unknown"
    tech_name = req.tech_name or tech_id

    # ── Step 1: 특허 원문 ──────────────────────────────────────
    patent_text = req.patent_text.strip()
    patent_raw = None
    if not patent_text and req.patent_id:
        for fetcher in [fetch_from_kipris, fetch_from_google_patents]:
            try:
                patent_raw = fetcher(req.patent_id)
                if patent_raw:
                    break
            except Exception:
                pass
        if patent_raw:
            patent_text = " ".join(filter(None, [
                patent_raw.get("title", ""),
                patent_raw.get("abstract", ""),
                " ".join(patent_raw.get("claims", [])),
            ]))
    if not patent_text:
        if req.patent_id:
            patent_text = f"Patent: {req.patent_id}"
        else:
            raise HTTPException(422, "patent_text 또는 patent_id 필수")

    # ── Step 2: PCML ───────────────────────────────────────────
    try:
        pcml_agent = PCMLAgent()
        pcml_sr = pcml_agent.assess({
            "tech_id": tech_id,
            "patent_id": req.patent_id,
            "patent_text": patent_text,
            "input_mode": "full_spec" if len(patent_text) > 200 else "claim_only",
        })
        pcml_out = pcml_sr.output_doc
        kpi_inputs = pcml_agent.extract_kpi_inputs(pcml_out)
    except Exception as e:
        raise HTTPException(500, f"PCML 실패: {e}")

    # ── Step 3: SCR ────────────────────────────────────────────
    try:
        scr_agent = ScreeningAgent()
        scr_sr = scr_agent.assess({
            "tech_id": tech_id,
            "pcml_result": pcml_out,
            "scope": req.scope,
        })
        scr_out = scr_sr.output_doc
    except Exception as e:
        raise HTTPException(500, f"SCR 실패: {e}")

    # ── Step 4: G3 시장성 ─ SCR 결과로 자동 보완 ──────────────
    white_space = scr_out.get("whiteSpace", [])
    competitors_raw = scr_out.get("competitorLandscape", {}).get("majorPlayers", [])
    competitor_names = [
        (c.get("name") or c) if isinstance(c, dict) else str(c)
        for c in competitors_raw[:10]
    ]

    # TAM 자동 추정: SCR ipc_classes 키워드 기반 기본값 적용
    tam = req.tam_usd or 500_000_000    # 기본 5억 달러 (중소 기술 기준)
    sam = req.sam_usd or tam * 0.15
    som = req.som_usd or sam * 0.05
    growth = req.growth_rate_pct or 8.0  # 글로벌 기술이전 시장 평균
    target_market = req.target_market or "글로벌 B2B 기술 라이선싱"

    try:
        g3_agent = MarketScanner()
        g3_sr = g3_agent.assess({
            "tech_name": tech_name,
            "target_market": target_market,
            "tam_usd": tam,
            "sam_usd": sam,
            "som_usd": som,
            "growth_rate_pct": growth,
            "competitors": competitor_names,
            "entry_barriers": [ws.get("barrier", ws) if isinstance(ws, dict) else str(ws) for ws in white_space[:5]],
            "substitute_technologies": [],
        })
        g3_out = g3_sr.output_doc
    except Exception as e:
        raise HTTPException(500, f"G3 시장성 분석 실패: {e}")

    gate_routing = scr_out.get("scrReport", {}).get("gateRouting", {})
    overall_gate = gate_routing.get("gate", scr_sr.gate)

    return {
        "tech_id": tech_id,
        "patent_id": req.patent_id,
        "chain": {
            "step1_patent": {
                "success": bool(patent_raw),
                "source": patent_raw.get("source", "") if patent_raw else "direct_input",
                "title": patent_raw.get("title", "") if patent_raw else "",
            },
            "step2_pcml": {
                "gate": pcml_sr.gate,
                "score": pcml_sr.score,
                "qc_grade": pcml_out.get("qc", {}).get("qc_grade", ""),
                "core_nodes": pcml_out.get("shared_variables", {}).get("self_core_nodes", 0),
                "release_status": pcml_out.get("governance", {}).get("release_status", ""),
                "kpi_inputs": kpi_inputs,
            },
            "step3_scr": {
                "gate": scr_sr.gate,
                "score": scr_sr.score,
                "novelty": scr_out.get("noveltyAnalysis", {}).get("status", ""),
                "inventive": scr_out.get("inventiveStep", {}).get("status", ""),
                "white_space": white_space,
                "hard_stops": [h for h in scr_out.get("scrReport", {}).get("hardStops", []) if h.get("detected")],
            },
            "step4_g3": {
                "gate": g3_sr.gate,
                "score": g3_sr.score,
                "tam_usd": tam,
                "sam_usd": sam,
                "som_usd": som,
                "growth_rate_pct": growth,
                "competitors_analyzed": len(competitor_names),
                "attractiveness": g3_out.get("industryAttractiveness", {}).get("rating", ""),
                "next_actions": g3_sr.next_actions,
            },
        },
        "overall_gate": overall_gate,
        "pipeline_scores": {
            "pcml": pcml_sr.score,
            "scr": scr_sr.score,
            "g3": g3_sr.score,
            "composite": round((pcml_sr.score * 0.3 + scr_sr.score * 0.4 + g3_sr.score * 0.3), 1),
        },
        "recommended_reports": gate_routing.get("recommendedReports", ["R1_investment"]),
        "next_steps": g3_sr.next_actions[:5],
        "warnings": pcml_sr.warnings + scr_sr.warnings,
        "consistency_check": _check_pcml_scr_consistency(pcml_sr, scr_sr),
    }


@app.post(
    "/analyze/async",
    response_model=JobStatus,
    tags=["비동기 Job"],
    summary="전체 분석 비동기 실행 (job_id 반환 → GET /jobs/{id} 폴링)",
)
def analyze_async(
    req: StageRequest,
    background_tasks: BackgroundTasks,
    _user: dict = Depends(require_auth),
):
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "created_at": _t.time(),
        "result": None,
        "error": None,
        "completed_at": None,
    }

    from pipeline.code_linker import CodeLinkerPipeline
    linker = CodeLinkerPipeline()

    def _work():
        ctx = linker.run(req.tech_id, req.input_data)
        return ctx.to_dict() if hasattr(ctx, "to_dict") else ctx

    background_tasks.add_task(_run_job, job_id, _work)
    return JobStatus(**_jobs[job_id])


# ═══════════════════════════════════════════════════════════════
# Phase 2 — 타입 스키마 엔드포인트 (기존 StageRequest 대체)
# ═══════════════════════════════════════════════════════════════

@app.post(
    "/ip/full-lifecycle",
    tags=["IP 라이프사이클"],
    summary="IP 전주기 분석 (발굴→보호→사업화→관리)",
)
def ip_full_lifecycle(req: IPAnalysisRequest, _user: dict = Depends(require_auth)):
    """IPAnalysisRequest → 4단계 IP 라이프사이클 전체 실행."""
    merged_input = {
        "tech_name": req.tech_name,
        "tech_description": req.tech_description,
        "ipc_codes": req.ipc_codes,
        "cpc_codes": req.cpc_codes,
        "target_markets": req.target_markets,
        "trl": req.trl,
        **req.input_data,
    }
    stage_inputs: dict[int, dict] = {i: merged_input for i in range(11)}
    pipeline = PhaseGatePipeline(req.tech_id)
    result = pipeline.run_all(stage_inputs, stop_on_kill=True)
    return result


@app.post(
    "/gap/analyze",
    tags=["갭 분석"],
    summary="기술 갭 · 이전 가능성 분석",
)
def gap_analyze(req: GapRequest, _user: dict = Depends(require_auth)):
    from agents import EcosystemMatcher
    result = EcosystemMatcher().assess({
        "tech_name": req.tech_name,
        "industry_sector": req.industry_sector,
        "trl": req.trl,
        **req.input_data,
    })
    return {"tech_id": req.tech_id, "stage": "G3-Eco", "result": result.to_dict()}


@app.post(
    "/execution/strategy",
    tags=["실행 전략"],
    summary="사업화 실행 전략 수립",
)
def execution_strategy(req: ExecutionRequest, _user: dict = Depends(require_auth)):
    from agents import IRDeckGenerator
    result = IRDeckGenerator().assess({
        "tech_name": req.tech_name,
        "business_model": req.business_model,
        "target_revenue_usd": req.target_revenue_usd,
        **req.input_data,
    })
    return {"tech_id": req.tech_id, "stage": "G6-IR", "result": result.to_dict()}


@app.post(
    "/valuation/dcf",
    tags=["가치평가"],
    summary="DCF · CCA · ROA 기술 가치평가",
)
def valuation(req: ValuationRequest, _user: dict = Depends(require_auth)):
    pipeline = PhaseGatePipeline(req.tech_id)
    return pipeline.run_stage(6, {
        "revenue_forecast": list(req.revenue_forecast.values()),
        "discount_rate_pct": req.discount_rate * 100,
        "royalty_rate_pct": req.royalty_rate * 100,
        "method": req.method,
        **req.input_data,
    })


@app.post(
    "/regulation/roadmap",
    tags=["규제 인증"],
    summary="FDA·CE·MFDS 규제 인증 경로 매핑",
)
def regulation_roadmap(req: RegulationRequest, _user: dict = Depends(require_auth)):
    from agents import RegulatoryRoadmapAgent
    result = RegulatoryRoadmapAgent().assess({
        "product_type": req.product_type,
        "target_countries": req.target_countries,
        "fda_510k": req.fda_510k,
        **req.input_data,
    })
    return {"tech_id": req.tech_id, "stage": "G8-Reg", "result": result.to_dict()}


@app.post(
    "/roadmap/full",
    tags=["로드맵"],
    summary="G0→G10 전체 로드맵 생성 (단계 입력 일괄)",
)
def roadmap_full(req: RoadmapRequest, _user: dict = Depends(require_auth)):
    base = {
        "tech_name": req.tech_name,
        "tech_type": req.tech_type,
        "region": req.region,
        "trl_current": req.trl_current,
        "trl_target": req.trl_target,
    }
    merged = {i: {**base, **req.stage_inputs.get(str(i), {})} for i in range(11)}
    pipeline = PhaseGatePipeline(req.tech_id)
    return pipeline.run_all(merged, stop_on_kill=False)


# ═══════════════════════════════════════════════════════════
# G5 사업화 로드맵 엔드포인트
# ═══════════════════════════════════════════════════════════

@app.post(
    "/g5/assess",
    tags=["G5 사업모델·GTM"],
    summary="G5 BM 설계 + 사업화 로드맵 + SMK 자동 생성",
)
def assess_g5_full(req: StageRequest, _: dict = Depends(require_auth)):
    """G5 BMDesigner 실행 후 사업화 로드맵·SMK 자동 트리거.
    output_doc에 commercialization_roadmap·smk 블록 포함.
    """
    from agents.g5_bm_designer import BMDesigner
    result = BMDesigner().assess(req.input_data)
    return {"tech_id": req.tech_id, "stage": result.stage,
            "score": result.score, "gate": result.gate,
            "output": result.output_doc,
            "next_actions": result.next_actions}


@app.post(
    "/g5/roadmap",
    tags=["G5 사업모델·GTM"],
    summary="사업화 로드맵 단독 생성 (KIAT/KEIT 협약 양식)",
)
def generate_commercialization_roadmap(req: StageRequest, _: dict = Depends(require_auth)):
    """G5 BMDesigner 결과 없이 독립 실행 가능.
    input_data에 bm_output(dict) 포함 시 BM 데이터와 통합.
    """
    from agents.g5_commercialization_roadmap import CommercializationRoadmap
    result = CommercializationRoadmap().assess(req.input_data)
    return {"tech_id": req.tech_id, "stage": result.stage,
            "score": result.score, "gate": result.gate,
            "roadmap": result.output_doc,
            "next_actions": result.next_actions}


# ═══════════════════════════════════════════════════════════
# G4 LoI 도입의향서 엔드포인트
# ═══════════════════════════════════════════════════════════

@app.post(
    "/g4/loi-template",
    tags=["G4 고객검증"],
    summary="LoI(도입의향서) 표준 양식 자동 생성",
)
def generate_loi_template(req: StageRequest, _: dict = Depends(require_auth)):
    """저장된 인터뷰 데이터 + 직접 입력값으로 LoI 초안 자동 생성.
    loi_count 또는 poc_requests가 1 이상이어야 생성됨.
    """
    from agents.g4_customer_validator import CustomerValidator
    tech_id = req.tech_id
    d = dict(req.input_data)

    # 저장된 인터뷰 병합
    if tech_id in _interview_store:
        stored = _interview_store[tech_id]
        d.setdefault("interviews", stored)
        meta = _interview_meta.get(tech_id, {})
        d.setdefault("loi_count", meta.get("loi_count", 0))
        d.setdefault("poc_requests", meta.get("poc_requests", 0))

    loi_count = d.get("loi_count", 0)
    poc_req   = d.get("poc_requests", 0)
    if loi_count < 1 and poc_req < 1:
        raise HTTPException(
            status_code=422,
            detail="LoI 또는 PoC 요청이 최소 1건 이상 필요합니다. "
                   "POST /g4/interviews 로 먼저 loi_count를 업데이트하세요."
        )

    template = CustomerValidator()._generate_loi_template(d)
    return {"tech_id": tech_id, "loi_template": template}


# ═══════════════════════════════════════════════════════════
# SMK 파이프라인 통합 엔드포인트
# ═══════════════════════════════════════════════════════════

@app.post(
    "/service/smk-from-pipeline",
    tags=["서비스 산출물"],
    summary="G3+G4+G5 통합 SMK 자동 생성",
)
def generate_smk_from_pipeline(req: StageRequest, _: dict = Depends(require_auth)):
    """G3 시장조사·G4 고객검증·G5 BM 결과를 통합해 SMK 생성.
    input_data에 g3_output·g4_output·g5_output(각 stage output_doc) 포함 가능.
    없으면 input_data 직접 값으로 SMK 생성.
    """
    from agents.smk_generator import SMKGenerator
    d = dict(req.input_data)
    tech_id = req.tech_id

    # G4 저장 인터뷰 자동 반영
    if tech_id in _interview_store:
        meta = _interview_meta.get(tech_id, {})
        d.setdefault("g4_loi_count",    meta.get("loi_count", 0))
        d.setdefault("g4_poc_requests", meta.get("poc_requests", 0))

    # G3 output 병합
    g3 = d.pop("g3_output", {})
    if g3:
        d.setdefault("tam_usd",          g3.get("market_sizing", {}).get("tam_usd", 0))
        d.setdefault("sam_usd",          g3.get("market_sizing", {}).get("sam_usd", 0))
        d.setdefault("growth_rate_pct",  g3.get("market_sizing", {}).get("cagr_pct", 15))
        d.setdefault("industry_sector",  g3.get("industry", ""))

    # G5 output 병합
    g5 = d.pop("g5_output", {})
    if g5:
        d.setdefault("value_proposition",    g5.get("business_model_canvas", {}).get("value_proposition", ""))
        d.setdefault("g5_competitive_position", g5.get("competitive_landscape", {}).get("position", "new_entrant"))
        d.setdefault("g5_gtm_strategy",      g5.get("gtm_strategy", {}))
        d.setdefault("bm_output",            g5)
        rev_streams = g5.get("business_model_canvas", {}).get("revenue_streams", {})
        if rev_streams:
            d.setdefault("revenue_model", list(rev_streams.keys())[0])

    result = SMKGenerator().assess(d)
    return {"tech_id": tech_id, "stage": result.stage,
            "score": result.score, "gate": result.gate,
            "smk": result.output_doc}
