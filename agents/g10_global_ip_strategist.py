"""G10-Global 글로벌 IP 전략 — 국가별 출원 우선순위·규제·TAM 매트릭스"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# 국가별 IP 환경 기초 스코어 (특허 강도·집행력·시장규모 종합)
_COUNTRY_IP_STRENGTH = {
    "USA": {"ip_score": 90, "market_tier": 1, "enforcement": "매우 강함", "avg_grant_months": 24},
    "EU":  {"ip_score": 85, "market_tier": 1, "enforcement": "강함 (EPO)", "avg_grant_months": 36},
    "CHN": {"ip_score": 65, "market_tier": 1, "enforcement": "개선 중", "avg_grant_months": 18},
    "JPN": {"ip_score": 80, "market_tier": 2, "enforcement": "강함", "avg_grant_months": 20},
    "KOR": {"ip_score": 78, "market_tier": 2, "enforcement": "강함", "avg_grant_months": 14},
    "SGP": {"ip_score": 82, "market_tier": 3, "enforcement": "강함", "avg_grant_months": 24},
    "ISR": {"ip_score": 75, "market_tier": 3, "enforcement": "강함", "avg_grant_months": 30},
    "IND": {"ip_score": 55, "market_tier": 2, "enforcement": "보통", "avg_grant_months": 48},
    "AUS": {"ip_score": 78, "market_tier": 3, "enforcement": "강함", "avg_grant_months": 24},
    "CAN": {"ip_score": 76, "market_tier": 3, "enforcement": "강함", "avg_grant_months": 30},
}

# 출원 전략 유형
_FILING_STRATEGIES = {
    "pct_first": "PCT 우선 → 국내단계 선별 진입 (비용 효율적, 30개월 유예)",
    "direct_key_markets": "핵심 시장 직접 출원 (미·EU·중 동시, PCT 생략, 빠른 권리화)",
    "home_first": "본국 우선 출원 후 PCT 연계 (비용 최소화, 로컬 레퍼런스 확보)",
    "regional": "지역 특허청 활용 (EPO·ARIPO·OAPI — 다수 국가 단일 출원)",
}


class GlobalIPStrategist(BaseAgent):
    stage_id = "G10-Global"
    stage_name = "글로벌 IP 전략"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          tech_name (str): 기술명
          target_market_countries (list): 진출 목표 국가 코드 리스트
          tam_by_country (dict): {국가코드: TAM USD} — 국가별 시장 규모
          regulatory_requirement_by_country (dict): {국가코드: ["인증1", "인증2"]}
          current_filings (list): 현재 출원/등록 특허 국가
          filing_strategy_preference (str, optional): pct_first/direct_key_markets/home_first/regional
          annual_ip_budget_usd (float): 연간 IP 예산
          competitor_presence (dict, optional): {국가코드: ["경쟁사1"]} 경쟁사 현황
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
        countries = d.get("target_market_countries", [])
        tam = d.get("tam_by_country", {})
        current = d.get("current_filings", [])
        budget = d.get("annual_ip_budget_usd", 0)

        # 목표 국가 수 (25점)
        score += min(25, len(countries) * 5)
        # TAM 데이터 존재 (20점)
        score += min(20, len(tam) * 4)
        # 현재 출원 커버리지 (20점)
        covered = sum(1 for c in countries if c in current)
        score += 20 * (covered / max(len(countries), 1))
        # 예산 적정성 (20점)
        estimated = sum(5_000 for _ in countries)  # 국가당 $5K 기준
        score += 20 if budget >= estimated else 10 if budget >= estimated * 0.5 else 3
        # 규제 정보 (15점)
        regs = d.get("regulatory_requirement_by_country", {})
        score += min(15, len(regs) * 3)
        return round(min(score, 100), 1)

    def _build_output(self, d: dict, score: float) -> dict:
        countries = d.get("target_market_countries", [])
        tam = d.get("tam_by_country", {})
        regs = d.get("regulatory_requirement_by_country", {})
        current = d.get("current_filings", [])
        competitors = d.get("competitor_presence", {})

        # 국가 우선순위 매트릭스 (TAM × IP강도 × 경쟁 역산)
        priority_matrix = []
        for c in countries:
            ip_info = _COUNTRY_IP_STRENGTH.get(c, {"ip_score": 50, "market_tier": 3, "enforcement": "보통", "avg_grant_months": 30})
            tam_val = tam.get(c, 0)
            comp_count = len(competitors.get(c, []))
            composite = round(
                (tam_val / max(max(tam.values(), default=1), 1) * 40) +
                (ip_info["ip_score"] / 100 * 35) +
                ((1 - min(comp_count, 5) / 5) * 25),
                1
            )
            priority_matrix.append({
                "country": c,
                "tam_usd": tam_val,
                "ip_strength_score": ip_info["ip_score"],
                "enforcement": ip_info["enforcement"],
                "avg_grant_months": ip_info["avg_grant_months"],
                "competitor_count": comp_count,
                "composite_priority": composite,
                "already_filed": c in current,
                "regulatory_requirements": regs.get(c, []),
            })
        priority_matrix.sort(key=lambda x: x["composite_priority"], reverse=True)

        # 출원 전략 추천
        strategy_pref = d.get("filing_strategy_preference", "pct_first")
        strategy_desc = _FILING_STRATEGIES.get(strategy_pref, _FILING_STRATEGIES["pct_first"])

        # 커버리지 갭
        gap_countries = [c for c in countries if c not in current]

        llm_result = self._llm(
            f"기술명: {d.get('tech_name', '')}\n"
            f"목표 국가: {countries}\n"
            f"우선순위 상위 3개국: {[m['country'] for m in priority_matrix[:3]]}\n"
            f"출원 공백 국가: {gap_countries}\n"
            f"예산: ${d.get('annual_ip_budget_usd', 0):,.0f}\n\n"
            "글로벌 IP 전략 권고를 JSON으로:\n"
            '{"strategy_summary":"","immediate_actions":[],"3year_roadmap":[],"risk_warnings":[]}',
            system="글로벌 IP 전략 전문가. JSON만 반환."
        )
        try:
            import json
            strategy_analysis = json.loads(llm_result)
        except Exception:
            top3 = [m["country"] for m in priority_matrix[:3]]
            strategy_analysis = {
                "strategy_summary": f"우선 {top3} 3개국 출원 후 PCT로 30개월 유예 확보",
                "immediate_actions": [f"{gap_countries[0]} 출원 즉시 진행"] if gap_countries else [],
            }

        return {
            "global_filing_strategy": {
                "strategy_type": strategy_pref,
                "strategy_description": strategy_desc,
                "target_countries_count": len(countries),
                "currently_filed_count": len(current),
                "coverage_gap": gap_countries,
            },
            "country_priority_matrix": priority_matrix,
            "strategy_analysis": strategy_analysis,
            "global_score": score,
        }

    def _next_actions(self, gate: str, d: dict) -> list[str]:
        countries = d.get("target_market_countries", [])
        current = d.get("current_filings", [])
        gap = [c for c in countries if c not in current]
        if gate == "Go":
            return [
                f"우선순위 1위 국가({gap[0] if gap else '확인'}) 출원 즉시 진행",
                "PCT 국제출원으로 30개월 내 전 목표국 권리 유예 확보",
                "G10-Competitive 경쟁대응 전략과 연계하여 모니터링 체계 구축",
            ]
        if gate == "Hold":
            return [
                "국가별 TAM 데이터 확보 (G3 시장성 분석 결과 활용)",
                "출원 예산 확정 후 국가 우선순위 재산정",
            ]
        return ["목표 국가 재선정 — 시장 매력도·IP 환경 재평가"]
