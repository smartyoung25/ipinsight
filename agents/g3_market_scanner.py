"""G3 시장성·산업매력도 평가 — EIC Transition + Porter 5 Forces"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult


class MarketScanner(BaseAgent):
    stage_id = "G3"
    stage_name = "시장성·산업매력도 평가"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data: tech_name, target_market, tam_usd, sam_usd, som_usd,
                    growth_rate_pct, competitors (list), entry_barriers (list),
                    substitute_technologies (list)
        """
        score = self._score(input_data)
        gate = self._gate_from_score(score)
        output_doc = self._build_output(input_data, score)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output_doc,
            next_actions=self._next_actions(gate, input_data),
        )

    def _score(self, d: dict) -> float:
        score = 0.0
        # TAM 규모 (25점)
        tam = d.get("tam_usd", 0)
        if tam >= 1_000_000_000:
            score += 25
        elif tam >= 100_000_000:
            score += 18
        elif tam >= 10_000_000:
            score += 10
        # 성장률 (20점)
        growth = d.get("growth_rate_pct", 0)
        score += min(20, growth * 2)
        # 경쟁 강도 역산 (20점) — 경쟁자 수가 적을수록 유리
        competitors = d.get("competitors", [])
        comp_count = len(competitors)
        score += max(0, 20 - comp_count * 3)
        # SOM 설정 여부 (20점)
        score += 20 if d.get("som_usd", 0) > 0 else 0
        # 진입장벽 명시 (15점)
        score += 15 if d.get("entry_barriers") else 0
        return round(min(score, 100), 1)

    def _build_output(self, d: dict, score: float) -> dict:
        tam = d.get("tam_usd", 0)
        sam = d.get("sam_usd", 0)
        som = d.get("som_usd", 0)

        llm_result = self._llm(
            f"기술: {d.get('tech_name', '')}\n"
            f"목표시장: {d.get('target_market', '')}\n"
            f"경쟁자: {d.get('competitors', [])}\n"
            f"대체기술: {d.get('substitute_technologies', [])}\n\n"
            "Porter 5 Forces 분석과 진입전략을 JSON으로:\n"
            '{"rivalry":"low/med/high","supplier_power":"","buyer_power":"",'
            '"new_entrant_threat":"","substitute_threat":"","entry_strategy":""}',
            system="시장분석 전문가. JSON만 반환."
        )
        try:
            import json
            porter = json.loads(llm_result)
        except Exception:
            porter = {"rivalry": "medium", "entry_strategy": llm_result}

        # 산업매력도 점수 (0~10)
        attractiveness = round(score / 10, 1)

        return {
            "market_analysis": {
                "target_market": d.get("target_market", ""),
                "tam_usd": tam,
                "sam_usd": sam,
                "som_usd": som,
                "tam_sam_ratio": round(sam / tam, 3) if tam > 0 else 0,
                "sam_som_ratio": round(som / sam, 3) if sam > 0 else 0,
                "growth_rate_pct": d.get("growth_rate_pct", 0),
                "market_attractiveness_score": attractiveness,
            },
            "competitive_landscape": {
                "competitor_count": len(d.get("competitors", [])),
                "competitors": d.get("competitors", []),
                "entry_barriers": d.get("entry_barriers", []),
                "substitute_technologies": d.get("substitute_technologies", []),
            },
            "porter_5_forces": porter,
            "priority_markets": self._priority_markets(d),
            "market_score": score,
        }

    def _priority_markets(self, d: dict) -> list[dict]:
        """TAM 기반 진입 우선순위 시장 추천"""
        base_market = d.get("target_market", "")
        return [
            {"market": base_market, "priority": 1, "rationale": "Beachhead 시장"},
            {"market": "인접시장 A (추가 분석 필요)", "priority": 2, "rationale": "확장 후보"},
        ]

    def _next_actions(self, gate: str, d: dict) -> list[str]:
        if gate == "Go":
            return [
                "G4 고객발견 진행 (I-Corps 방법론, 인터뷰 30건 이상)",
                f"Beachhead 시장 확정: {d.get('target_market', '')}",
                "주요 경쟁사 3개사 딥다이브 분석",
            ]
        if gate == "Hold":
            return [
                "TAM/SAM/SOM 추정 근거 보강",
                "세부 고객군(Micro-segment) 재정의",
                "경쟁사 차별화 전략 수립",
            ]
        return [
            "시장 부재 또는 과포화 — 적용시장 재정의",
            "니치 마켓 또는 신규 시장 창출 전략 검토",
        ]
