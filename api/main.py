"""IPInsight 글로벌 기술사업화 Agent OS — FastAPI 엔드포인트"""
from __future__ import annotations
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import StageRequest, PipelineRequest, FundingMatchRequest
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

app = FastAPI(
    title="IPInsight IP Lifecycle × 글로벌 기술사업화 OS",
    description="G0~G10 전주기 + 4단계 IP 라이프사이클 통합 — WIPO·TRL·I-Corps·ARL·MRL·포트폴리오",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "IPInsight Agent OS", "version": "1.0.0"}


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
