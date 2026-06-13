"""G1-Maint: 특허 유지비 최적화 — 국가별 갱신료 vs 기술 가치 자동 판단
포트폴리오 각 특허의 유지·포기·이전 결정을 비용-편익 분석으로 지원.
"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# 주요 국가별 연차 유지료 기준 (USD, 출원 후 연도별 누적)
_RENEWAL_COSTS = {
    "KOR": {"annual_avg": 800,   "years": 20, "grace_period_months": 6},
    "USA": {"annual_avg": 2_200, "years": 20, "grace_period_months": 0},
    "EU":  {"annual_avg": 1_500, "years": 20, "grace_period_months": 6},
    "JPN": {"annual_avg": 1_200, "years": 20, "grace_period_months": 6},
    "CHN": {"annual_avg": 600,   "years": 20, "grace_period_months": 6},
    "IND": {"annual_avg": 300,   "years": 20, "grace_period_months": 6},
    "SGP": {"annual_avg": 500,   "years": 20, "grace_period_months": 6},
    "AUS": {"annual_avg": 900,   "years": 20, "grace_period_months": 6},
    "CAN": {"annual_avg": 700,   "years": 20, "grace_period_months": 6},
    "BRA": {"annual_avg": 400,   "years": 20, "grace_period_months": 12},
}

# 결정 기준
_DECISION_THRESHOLDS = {
    "maintain":   {"roi_min": 2.0, "strategic_score_min": 60},
    "transfer":   {"roi_min": 0.5, "strategic_score_min": 30},
    "abandon":    {"roi_max": 0.5, "strategic_score_max": 30},
}


class PatentMaintenanceOptimizer(BaseAgent):
    stage_id   = "G1-Maint"
    stage_name = "특허 유지비 최적화"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          portfolio (list of {
            patent_id: str,
            title: str,
            filing_year: int,
            countries: list[str],        # 등록 국가 코드
            remaining_years: int,        # 남은 존속 기간
            annual_licensing_revenue_usd: float,  # 로열티 등 연간 수익
            strategic_importance: int,   # 0~100 (핵심 특허일수록 높음)
            trl: int,
            competitor_blocking_value: float,  # 경쟁사 차단 가치 (연간)
            market_size_usd: float,
          }):
          annual_budget_usd (float): 유지비 연간 예산
          company_stage (str): early/growth/mature
        """
        portfolio = input_data.get("portfolio", [])
        decisions = [self._decide_patent(p, input_data) for p in portfolio]
        score     = self._score(decisions, input_data)
        gate      = self._gate_from_score(score)
        output    = self._build_output(input_data, decisions, score)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output,
            next_actions=self._next_actions(gate, decisions),
        )

    def _decide_patent(self, p: dict, global_d: dict) -> dict:
        countries   = p.get("countries", ["KOR"])
        rem_years   = p.get("remaining_years", 10)
        rev_annual  = p.get("annual_licensing_revenue_usd", 0)
        strategic   = p.get("strategic_importance", 50)
        block_val   = p.get("competitor_blocking_value", 0)

        # 연간 유지비 계산
        annual_cost = sum(
            _RENEWAL_COSTS.get(c, {"annual_avg": 800})["annual_avg"]
            for c in countries
        )
        total_remaining_cost = annual_cost * rem_years

        # 총 기대 가치
        total_value = (rev_annual + block_val) * rem_years

        # ROI
        roi = total_value / max(total_remaining_cost, 1)

        # 결정
        if roi >= _DECISION_THRESHOLDS["maintain"]["roi_min"] or strategic >= _DECISION_THRESHOLDS["maintain"]["strategic_score_min"]:
            decision = "유지"
            action   = "계속 갱신"
        elif roi >= _DECISION_THRESHOLDS["transfer"]["roi_min"] or strategic >= _DECISION_THRESHOLDS["transfer"]["strategic_score_min"]:
            decision = "이전/매각"
            action   = "기술이전 또는 포트폴리오 매각 추진"
        else:
            decision = "포기"
            action   = "다음 갱신 시 포기 — 비용 절감"

        # 최적화: 비핵심 국가 일부 포기
        country_optimization = []
        for c in countries:
            c_cost = _RENEWAL_COSTS.get(c, {"annual_avg": 800})["annual_avg"]
            c_value = (rev_annual + block_val) / max(len(countries), 1)
            c_roi   = c_value / max(c_cost, 1)
            country_optimization.append({
                "country": c,
                "annual_cost_usd": c_cost,
                "estimated_value_usd": round(c_value),
                "country_roi": round(c_roi, 2),
                "recommendation": "유지" if c_roi >= 1.5 else "포기 검토",
            })

        return {
            "patent_id":              p.get("patent_id", ""),
            "title":                  p.get("title", ""),
            "remaining_years":        rem_years,
            "countries":              countries,
            "annual_cost_usd":        round(annual_cost),
            "total_remaining_cost_usd": round(total_remaining_cost),
            "total_expected_value_usd": round(total_value),
            "roi":                    round(roi, 2),
            "strategic_importance":   strategic,
            "decision":               decision,
            "action":                 action,
            "country_optimization":   country_optimization,
        }

    def _score(self, decisions: list, d: dict) -> float:
        if not decisions:
            return 0.0
        budget  = d.get("annual_budget_usd", float("inf"))
        total_cost = sum(dec["annual_cost_usd"] for dec in decisions if dec["decision"] == "유지")
        within_budget = total_cost <= budget
        roi_avg = sum(dec["roi"] for dec in decisions) / len(decisions)
        maintain_cnt = sum(1 for dec in decisions if dec["decision"] == "유지")

        score = 0.0
        score += min(40, roi_avg * 15)
        score += 30 if within_budget else 10
        score += min(30, maintain_cnt * 8)
        return round(min(score, 100), 1)

    def _build_output(self, d: dict, decisions: list, score: float) -> dict:
        maintain = [dec for dec in decisions if dec["decision"] == "유지"]
        transfer = [dec for dec in decisions if dec["decision"] == "이전/매각"]
        abandon  = [dec for dec in decisions if dec["decision"] == "포기"]

        annual_savings = sum(dec["annual_cost_usd"] for dec in abandon + transfer)
        portfolio_roi  = (sum(dec["total_expected_value_usd"] for dec in maintain) /
                          max(sum(dec["total_remaining_cost_usd"] for dec in maintain), 1))

        llm_text = self._llm(
            f"포트폴리오 규모: {len(decisions)}건\n"
            f"유지: {len(maintain)}건 / 이전: {len(transfer)}건 / 포기: {len(abandon)}건\n"
            f"연간 절감액: ${annual_savings:,.0f}\n"
            f"포트폴리오 ROI: {portfolio_roi:.2f}\n\n"
            "특허 포트폴리오 최적화 전략 3가지를 JSON으로:\n"
            '{"optimization_tips":[]}',
            system="IP 포트폴리오 관리 전문가. 비용 대비 가치 극대화 전략. JSON 반환."
        )
        try:
            import json
            llm_out = json.loads(llm_text)
        except Exception:
            llm_out = {"optimization_tips": []}

        return {
            "portfolio_summary": {
                "total_patents":   len(decisions),
                "maintain_count":  len(maintain),
                "transfer_count":  len(transfer),
                "abandon_count":   len(abandon),
                "annual_savings_usd": round(annual_savings),
                "portfolio_roi":   round(portfolio_roi, 2),
            },
            "patent_decisions":      decisions,
            "high_value_patents":    [d for d in maintain if d["roi"] >= 3.0],
            "optimization_tips":     llm_out.get("optimization_tips", []),
            "budget_analysis": {
                "annual_budget_usd":   d.get("annual_budget_usd", 0),
                "projected_annual_cost": round(sum(dec["annual_cost_usd"] for dec in maintain)),
                "within_budget":        sum(dec["annual_cost_usd"] for dec in maintain) <= d.get("annual_budget_usd", float("inf")),
            },
            "maintenance_score": score,
        }

    def _next_actions(self, gate: str, decisions: list) -> list[str]:
        abandon = [d for d in decisions if d["decision"] == "포기"]
        transfer = [d for d in decisions if d["decision"] == "이전/매각"]
        actions = []
        if gate == "Go":
            actions.append(f"포트폴리오 최적화 완료 — 연간 ${sum(d['annual_cost_usd'] for d in abandon):,.0f} 절감 예정")
        if abandon:
            actions.append(f"포기 대상 {len(abandon)}건: 다음 갱신 기한 전 변리사에게 포기 의뢰")
        if transfer:
            actions.append(f"이전 대상 {len(transfer)}건: TLO·기술거래소에 매각 의뢰 또는 번들 라이선싱 검토")
        if not actions:
            actions.append("포트폴리오 데이터 입력 후 최적화 분석 실행")
        return actions
