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

        # 산출물 저장
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

    def run_pipeline(self, stage_inputs: dict[int, dict], stop_on_kill: bool = True) -> dict:
        """
        G0~G10 순차 실행.
        stage_inputs: {0: {...}, 1: {...}, ...}
        stop_on_kill: Kill 판정 시 파이프라인 중단 여부
        """
        summary = {
            "tech_id": self.tech_id,
            "start_time": datetime.now().isoformat(),
            "stages": [],
            "final_gate": "Go",
            "killed_at": None,
        }

        for stage_num in sorted(STAGE_AGENTS.keys()):
            if stage_num not in stage_inputs:
                continue

            result = self.run_stage(stage_num, stage_inputs[stage_num])

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

        # 전체 파이프라인 요약 저장
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
