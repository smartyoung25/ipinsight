"""R1~R9 보고서 엔드포인트

의존성 그래프: api/report_deps.py
LLM 프롬프트: R1은 buildR1Prompt 기반, R2~R9는 간소화 형태

엔드포인트:
  POST /reports/generate        : 단일 보고서 생성
  GET  /reports/availability    : R1~R9 가용성 체크
  GET  /reports/{report_id}     : 저장된 보고서 조회
  POST /reports/cascade-stale   : 보고서 stale 전파
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth import require_auth
from api.report_deps import (
    ALL_REPORTS, REPORT_DEFS,
    get_all_availability, check_availability, mark_stale_cascade,
)

router = APIRouter(prefix="/reports", tags=["reports"])

# 인메모리 보고서 저장소 (빠른 조회용, DB가 영속 저장)
_report_store: dict[str, dict[str, Any]] = {}

from api.services.report_pipeline import (
    build_store_a_from_pcml, build_store_b_from_scr, build_store_d_from_context,
    recommend_reports, generate_report_content,
    save_report, list_reports, get_report_by_db_id, get_latest_report,
    save_pipeline_run, list_pipeline_runs, REPORT_META,
)


# ─── 요청/응답 스키마 ─────────────────────────────────

class ReportRequest(BaseModel):
    tech_id: str = Field(..., description="기술/특허 ID")
    report_id: str = Field(..., description="R1_investment | R2_enforcement | ... | R9_sps")
    tier: str = Field("FULL", description="FREE | LITE | FULL")
    store_a: dict[str, Any] = Field(default_factory=dict, description="PCML 결과 (StoreA)")
    store_b: dict[str, Any] = Field(default_factory=dict, description="SCR 결과 (StoreB)")
    store_d: dict[str, Any] = Field(default_factory=dict, description="사용자 컨텍스트 (StoreD)")
    dep_reports: dict[str, Any] = Field(default_factory=dict, description="의존 보고서 결과")


class AvailabilityRequest(BaseModel):
    completed: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="완료된 보고서 맵 {report_id: {status, pcml_v, scr_v}}"
    )
    has_store_a: bool = Field(True)
    has_store_b: bool = Field(True)
    pcml_version: int = Field(0)
    screening_version: int = Field(0)


class CascadeStaleRequest(BaseModel):
    completed: dict[str, dict[str, Any]] = Field(default_factory=dict)
    changed_report_id: str = Field(..., description="갱신된 보고서 ID")


# ─── 프롬프트 빌더 ────────────────────────────────────

_REPORT_ROLES = {
    "R1_investment": "PQE-R1 Enhanced v3 투자·인수 심사 보고서 분석가",
    "R2_enforcement": "PQE-R2 권리행사·분쟁 전략 보고서 분석가",
    "R3_commercialize": "PQE-R3 사업화·연구개발 실행 보고서 분석가",
    "R4_portfolio": "PQE-R4 포트폴리오·대외 제출 보고서 분석가",
    "R5_valuation": "PQE-R5 v3 기술가치평가(Technology Valuation) 분석가",
    "R6_ir": "PQE-R6 투자자 IR 브리프 분석가",
    "R7_license": "PQE-R7 라이선스·기술이전 준비도 보고서 분석가",
    "R8_gov_ir": "PQE-R8 정부지원/IR 제출 보고서 분석가",
    "R9_sps": "PQE-R9 선행기술조사(SPS) 보고서 분석가",
}

_REPORT_DESCRIPTIONS = {
    "R1_investment": """10개 블록 강제 출력 + FREE/LITE/FULL 계층 + KPI1~10 단계 계산 + NPV 3시나리오 + Hard Stop 5항목 + 90일 Action Plan.
블록 순서: 1.상태 2.입력요약 3.분석범위 4.청구항파싱 5.구성요소맵 6.구조지표 7.KPI 8.투자심사해석 9.진단 10.다음조치
FULL에서만: 시장평가(TAM/SAM/SOM) · NPV 3시나리오 · Hard Stop 5항목 완전분석 · 90일 Action Plan 15개 · 투자결론""",

    "R2_enforcement": """권리행사·분쟁 전략 보고서. PCML 6지표 활용.
핵심 출력: 분쟁전략(공격/방어/협상) · 경쟁특허 Tier 1~3 · Key Passages · NPV · 라이선스 조건
FULL에서만: §101 분석 · 무효화 위험 · 분쟁비용 NPV · 협상 조건 Term Sheet""",

    "R3_commercialize": """사업화·연구개발 실행 보고서. TRL 로드맵 + BM.
핵심 출력: TRL 현재→목표 로드맵 · BM 4가지(라이선싱/매각/직접사업화/JV) · 파트너십 Tier A/B/C
FULL에서만: White Space 출원전략 · R&D 과제 5개 · 예산·일정""",

    "R4_portfolio": """포트폴리오·대외 제출 보고서.
핵심 출력: Asset Tier(Core/Defensive/Peripheral) · PQE 점수 · HHI · Landscape 분석
FULL에서만: IR/정부과제/기술이전 3가지 메시지 · 포트폴리오 최적화 권고""",

    "R5_valuation": """기술가치평가 보고서. 3접근법(수익·시장·원가) + TCF + WACC.
국제기준: WIPO IP Valuation Guidelines(2023) · KIIP · ISO 10668:2010 · OECD TP · US IRS Rev.Rul.59-60
블록 8 9서브(FULL): (1)시장세그먼트 3개×TAM/SAM/SOM (2)수익접근법 NPV 3시나리오 (3)3개년 매출×4스트림
(4)비용구체화 (5)시장접근법 비교사례 3건 (6)원가접근법 재현 (7)TCF KIIP/OECD (8)WACC (9)수명주기 교차검증""",

    "R6_ir": """투자자 IR 브리프. R5 연계 권장.
핵심 출력: PCML 7지표 투자자 언어 번역 · 기술/시장 경쟁력 근거 · IR Deck 4문장 · 투자 포인트 3가지""",

    "R7_license": """라이선스·기술이전 준비도 보고서. R5+R2 연계 권장.
핵심 출력: 거래 준비도(1~5단계) · 후보군 세그멘테이션(Tier A/B/C) · BM×거래방식 매트릭스
FULL에서만: Term Sheet 10항목 · 실시료 산출식 · 리스크 할인율 근거""",

    "R8_gov_ir": """정부지원/IR 제출용 요약 보고서. R1 또는 R2 연계 권장.
핵심 출력: 기술보증 적합성 · 과제신청 핵심 메시지 · 투자유치 요약(Executive Summary 1page)""",

    "R9_sps": """선행기술조사(SPS) 보고서. SCR 스크리닝과 연계.
핵심 출력: 선행기술 인용목록 · 신규성/진보성 상세분석 · §102/§103 위험도 · White Space 지도""",
}


def _build_report_prompt(req: ReportRequest) -> str:
    role = _REPORT_ROLES.get(req.report_id, "IPInsight 보고서 분석가")
    description = _REPORT_DESCRIPTIONS.get(req.report_id, "")
    defn = REPORT_DEFS.get(req.report_id)
    label = defn.label if defn else req.report_id

    tier_label = {"FULL": "FULL ₩300,000", "LITE": "LITE ₩100,000", "FREE": "FREE 무료"}.get(req.tier, req.tier)
    is_full = req.tier == "FULL"

    return f"""[ROLE]
당신은 IIAMHUB IPinsight {role}입니다.

[REPORT]
{label} — {tier_label}

[DESCRIPTION]
{description}

[TIER]
{"FULL: 전체 블록 완전 출력. 수치 산출식·conf. 모두 포함." if is_full else "LITE: 블록 요약 출력. 예비 점수·방향성만." if req.tier == "LITE" else "FREE: 핵심 KPI 3개·방향성만. 잠금 처리."}

[INPUT — Store A (PCML)]
{json.dumps(req.store_a, ensure_ascii=False, indent=2) if req.store_a else "없음"}

[INPUT — Store B (SCR)]
{json.dumps(req.store_b, ensure_ascii=False, indent=2) if req.store_b else "없음"}

[INPUT — Store D (사용자 컨텍스트)]
{json.dumps(req.store_d, ensure_ascii=False, indent=2) if req.store_d else "없음 — 시장 데이터 추정 + (추정, conf.X.XX) 표시"}

[INPUT — 의존 보고서]
{json.dumps(req.dep_reports, ensure_ascii=False, indent=2) if req.dep_reports else "없음"}

[ABSOLUTE PROHIBITIONS]
① 원문에 없는 구성요소·관계·효과·수치 생성 금지
② 계산 불가 상황에서 숫자 꾸며내기 금지 — N/A 처리
③ 근거 없는 법률·시장·가치 결론 단정 금지 — (추정, conf.X.XX) 표시
④ 블록 순서 변경 또는 번호 생략 금지

[OUTPUT SCHEMA]
JSON 형식으로 출력:
{{
  "reportId": "IAH-2026-{req.tech_id}-{req.report_id}-{req.tier}",
  "reportType": "{req.report_id}",
  "tier": "{req.tier}",
  "tech_id": "{req.tech_id}",
  "keyFindings": ["string - 핵심 결론 3가지"],
  "sections": ["string - 블록 목록"],
  "content": "string - 마크다운 전체 보고서",
  "structuredData": {{}}
}}

[마크다운 출력 규칙]
- ## 블록 1 … → ## 블록 2 … 순서 고정
- 역순·건너뛰기·중복 금지
- 투자결론·Executive Summary 등 부가 섹션은 마지막 블록 다음에만
- 한글(영문) 병기 형식 준수
- 조사자 정보·면책 조항 마지막에 기재
"""


def _rule_fallback_report(req: ReportRequest) -> dict:
    """LLM 없을 때 최소 골격 반환."""
    defn = REPORT_DEFS.get(req.report_id)
    return {
        "reportId": f"IAH-2026-{req.tech_id}-{req.report_id}-{req.tier}",
        "reportType": req.report_id,
        "tier": req.tier,
        "tech_id": req.tech_id,
        "keyFindings": ["LLM 키 미설정 — 규칙 기반 폴백"],
        "sections": [],
        "content": f"# {defn.label if defn else req.report_id}\n\nLLM 미사용 — `ANTHROPIC_API_KEY` 설정 후 재생성 가능.",
        "structuredData": {},
        "_fallback": True,
    }


def _call_llm(prompt: str) -> dict:
    """LLM 호출 + JSON 추출."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=16000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        m = re.search(r"\{[\s\S]+\}", raw)
        if m:
            return json.loads(m.group())
    except Exception:
        pass
    return {}


# ─── 엔드포인트 ──────────────────────────────────────

@router.post("/generate")
def generate_report(req: ReportRequest, _: dict = Depends(require_auth)):
    """단일 보고서를 생성하고 인메모리 스토어에 저장한다."""
    if req.report_id not in ALL_REPORTS:
        raise HTTPException(status_code=400, detail=f"알 수 없는 보고서 ID: {req.report_id}")

    # 의존성 체크 (store에서 완료 여부 확인)
    completed_map = {
        rid: {"status": "completed"}
        for rid in _report_store
        if _report_store[rid].get("status") == "completed"
    }
    avail = check_availability(req.report_id, completed_map)
    if not avail.available:
        missing_info = []
        if avail.missing_deps:
            missing_info.append(f"선행 보고서 필요: {avail.missing_deps}")
        if avail.missing_or_deps:
            missing_info.append(f"OR 조건 미충족: {avail.missing_or_deps}")
        raise HTTPException(
            status_code=422,
            detail=f"보고서 생성 불가 — {'; '.join(missing_info)}",
        )

    # LLM 호출 또는 폴백
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        prompt = _build_report_prompt(req)
        result = _call_llm(prompt)
        if not result:
            result = _rule_fallback_report(req)
    else:
        result = _rule_fallback_report(req)

    # 저장
    store_key = f"{req.tech_id}:{req.report_id}"
    _report_store[store_key] = {
        **result,
        "status": "completed",
        "pcml_v": req.store_a.get("_version", 0),
        "scr_v": req.store_b.get("_version", 0),
    }

    return result


@router.post("/availability")
def check_report_availability(req: AvailabilityRequest, _: dict = Depends(require_auth)):
    """R1~R9 전체 가용성을 체크해 Tier 순으로 반환한다."""
    results = get_all_availability(
        req.completed,
        req.has_store_a,
        req.has_store_b,
        req.pcml_version,
        req.screening_version,
    )
    return [
        {
            "report_id": r.report_id,
            "label": r.label,
            "tier": r.tier,
            "available": r.available,
            "completed": r.completed,
            "stale": r.stale,
            "missing_deps": r.missing_deps,
            "missing_or_deps": r.missing_or_deps,
            "missing_stores": r.missing_stores,
        }
        for r in results
    ]


@router.get("/{report_id}")
def get_report(report_id: str, tech_id: str, _: dict = Depends(require_auth)):
    """저장된 보고서를 조회한다."""
    key = f"{tech_id}:{report_id}"
    if key not in _report_store:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없음")
    return _report_store[key]


@router.post("/cascade-stale")
def cascade_stale(req: CascadeStaleRequest, _: dict = Depends(require_auth)):
    """보고서 갱신 시 의존 보고서를 stale 처리하고 목록을 반환한다."""
    if req.changed_report_id not in ALL_REPORTS:
        raise HTTPException(status_code=400, detail=f"알 수 없는 보고서 ID: {req.changed_report_id}")
    staled = mark_stale_cascade(req.completed, req.changed_report_id)
    return {
        "changed": req.changed_report_id,
        "staled": staled,
        "updated_completed": req.completed,
    }


@router.get("/definitions/all")
def get_report_definitions(_: dict = Depends(require_auth)):
    """R1~R9 보고서 정의 전체 반환."""
    return {
        rid: {
            "label": defn.label,
            "label_en": defn.label_en,
            "tier": defn.tier,
            "description": defn.description,
            "deps": defn.deps,
            "or_deps": defn.or_deps,
        }
        for rid, defn in REPORT_DEFS.items()
    }


# ─── 파이프라인 통합 엔드포인트 ──────────────────────────────────

class PipelineReportRequest(BaseModel):
    tech_id:    str   = Field(..., description="기술 ID")
    tech_name:  str   = Field("", description="기술명")
    input_text: str   = Field("", description="특허/기술 텍스트")
    trl:        int   = Field(4,  description="TRL 단계")
    report_ids: list[str] = Field(default_factory=list, description="생성할 보고서 목록 (빈 목록=추천 기반 자동)")
    tier:       str   = Field("LITE", description="FREE | LITE | FULL")
    store_a:    dict  = Field(default_factory=dict, description="PCML 결과 (없으면 자동 생성)")
    store_b:    dict  = Field(default_factory=dict, description="SCR 결과  (없으면 자동 생성)")
    extra:      dict  = Field(default_factory=dict, description="TAM/SAM/SOM 등 추가 컨텍스트")


@router.post("/pipeline", summary="분석→보고서 일괄 파이프라인")
def run_report_pipeline(req: PipelineReportRequest, _: dict = Depends(require_auth)):
    """
    1. PCML/SCR 결과가 없으면 입력 텍스트로 자동 분석
    2. 보고서 목록이 없으면 AI 추천
    3. 선택 보고서 생성 + SQLite 저장
    4. 전체 결과 반환
    """
    import time as _time

    # Step1: StoreA/B 구성
    store_a = req.store_a or {}
    store_b = req.store_b or {}

    if not store_a and req.input_text:
        # 간이 PCML 폴백 (실제 에이전트 없을 때)
        store_a = {
            "release_status": "internal_only",
            "pcml_score": 50,
            "claim_count": 0,
            "components": [],
            "strengths": ["텍스트 기반 분석"],
            "weaknesses": ["상세 PCML 분석 미수행"],
            "_version": int(_time.time()),
            "_source": "fallback",
        }

    if not store_b and req.input_text:
        store_b = {
            "gate": "Hold",
            "scr_score": 50,
            "white_space": [],
            "competitor_landscape": {"majorPlayers": []},
            "risk_factors": [],
            "_version": int(_time.time()),
            "_source": "fallback",
        }

    store_d = build_store_d_from_context(req.tech_name, req.trl, req.extra)

    # Step2: 보고서 추천
    recs = recommend_reports(store_a, store_b, req.trl)
    if req.report_ids:
        target_ids = req.report_ids
    else:
        target_ids = [r["id"] for r in recs[:3]]  # 기본 상위 3개

    # Step3: 보고서 생성 + 저장
    generated = []
    for rid in target_ids:
        content = generate_report_content(
            report_id=rid, tech_id=req.tech_id, tier=req.tier,
            store_a=store_a, store_b=store_b, store_d=store_d,
        )
        db_id = save_report(
            tech_id=req.tech_id, report_id=rid, tier=req.tier,
            content=content,
            pcml_score=store_a.get("pcml_score", 0),
            scr_score=store_b.get("scr_score", 0),
        )
        meta = REPORT_META.get(rid, {})
        generated.append({
            "db_id":      db_id,
            "report_id":  rid,
            "label":      meta.get("label", rid),
            "icon":       meta.get("icon", "📄"),
            "tier":       req.tier,
            "key_findings": content.get("keyFindings", []),
            "content_preview": (content.get("content", "")[:300] + "…"),
            "fallback":   content.get("_fallback", False),
        })
        # 인메모리에도 캐시
        _report_store[f"{req.tech_id}:{rid}"] = {**content, "status": "completed"}

    # Step4: 파이프라인 실행 기록
    run_id = save_pipeline_run(
        tech_id=req.tech_id, tech_name=req.tech_name,
        input_text=req.input_text[:500], trl=req.trl,
        store_a=store_a, store_b=store_b,
        reports=[r["report_id"] for r in generated],
    )

    return {
        "run_id":      run_id,
        "tech_id":     req.tech_id,
        "tech_name":   req.tech_name,
        "trl":         req.trl,
        "recommended": recs,
        "generated":   generated,
        "store_a_summary": {
            "pcml_score": store_a.get("pcml_score"),
            "release_status": store_a.get("release_status"),
            "source": store_a.get("_source", "provided"),
        },
        "store_b_summary": {
            "gate": store_b.get("gate"),
            "scr_score": store_b.get("scr_score"),
            "source": store_b.get("_source", "provided"),
        },
    }


@router.get("/db/list", summary="저장된 보고서 목록 조회")
def list_saved_reports(tech_id: str = "", _: dict = Depends(require_auth)):
    return list_reports(tech_id or None)


@router.get("/db/{db_id}", summary="DB 보고서 단건 조회")
def get_saved_report(db_id: str, _: dict = Depends(require_auth)):
    r = get_report_by_db_id(db_id)
    if not r:
        raise HTTPException(status_code=404, detail="보고서 없음")
    return r


@router.get("/runs/list", summary="파이프라인 실행 이력")
def list_runs(tech_id: str = "", _: dict = Depends(require_auth)):
    return list_pipeline_runs(tech_id or None)


@router.get("/history", summary="보고서·파이프라인 통합 이력 (최신순)")
def get_history(tech_id: str = "", limit: int = 50, _: dict = Depends(require_auth)):
    """pipeline_runs + reports를 통합하여 최신순으로 반환.
    각 항목에 type='pipeline_run' 또는 type='report' 포함.
    """
    runs = list_pipeline_runs(tech_id or None)
    reps = list_reports(tech_id or None)
    items = []
    for r in runs:
        items.append({
            "type": "pipeline_run",
            "id": r["id"],
            "tech_id": r["tech_id"],
            "tech_name": r.get("tech_name", ""),
            "status": r.get("status", ""),
            "created_at": r["created_at"],
            "summary": {
                "trl": r.get("trl"),
                "reports_generated": r.get("reports_generated", "[]"),
                "pcml_score": (r.get("store_a") and __import__("json").loads(r["store_a"]) or {}).get("pcml_score"),
                "scr_gate": (r.get("store_b") and __import__("json").loads(r["store_b"]) or {}).get("gate"),
            },
        })
    for r in reps:
        items.append({
            "type": "report",
            "id": r["id"],
            "tech_id": r["tech_id"],
            "report_id": r.get("report_id", ""),
            "tier": r.get("tier", ""),
            "status": r.get("status", ""),
            "created_at": r["created_at"],
            "summary": {
                "pcml_score": r.get("pcml_score"),
                "scr_score": r.get("scr_score"),
                "key_findings_count": len(__import__("json").loads(r["key_findings"] or "[]")),
            },
        })
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return {"items": items[:limit], "total": len(items)}


@router.get("/recommend", summary="입력 기반 보고서 추천")
def recommend(
    pcml_score: float = 50, scr_score: float = 50,
    gate: str = "Hold", trl: int = 4,
    _: dict = Depends(require_auth),
):
    store_a = {"pcml_score": pcml_score}
    store_b = {"scr_score": scr_score, "gate": gate}
    return recommend_reports(store_a, store_b, trl)
