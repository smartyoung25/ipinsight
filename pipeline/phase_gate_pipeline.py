"""G0~G10 Stage Gate Pipeline — 전주기 기술사업화 실행"""
from __future__ import annotations
import json
import os
from pathlib import Path
from datetime import datetime

from agents import (
    TechScout, IPStructurer, TRLAssessor, MarketScanner,
    CustomerValidator, BMDesigner, ValuationEngine, PoCManager,
    MRLARLAssessor, DealStructurer, PerformanceTracker,
)
from agents.base_agent import StageResult

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"

STAGE_AGENTS = {
    0: TechScout,
    1: IPStructurer,
    2: TRLAssessor,
    3: MarketScanner,
    4: CustomerValidator,
    5: BMDesigner,
    6: ValuationEngine,
    7: PoCManager,
    8: MRLARLAssessor,
    9: DealStructurer,
    10: PerformanceTracker,
}

STAGE_NAMES = {
    0: "G0_기술발굴",
    1: "G1_IP구조화",
    2: "G2_TRL평가",
    3: "G3_시장성",
    4: "G4_고객검증",
    5: "G5_BM설계",
    6: "G6_가치평가",
    7: "G7_PoC실증",
    8: "G8_MRL_ARL",
    9: "G9_거래투자",
    10: "G10_성과관리",
}

# 단계 결과 → 다음 단계 입력 자동 전달 맵
# key: 완료된 stage_num, value: StageResult → 추가 입력 dict 변환 함수
_STAGE_OUTPUT_MAP: dict[int, object] = {
    3: lambda r: {  # G3 시장성 → G4 고객검증
        "market_size_usd": r.output_doc.get("market_analysis", {}).get("tam_usd", 0),
        "target_segments": r.output_doc.get("market_analysis", {}).get("segments", []),
        "industry_sector": r.output_doc.get("industry", ""),
    },
    4: lambda r: {  # G4 고객검증 → G5 BM설계
        "loi_count": (
            len(r.output_doc.get("loi_template", {}).get("signatories", []))
            if isinstance(r.output_doc.get("loi_template"), dict)
            else r.output_doc.get("loi_count", 0)
        ),
        "poc_requests": r.output_doc.get("poc_requests", 0),
        "jtbd_summary": r.output_doc.get("jtbd_summary", ""),
        "validated_segments": r.output_doc.get("validated_segments", []),
        "interview_count": r.output_doc.get("interview_count", 0),
    },
    5: lambda r: {  # G5 BM설계 → G6 가치평가
        "revenue_model": r.output_doc.get("revenue_streams", []),
        "tam_usd": r.output_doc.get("market_size", {}).get("tam_usd", 0),
        "unit_economics": r.output_doc.get("unit_economics", {}),
        "business_model_type": r.output_doc.get("canvas", {}).get("model_type", ""),
    },
    6: lambda r: {  # G6 가치평가 → G7 PoC
        "valuation_usd": r.output_doc.get("valuation_usd", 0),
        "target_irr": r.output_doc.get("irr_pct", 15),
    },
    7: lambda r: {  # G7 PoC → G8 MRL/ARL
        "poc_results": r.output_doc.get("poc_results", {}),
        "trl_achieved": r.output_doc.get("trl_achieved", 0),
    },
    8: lambda r: {  # G8 MRL/ARL → G9 거래
        "mrl": r.output_doc.get("mrl_score", 0),
        "arl": r.output_doc.get("arl_score", 0),
        "bottleneck_dimension": r.output_doc.get("bottleneck", ""),
    },
    9: lambda r: {  # G9 거래 → G10 성과관리
        "deal_structure": r.output_doc.get("deal_structure", {}),
        "royalty_rate": r.output_doc.get("royalty_rate_pct", 5),
    },
}


class PhaseGatePipeline:
    def __init__(self, tech_id: str):
        self.tech_id = tech_id
        self.output_dir = OUTPUT_DIR / tech_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: dict[int, StageResult] = {}
        self.pipeline_log: list[dict] = []

    def run_stage(self, stage_num: int, input_data: dict) -> StageResult:
        """단일 단계 실행"""
        if stage_num not in STAGE_AGENTS:
            raise ValueError(f"유효하지 않은 단계: {stage_num}. 0~10 사이여야 합니다.")

        agent_cls = STAGE_AGENTS[stage_num]
        agent = agent_cls()
        result = agent.assess(input_data)
        self.results[stage_num] = result

        output_path = self.output_dir / f"{STAGE_NAMES[stage_num]}_result.json"
        output_path.write_text(result.to_json(), encoding="utf-8")

        self.pipeline_log.append({
            "stage": stage_num,
            "stage_name": STAGE_NAMES[stage_num],
            "score": result.score,
            "gate": result.gate,
            "timestamp": datetime.now().isoformat(),
        })

        return result

    def run_pipeline(
        self,
        stage_inputs: dict[int, dict],
        stop_on_kill: bool = True,
        auto_chain: bool = True,
    ) -> dict:
        """
        G0~G10 순차 실행.
        stage_inputs: {0: {...}, 1: {...}, ...}
        stop_on_kill: Kill 판정 시 파이프라인 중단
        auto_chain:   True이면 이전 단계 결과를 다음 단계 입력에 자동 병합 (_STAGE_OUTPUT_MAP)
        """
        summary = {
            "tech_id": self.tech_id,
            "start_time": datetime.now().isoformat(),
            "stages": [],
            "final_gate": "Go",
            "killed_at": None,
            "auto_chain": auto_chain,
        }

        for stage_num in sorted(STAGE_AGENTS.keys()):
            if stage_num not in stage_inputs:
                continue

            input_data = dict(stage_inputs[stage_num])

            # 이전 단계 결과 자동 병합 (auto_chain=True, 명시 입력 우선)
            if auto_chain and stage_num > 0:
                prev = stage_num - 1
                if prev in self.results and prev in _STAGE_OUTPUT_MAP:
                    try:
                        carried = _STAGE_OUTPUT_MAP[prev](self.results[prev])
                        for k, v in carried.items():
                            if k not in input_data:  # 명시 입력이 없을 때만 적용
                                input_data[k] = v
                    except Exception:
                        pass

            result = self.run_stage(stage_num, input_data)

            stage_summary = {
                "stage": stage_num,
                "name": STAGE_NAMES[stage_num],
                "score": result.score,
                "gate": result.gate,
                "warnings": result.warnings,
                "next_actions": result.next_actions[:2],
            }
            summary["stages"].append(stage_summary)

            if result.gate == "Kill" and stop_on_kill:
                summary["final_gate"] = "Kill"
                summary["killed_at"] = stage_num
                break
            elif result.gate == "Hold":
                summary["final_gate"] = "Hold"

        summary["end_time"] = datetime.now().isoformat()

        summary_path = self.output_dir / "pipeline_summary.json"
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        return summary

    def get_result(self, stage_num: int) -> StageResult | None:
        return self.results.get(stage_num)

    def get_all_results(self) -> dict:
        return {
            stage: result.to_dict()
            for stage, result in self.results.items()
        }
