"""G6 IP·기술 가치평가 — DCF·로열티역산·Real Option·Monte Carlo"""
from __future__ import annotations
import math
import random
from .base_agent import BaseAgent, StageResult


class ValuationEngine(BaseAgent):
    stage_id = "G6"
    stage_name = "IP·기술 가치평가"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data: tech_name, industry_sector, revenue_forecast (list of annual USD),
                    discount_rate_pct, royalty_rate_pct, tech_contribution_pct,
                    patent_remaining_years, risk_adjustment_pct, monte_carlo_runs
        """
        dcf_val = self._dcf(input_data)
        royalty_val = self._royalty(input_data)
        real_option_val = self._real_option(input_data)
        mc_result = self._monte_carlo(input_data)

        # 가중 평균 (DCF 40%, 로열티 35%, Real Option 25%)
        weighted_val = dcf_val * 0.4 + royalty_val * 0.35 + real_option_val * 0.25

        score = self._score(input_data, weighted_val)
        gate = self._gate_from_score(score)

        output_doc = {
            "tech_valuation_report": {
                "tech_name": input_data.get("tech_name", ""),
                "dcf_value_usd": round(dcf_val, 0),
                "royalty_value_usd": round(royalty_val, 0),
                "real_option_value_usd": round(real_option_val, 0),
                "weighted_value_usd": round(weighted_val, 0),
                "value_range_usd": {
                    "low": round(mc_result["p10"], 0),
                    "mid": round(mc_result["p50"], 0),
                    "high": round(mc_result["p90"], 0),
                },
                "methodology": "DCF 40% + 로열티역산 35% + Real Option 25%",
            },
            "ip_valuation": {
                "patent_remaining_years": input_data.get("patent_remaining_years", 0),
                "royalty_rate_pct": input_data.get("royalty_rate_pct", 0),
                "tech_contribution_pct": input_data.get("tech_contribution_pct", 0),
                "royalty_benchmarks": self._get_royalty_benchmark(input_data.get("industry_sector", "")),
            },
            "investment_review": {
                "npv_usd": round(dcf_val, 0),
                "irr_pct": self._estimate_irr(input_data),
                "payback_years": self._payback(input_data),
                "sensitivity": self._sensitivity(input_data),
            },
            "risk_adjusted_value": {
                "base_value_usd": round(weighted_val, 0),
                "risk_adjustment_pct": input_data.get("risk_adjustment_pct", 30),
                "risk_adjusted_usd": round(weighted_val * (1 - input_data.get("risk_adjustment_pct", 30) / 100), 0),
            },
            "monte_carlo_simulation": mc_result,
            "valuation_score": score,
        }

        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output_doc,
            next_actions=self._next_actions(gate, weighted_val),
        )

    def _dcf(self, d: dict) -> float:
        forecasts = d.get("revenue_forecast", [])
        r = d.get("discount_rate_pct", 15) / 100
        tech_contrib = d.get("tech_contribution_pct", 30) / 100
        total = 0.0
        for t, rev in enumerate(forecasts, 1):
            total += (rev * tech_contrib) / ((1 + r) ** t)
        return max(total, 0)

    def _royalty(self, d: dict) -> float:
        forecasts = d.get("revenue_forecast", [])
        royalty_rate = d.get("royalty_rate_pct", 3) / 100
        r = d.get("discount_rate_pct", 15) / 100
        years = min(d.get("patent_remaining_years", 10), len(forecasts))
        total = 0.0
        for t, rev in enumerate(forecasts[:years], 1):
            total += (rev * royalty_rate) / ((1 + r) ** t)
        return max(total, 0)

    def _real_option(self, d: dict) -> float:
        # Black-Scholes 간략화: 옵션가치 = 기술가치 × 변동성 조정
        base = self._dcf(d)
        volatility = 0.4  # 기술사업화 표준 변동성
        T = d.get("patent_remaining_years", 5)
        option_premium = base * volatility * math.sqrt(T) * 0.3
        return base + option_premium

    def _monte_carlo(self, d: dict) -> dict:
        runs = d.get("monte_carlo_runs", 1000)
        results = []
        base = self._dcf(d)
        for _ in range(runs):
            # 매출 성장률 ±30% 변동, 할인율 ±20% 변동
            revenue_shock = random.gauss(1.0, 0.3)
            discount_shock = random.gauss(1.0, 0.2)
            val = base * revenue_shock / discount_shock
            results.append(max(val, 0))
        results.sort()
        n = len(results)
        return {
            "runs": runs,
            "p10": results[int(n * 0.1)],
            "p50": results[int(n * 0.5)],
            "p90": results[int(n * 0.9)],
            "mean": sum(results) / n,
        }

    def _score(self, d: dict, val: float) -> float:
        score = 0.0
        # 가치 규모 (40점)
        if val >= 10_000_000:
            score += 40
        elif val >= 1_000_000:
            score += 28
        elif val >= 100_000:
            score += 15
        # 재무 가정 완성도 (35점)
        score += 15 if d.get("revenue_forecast") else 0
        score += 10 if d.get("discount_rate_pct") else 0
        score += 10 if d.get("royalty_rate_pct") else 0
        # 리스크 조정 반영 (25점)
        score += 25 if d.get("risk_adjustment_pct") else 0
        return round(min(score, 100), 1)

    def _get_royalty_benchmark(self, sector: str) -> dict:
        kb = self._load_knowledge("royalty_benchmarks.json")
        for ind in kb.get("industries", []):
            if sector.lower() in ind.get("sector", "").lower():
                return ind.get("royalty_rate_pct", {})
        return {"min": 2, "typical": 4, "max": 8}

    def _estimate_irr(self, d: dict) -> float:
        forecasts = d.get("revenue_forecast", [])
        contrib = d.get("tech_contribution_pct", 30) / 100
        if not forecasts:
            return 0.0
        annual_return = sum(forecasts) * contrib / len(forecasts)
        initial_investment = forecasts[0] * 0.2 if forecasts else 1
        return round(annual_return / max(initial_investment, 1) * 100, 1)

    def _payback(self, d: dict) -> float:
        forecasts = d.get("revenue_forecast", [])
        contrib = d.get("tech_contribution_pct", 30) / 100
        investment = d.get("investment_usd", 500_000)
        cumulative = 0.0
        for t, rev in enumerate(forecasts, 1):
            cumulative += rev * contrib
            if cumulative >= investment:
                return float(t)
        return float(len(forecasts) + 1)

    def _sensitivity(self, d: dict) -> dict:
        base = self._dcf(d)
        return {
            "revenue_up10pct": round(base * 1.1, 0),
            "revenue_down10pct": round(base * 0.9, 0),
            "discount_rate_up2pct": round(base * 0.85, 0),
            "royalty_rate_up1pct": round(base * 1.15, 0),
        }

    def _next_actions(self, gate: str, val: float) -> list[str]:
        if gate == "Go":
            return [
                "G7 PoC·실증 계획 수립",
                f"기술가치 ${val:,.0f} 기반 투자자 IR 자료 준비",
                "라이선싱 협상 시 제시가격 하한선 설정",
            ]
        if gate == "Hold":
            return [
                "매출 예측 가정 재검토",
                "기술기여도(%) 전문가 검증 의뢰",
                "유사 거래사례 추가 조사",
            ]
        return [
            "경제성 부족 — 수익모델 재설계 또는 원가절감 방안 검토",
            "G5 BM 설계 재실시",
        ]
