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

app = FastAPI(
    title="IPInsight 글로벌 기술사업화 Agent OS",
    description="G0~G10 전주기 기술사업화 프로세스 자동화 — WIPO·TRL·I-Corps·ARL·MRL 통합",
    version="1.0.0",
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
