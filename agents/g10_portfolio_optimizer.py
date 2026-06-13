"""G10-Portfolio IP 포트폴리오 최적화 — 성장성·방어력·수익성 3축 평가"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# 포트폴리오 기술 상태 분류 (BCG 매트릭스 응용)
_TECH_CATEGORIES = {
    "star": {
        "label": "★ Star — 강화 투자",
        "desc": "높은 시장성장 + 강한 경쟁위치. 집중 투자·빠른 사업화 실행",
        "action": "추가 IP 보강 + 글로벌 확장 가속",
    },
    "cash_cow": {
        "label": "🐄 Cash Cow — 수익 극대화",
        "desc": "성숙 시장 + 강한 경쟁위치. 라이선싱으로 수익 극대화",
        "action": "비독점 라이선스 확대 + 유지비용 최적화",
    },
    "question_mark": {
        "label": "❓ Question Mark — 선택적 투자",
        "desc": "높은 시장성장 + 약한 경쟁위치. 추가 투자 또는 철수 결정 필요",
        "action": "PoC 추가 실증 후 투자 여부 결정 (6개월 내)",
    },
    "dog": {
        "label": "🐕 Dog — 구조조정",
        "desc": "성숙 시장 + 약한 경쟁위치. 매각·기술이전·폐기 검토",
        "action": "IP 기술이전 또는 방어적 공개 후 유지비용 제거",
    },
}

# 포트폴리오 건강 지표
_HEALTH_METRICS = [
    {"metric": "IP 집중도 (상위 3개 기술 매출 비중)", "healthy": "<60%", "risk": ">80%"},
    {"metric": "평균 특허 잔존 수명", "healthy": ">10년", "risk": "<5년"},
    {"metric": "라이선싱 수익 비중", "healthy": ">20%", "risk": "<5%"},
    {"metric": "R&D 대비 IP 수익률(ROI)", "healthy": ">200%", "risk": "<50%"},
    {"metric": "신규 IP 창출 건수/년", "healthy": "≥5건", "risk": "<2건"},
]


class PortfolioOptimizer(BaseAgent):
    stage_id = "G10-Portfolio"
    stage_name = "IP 포트폴리오 최적화"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          portfolio_techs (list of {
            tech_id, tech_name, trl, mrl, arl,
            annual_revenue_usd, annual_cost_usd,
            market_growth_pct, competitive_position: strong/medium/weak,
            patent_remaining_years, licensing_revenue_usd
          }): 포트폴리오 기술 목록
          cost_by_tech (dict, optional): {tech_id: annual_ip_cost_usd}
          revenue_by_tech (dict, optional): {tech_id: annual_revenue_usd}
          kpi_performance (list, optional): G10 KPI 결과 연계
          total_ip_budget_usd (float): 연간 총 IP 예산
          strategic_focus (str, optional): growth/efficiency/defense
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
        techs = d.get("portfolio_techs", [])
        if not techs:
            return 0.0

        score = 0.0
        # 포트폴리오 다양성 (20점)
        score += min(20, len(techs) * 4)

        # 수익성 (30점)
        total_rev = sum(t.get("annual_revenue_usd", 0) for t in techs)
        total_cost = sum(t.get("annual_cost_usd", 0) for t in techs)
        if total_cost > 0:
            roi = total_rev / total_cost
            score += min(30, roi * 10)

        # TRL 완성도 (20점)
        avg_trl = sum(t.get("trl", 1) for t in techs) / len(techs)
        score += round(avg_trl / 9 * 20, 1)

        # 경쟁 위치 복합 점수 (15점)
        avg_comp = sum(self._competitive_position_score(t) for t in techs) / len(techs)
        score += round(avg_comp / 100 * 15, 1)

        # 특허 잔존 수명 (15점)
        avg_life = sum(t.get("patent_remaining_years", 0) for t in techs) / len(techs)
        score += min(15, avg_life * 1.5)

        return round(min(score, 100), 1)

    def _competitive_position_score(self, tech: dict) -> float:
        """BCG X축 — 경쟁 위치 복합 점수 (0~100)
        자기 선언 competitive_position을 IP 강도 지표로 보완.

        구성:
          ① 자기 선언 포지션 (35점): strong=35, medium=20, weak=5
          ② 특허 잔존 수명 (25점): 20년→25점, 5년→6점
          ③ TRL 성숙도 (20점): TRL 9→20점
          ④ ARL 시장 채택 (20점): ARL 9→20점
        """
        pos = tech.get("competitive_position", "weak")
        pos_score = {"strong": 35, "medium": 20, "weak": 5}.get(pos, 5)

        life = tech.get("patent_remaining_years", 0)
        life_score = min(25, life * 1.25)

        trl = tech.get("trl", 1)
        trl_score = round(trl / 9 * 20, 1)

        arl = tech.get("arl", 1)
        arl_score = round(arl / 9 * 20, 1)

        return round(pos_score + life_score + trl_score + arl_score, 1)

    def _classify_tech(self, tech: dict) -> tuple[str, dict]:
        """BCG Matrix 분류 + 좌표 반환
        X축: 경쟁 위치 점수 (0~100) — 높을수록 강함
        Y축: 시장 성장률 (%)
        기준선: X=50 (경쟁위치 중간), Y=10% (고성장 임계)
        """
        growth = tech.get("market_growth_pct", 0)
        comp_score = self._competitive_position_score(tech)
        high_growth = growth >= 10
        strong_pos = comp_score >= 50

        if high_growth and strong_pos:
            category = "star"
        elif not high_growth and strong_pos:
            category = "cash_cow"
        elif high_growth and not strong_pos:
            category = "question_mark"
        else:
            category = "dog"

        bcg_coords = {
            "x_competitive_score": comp_score,   # 0~100 (높을수록 강함)
            "y_market_growth_pct": growth,
            "quadrant": category,
            "x_threshold": 50,
            "y_threshold": 10,
        }
        return category, bcg_coords

    def _build_output(self, d: dict, score: float) -> dict:
        techs = d.get("portfolio_techs", [])
        budget = d.get("total_ip_budget_usd", 0)
        focus = d.get("strategic_focus", "growth")

        # 기술별 분류 + ROI 산정 + BCG 좌표
        classified = []
        for t in techs:
            cat, bcg_coords = self._classify_tech(t)
            rev = t.get("annual_revenue_usd", 0)
            cost = t.get("annual_cost_usd", 1)
            lic = t.get("licensing_revenue_usd", 0)
            classified.append({
                **t,
                "category": cat,
                "category_info": _TECH_CATEGORIES[cat],
                "roi": round(rev / max(cost, 1) * 100, 1),
                "licensing_share_pct": round(lic / max(rev, 1) * 100, 1),
                "recommended_action": _TECH_CATEGORIES[cat]["action"],
                "bcg_position": bcg_coords,
            })

        # 카테고리별 요약
        cat_summary = {}
        for cat in _TECH_CATEGORIES:
            items = [c for c in classified if c["category"] == cat]
            cat_summary[cat] = {
                "count": len(items),
                "total_revenue_usd": sum(i.get("annual_revenue_usd", 0) for i in items),
                "total_cost_usd": sum(i.get("annual_cost_usd", 0) for i in items),
                "tech_names": [i.get("tech_name", "") for i in items],
            }

        # 매각/이전 권고 (Dog 카테고리)
        divestment_candidates = [c for c in classified if c["category"] == "dog"]

        # 집중 투자 권고 (Star 카테고리)
        investment_targets = [c for c in classified if c["category"] == "star"]

        # 포트폴리오 건강 진단
        total_rev = sum(t.get("annual_revenue_usd", 0) for t in techs)
        total_cost = sum(t.get("annual_cost_usd", 0) for t in techs)
        avg_life = sum(t.get("patent_remaining_years", 0) for t in techs) / max(len(techs), 1)
        health_diagnosis = {
            "overall_roi_pct": round(total_rev / max(total_cost, 1) * 100, 1),
            "avg_patent_life_years": round(avg_life, 1),
            "portfolio_balance": {k: cat_summary[k]["count"] for k in _TECH_CATEGORIES},
            "health_metrics": _HEALTH_METRICS,
        }

        llm_result = self._llm(
            f"포트폴리오 기술 수: {len(techs)}\n"
            f"Star: {cat_summary['star']['count']}건, Cash Cow: {cat_summary['cash_cow']['count']}건, "
            f"Question Mark: {cat_summary['question_mark']['count']}건, Dog: {cat_summary['dog']['count']}건\n"
            f"전체 ROI: {health_diagnosis['overall_roi_pct']}%\n"
            f"매각 후보: {len(divestment_candidates)}건\n"
            f"전략 방향: {focus}\n\n"
            "포트폴리오 최적화 전략을 JSON으로:\n"
            '{"optimization_summary":"","3year_target":"","resource_reallocation":[],"new_ip_investment_areas":[]}',
            system="IP 포트폴리오 전략가. JSON만 반환."
        )
        try:
            import json
            optimization_plan = json.loads(llm_result)
        except Exception:
            optimization_plan = {
                "optimization_summary": f"Star {cat_summary['star']['count']}건 집중 투자, Dog {cat_summary['dog']['count']}건 구조조정",
                "resource_reallocation": [f"Dog 기술 IP 유지비 절감으로 Star 투자 재원 확보"],
            }

        # BCG 기반 예산 배분 (기본 규칙: Star 40%, Cash Cow 20%, QM 30%, Dog 10%)
        _BUDGET_ALLOC = {"star": 0.40, "cash_cow": 0.20, "question_mark": 0.30, "dog": 0.10}
        # strategic_focus에 따라 조정
        if focus == "growth":
            _BUDGET_ALLOC.update({"star": 0.45, "question_mark": 0.35, "cash_cow": 0.15, "dog": 0.05})
        elif focus == "efficiency":
            _BUDGET_ALLOC.update({"cash_cow": 0.40, "star": 0.30, "question_mark": 0.20, "dog": 0.10})
        elif focus == "defense":
            _BUDGET_ALLOC.update({"star": 0.35, "cash_cow": 0.30, "question_mark": 0.25, "dog": 0.10})

        budget_allocation = {
            cat: {
                "alloc_pct": round(_BUDGET_ALLOC[cat] * 100, 0),
                "budget_usd": round(budget * _BUDGET_ALLOC[cat], 0),
                "tech_count": cat_summary[cat]["count"],
                "rationale": _TECH_CATEGORIES[cat]["action"],
            }
            for cat in _TECH_CATEGORIES
        }

        # BCG 매트릭스 좌표 집계 (시각화용)
        bcg_matrix_data = [
            {
                "tech_name": c.get("tech_name", ""),
                "x": c["bcg_position"]["x_competitive_score"],
                "y": c["bcg_position"]["y_market_growth_pct"],
                "quadrant": c["category"],
                "revenue_usd": c.get("annual_revenue_usd", 0),
            }
            for c in classified
        ]

        return {
            "portfolio_optimization_plan": {
                "tech_name": "전체 IP 포트폴리오",
                "total_techs": len(techs),
                "strategic_focus": focus,
                "category_summary": cat_summary,
                "classified_portfolio": classified,
                "bcg_matrix": {
                    "data_points": bcg_matrix_data,
                    "x_axis": "경쟁 위치 점수 (IP강도·TRL·ARL·특허수명 복합, 0~100)",
                    "y_axis": "시장 성장률 (%)",
                    "x_threshold": 50,
                    "y_threshold": 10,
                    "note": "BCG Matrix X축을 자기선언 대신 IP 강도 지표로 객관화 (TRL+ARL+특허수명+경쟁위치)",
                },
                "budget_allocation": budget_allocation,
            },
            "divestment_recommendation": {
                "candidates": divestment_candidates,
                "count": len(divestment_candidates),
                "estimated_cost_savings_usd": sum(c.get("annual_cost_usd", 0) for c in divestment_candidates),
                "recommended_exit": "IP 기술이전 또는 방어적 공개 후 유지비 제거",
            },
            "investment_priority": {
                "star_techs": investment_targets,
                "count": len(investment_targets),
                "additional_investment_needed_usd": max(0, budget * 0.4),
            },
            "portfolio_health": health_diagnosis,
            "optimization_strategy": optimization_plan,
            "portfolio_score": score,
        }

    def _next_actions(self, gate: str, d: dict) -> list[str]:
        techs = d.get("portfolio_techs", [])
        dogs = [t for t in techs if self._classify_tech(t)[0] == "dog"]
        stars = [t for t in techs if self._classify_tech(t)[0] == "star"]
        if gate == "Go":
            return [
                f"Star 기술 {len(stars)}건 집중 투자 계획 수립 (G9 거래구조 연계)",
                f"Dog 기술 {len(dogs)}건 구조조정 실행 — IP 기술이전 또는 방어적 공개",
                "분기별 포트폴리오 KPI 리뷰 사이클 구축",
            ]
        if gate == "Hold":
            return [
                "포트폴리오 기술 수익·비용 데이터 완성 후 재평가",
                "경쟁위치 분석 보강 (G10-Competitive 결과 연계)",
            ]
        return ["포트폴리오 전면 재구성 — 핵심 기술 재식별 필요"]
