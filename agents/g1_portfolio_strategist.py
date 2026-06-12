"""G1-Portfolio 특허 포트폴리오 구성 — 1단계 IP개발 핵심 전략"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# PCT 출원 타임라인 (우선일 기준)
_PCT_TIMELINE = {
    "priority_filing": {"months": 0, "desc": "최초 출원일 (우선일 확보)"},
    "pct_filing": {"months": 12, "desc": "PCT 국제출원 (우선일 후 12개월 이내)"},
    "national_phase": {"months": 30, "desc": "각국 국내단계 진입 (우선일 후 30~31개월)"},
    "examination": {"months": 42, "desc": "평균 심사 기간 (국가별 12~24개월 추가)"},
}

# 국가별 특허 출원 비용 추정 (USD, 출원+등록 기준)
_FILING_COST_USD = {
    "KOR": 3_000,
    "USA": 12_000,
    "EU": 15_000,    # EPO (지정국 3개 기준)
    "CHN": 5_000,
    "JPN": 8_000,
    "SGP": 4_000,
    "ISR": 4_500,
    "AUS": 6_000,
    "CAN": 7_000,
    "IND": 3_000,
}

# 포트폴리오 3계층 역할
_PORTFOLIO_LAYERS = {
    "core": {
        "role": "코어(핵심) IP",
        "desc": "경쟁사가 회피 불가능한 광범위한 독립청구항 특허",
        "filing_priority": "최우선 — 전략국 PCT 출원",
        "target_count": "3~5개",
    },
    "satellite": {
        "role": "위성(실시) IP",
        "desc": "코어 특허 주변의 구체적 실시 방법·제품·용도 특허",
        "filing_priority": "2순위 — 주요 시장국 직접 출원",
        "target_count": "5~10개",
    },
    "defensive": {
        "role": "방어(공개) IP",
        "desc": "경쟁사 출원 차단을 위한 선행기술 공개(방어적 공개) 또는 분산 특허",
        "filing_priority": "선택적 — 비용 최소화",
        "target_count": "필요 시 다수",
    },
}


class PatentPortfolioStrategist(BaseAgent):
    stage_id = "G1-Portfolio"
    stage_name = "특허 포트폴리오 구성 전략"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          tech_name (str): 기술명
          core_patents (list of {title, ipc, claims_count, status}): 코어 특허 후보
          satellite_patents (list of {title, ipc, claims_count}): 위성 특허 후보
          defensive_patents (list of {title, ipc}): 방어 특허 후보
          target_countries (list): 출원 목표 국가 코드 리스트
          budget_usd (float): 연간 IP 예산
          priority_date (str, optional): 우선일 (YYYY-MM-DD)
          tech_lifecycle_years (int, optional): 기술 수명 주기
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
        cores = d.get("core_patents", [])
        sats = d.get("satellite_patents", [])
        defs = d.get("defensive_patents", [])
        countries = d.get("target_countries", [])
        budget = d.get("budget_usd", 0)

        # 코어 특허 존재 (30점)
        score += min(30, len(cores) * 10)
        # 위성 특허 구성 (20점)
        score += min(20, len(sats) * 4)
        # 출원 대상국 선정 (25점)
        score += min(25, len(countries) * 5)
        # 예산 계획 (15점)
        estimated_cost = self._estimate_cost(countries, len(cores) + len(sats))
        if budget > 0:
            score += 15 if budget >= estimated_cost else 8 if budget >= estimated_cost * 0.5 else 3
        # 방어 특허 (10점)
        score += min(10, len(defs) * 3)
        return round(min(score, 100), 1)

    def _estimate_cost(self, countries: list, patent_count: int) -> float:
        base_cost = sum(_FILING_COST_USD.get(c, 5_000) for c in countries)
        return base_cost * max(patent_count, 1)

    def _build_output(self, d: dict, score: float) -> dict:
        cores = d.get("core_patents", [])
        sats = d.get("satellite_patents", [])
        defs = d.get("defensive_patents", [])
        countries = d.get("target_countries", [])
        budget = d.get("budget_usd", 0)
        priority_date = d.get("priority_date", "미정")

        # PCT 타임라인 계산
        import datetime
        try:
            pd = datetime.datetime.strptime(priority_date, "%Y-%m-%d")
            pct_date = (pd + datetime.timedelta(days=365)).strftime("%Y-%m-%d")
            national_date = (pd + datetime.timedelta(days=912)).strftime("%Y-%m-%d")
        except Exception:
            pct_date = "우선일 확정 후 12개월"
            national_date = "우선일 확정 후 30개월"

        # 비용 산정
        cost_breakdown = {c: _FILING_COST_USD.get(c, 5_000) * (len(cores) + len(sats))
                         for c in countries}
        total_cost = sum(cost_breakdown.values())
        budget_gap = max(0, total_cost - budget)

        # 우선 출원 국가 권고 (코어만)
        core_country_priority = sorted(
            countries,
            key=lambda c: _FILING_COST_USD.get(c, 5_000)
        )[:5]

        llm_result = self._llm(
            f"기술명: {d.get('tech_name', '')}\n"
            f"코어 특허: {len(cores)}개, 위성: {len(sats)}개, 방어: {len(defs)}개\n"
            f"목표 국가: {countries}\n"
            f"예산: ${budget:,.0f} / 예상 비용: ${total_cost:,.0f}\n\n"
            "특허 포트폴리오 전략 권고를 JSON으로:\n"
            '{"portfolio_strategy":"","key_risks":[],"quick_wins":[],"long_term_goals":[]}',
            system="특허 포트폴리오 전략 전문가. JSON만 반환."
        )
        try:
            import json
            strategy_analysis = json.loads(llm_result)
        except Exception:
            strategy_analysis = {
                "portfolio_strategy": f"코어 {len(cores)}건 PCT 출원 후 {countries[:3]} 국내단계 진입 권장",
                "quick_wins": ["코어 특허 우선 출원으로 우선권 확보"],
            }

        return {
            "portfolio_map": {
                "tech_name": d.get("tech_name", ""),
                "layers": {
                    "core": {
                        **_PORTFOLIO_LAYERS["core"],
                        "patents": cores,
                        "count": len(cores),
                    },
                    "satellite": {
                        **_PORTFOLIO_LAYERS["satellite"],
                        "patents": sats,
                        "count": len(sats),
                    },
                    "defensive": {
                        **_PORTFOLIO_LAYERS["defensive"],
                        "patents": defs,
                        "count": len(defs),
                    },
                },
                "total_patents": len(cores) + len(sats) + len(defs),
            },
            "filing_timeline": {
                "priority_date": priority_date,
                "pct_deadline": pct_date,
                "national_phase_deadline": national_date,
                "milestones": _PCT_TIMELINE,
            },
            "cost_projection": {
                "target_countries": countries,
                "cost_by_country_usd": cost_breakdown,
                "total_estimated_usd": total_cost,
                "budget_usd": budget,
                "budget_gap_usd": budget_gap,
                "priority_countries_for_core": core_country_priority,
                "note": "비용은 출원·심사·등록 합산 추정치. 번역·대리인 비용 별도.",
            },
            "portfolio_strategy": strategy_analysis,
            "portfolio_score": score,
        }

    def _next_actions(self, gate: str, d: dict) -> list[str]:
        if gate == "Go":
            return [
                "코어 특허 PCT 출원 즉시 진행 (우선일 12개월 이내)",
                "G2 TRL 평가와 병행하여 기술 증빙 자료 확보",
                "IP 전문 대리인 선임 및 청구항 초안 검토",
            ]
        if gate == "Hold":
            actions = []
            if not d.get("core_patents"):
                actions.append("코어 특허 후보 최소 1건 이상 식별")
            if not d.get("target_countries"):
                actions.append("출원 목표 국가 확정 (시장성 G3과 연계)")
            if not d.get("budget_usd"):
                actions.append("연간 IP 예산 계획 수립")
            return actions
        return [
            "코어 기술 재정의 후 포트폴리오 재구성",
            "G0 기술발굴 단계 재검토",
        ]
