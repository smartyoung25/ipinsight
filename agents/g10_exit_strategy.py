"""G10-Exit: 엑시트 전략 — M&A·IPO·세컨더리·라이선스 엑시트 시나리오
Series A 이후 투자자·창업자 회수 경로를 정량적으로 설계.
"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# 엑시트 유형별 특성
_EXIT_TYPES = {
    "strategic_ma": {
        "label": "전략적 M&A",
        "typical_multiple": (3, 8),   # 매출 멀티플 범위
        "timeline_years":  (2, 5),
        "trl_min": 6,
        "revenue_min_usd": 500_000,
        "pros": ["프리미엄 밸류에이션","시너지 가치 반영","빠른 글로벌 확장"],
        "cons": ["문화 충돌 위험","독립성 상실","실사(DD) 부담"],
        "trigger": "전략적 투자자·CVC가 Venture Client로 진입 시 M&A 전환 신호",
    },
    "financial_ma": {
        "label": "재무적 M&A (PE·바이아웃)",
        "typical_multiple": (6, 12),
        "timeline_years":  (3, 7),
        "trl_min": 7,
        "revenue_min_usd": 2_000_000,
        "pros": ["높은 멀티플","경영진 인센티브 유지","성장 후 재매각"],
        "cons": ["EBITDA 기반 평가(적자 기업 불리)","레버리지 부담"],
        "trigger": "ARR $2M+ + EBITDA 흑자 전환 시 PE 관심",
    },
    "ipo": {
        "label": "기업공개(IPO)",
        "typical_multiple": (5, 15),
        "timeline_years":  (5, 10),
        "trl_min": 8,
        "revenue_min_usd": 10_000_000,
        "pros": ["최고 밸류에이션","브랜드 가치 향상","추가 자금 조달"],
        "cons": ["공시 부담·비용","주가 변동 리스크","Lock-up 기간"],
        "trigger": "ARR $10M+ + YoY 성장률 50%+ + 흑자 가능성",
    },
    "secondary_sale": {
        "label": "세컨더리 지분 매각",
        "typical_multiple": (2, 5),
        "timeline_years":  (1, 3),
        "trl_min": 5,
        "revenue_min_usd": 200_000,
        "pros": ["부분 유동성 확보","경영 지속 가능","빠른 실행"],
        "cons": ["낮은 멀티플","시그널 효과(매도 신호)"],
        "trigger": "초기 투자자 DPI 확보 필요 시 활용",
    },
    "license_exit": {
        "label": "기술 라이선스·이전 엑시트",
        "typical_multiple": (1, 4),
        "timeline_years":  (1, 3),
        "trl_min": 4,
        "revenue_min_usd": 0,
        "pros": ["매출 없이도 가능","IP 가치 실현","비희석"],
        "cons": ["낮은 총가치","운영 지속 어려움"],
        "trigger": "TRL 높고 시장 진입 자원 부족 시 기술이전 엑시트",
    },
}


class ExitStrategyDesigner(BaseAgent):
    stage_id   = "G10-Exit"
    stage_name = "엑시트 전략 설계"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          company_name (str)
          trl (int)
          arr_usd (float): 연간 반복매출
          ebitda_usd (float): EBITDA (음수 허용)
          growth_rate_yoy_pct (float): YoY 성장률 %
          current_valuation_usd (float): 현재 기업가치
          total_invested_usd (float): 총 투자 유치액
          founder_equity_pct (float): 창업자 지분율 %
          investor_equity_pct (float): 투자자 지분율 %
          target_exit_years (int): 목표 엑시트 기간 (년)
          preferred_exit (str): strategic_ma/financial_ma/ipo/secondary_sale/license_exit
          strategic_acquirer_candidates (list[str]): M&A 후보 기업
          industry_sector (str)
          ip_strength_score (float): 0~100
          patent_count (int)
        """
        scenarios = self._build_scenarios(input_data)
        score     = self._score(input_data, scenarios)
        gate      = self._gate_from_score(score)
        output    = self._build_output(input_data, scenarios, score)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output,
            next_actions=self._next_actions(gate, scenarios, input_data),
        )

    def _build_scenarios(self, d: dict) -> list[dict]:
        arr      = d.get("arr_usd", 0)
        trl      = d.get("trl", 1)
        growth   = d.get("growth_rate_yoy_pct", 0)
        cur_val  = d.get("current_valuation_usd", 0)
        tgt_yrs  = d.get("target_exit_years", 5)
        inv_eq   = d.get("investor_equity_pct", 30)
        fnd_eq   = d.get("founder_equity_pct", 60)

        scenarios = []
        for exit_key, exit_info in _EXIT_TYPES.items():
            # 자격 요건 확인
            feasible = (trl >= exit_info["trl_min"]) and (arr >= exit_info["revenue_min_usd"])
            tl_min, tl_max = exit_info["timeline_years"]
            in_timeline = tl_min <= tgt_yrs <= tl_max + 2

            # 미래 매출 추정 (성장률 적용)
            future_years = min(tgt_yrs, tl_max)
            future_arr   = arr * ((1 + growth/100) ** future_years)

            # 엑시트 밸류에이션 추정
            low_mult, high_mult = exit_info["typical_multiple"]
            val_low  = future_arr * low_mult
            val_high = future_arr * high_mult
            val_mid  = (val_low + val_high) / 2

            # 회수금 계산
            investor_return = val_mid * (inv_eq / 100)
            founder_return  = val_mid * (fnd_eq / 100)
            moic = round(investor_return / max(d.get("total_invested_usd", val_mid * 0.1), 1), 2)

            scenarios.append({
                "exit_type":        exit_key,
                "exit_label":       exit_info["label"],
                "feasible":         feasible,
                "in_timeline":      in_timeline,
                "timeline_years":   (tl_min, tl_max),
                "future_arr_usd":   round(future_arr),
                "valuation_low":    round(val_low),
                "valuation_mid":    round(val_mid),
                "valuation_high":   round(val_high),
                "investor_return_usd": round(investor_return),
                "founder_return_usd":  round(founder_return),
                "moic":             moic,
                "pros":             exit_info["pros"],
                "cons":             exit_info["cons"],
                "trigger":          exit_info["trigger"],
                "acquirer_candidates": d.get("strategic_acquirer_candidates", []) if exit_key == "strategic_ma" else [],
            })

        # 실현 가능·타임라인 맞는 순으로 정렬
        scenarios.sort(key=lambda x: (not x["feasible"], not x["in_timeline"], -x["valuation_mid"]))
        return scenarios

    def _score(self, d: dict, scenarios: list) -> float:
        score = 0.0
        feasible = [s for s in scenarios if s["feasible"]]
        # 실현 가능 엑시트 수 (30점)
        score += min(30, len(feasible) * 10)
        # 최고 MOIC (30점)
        max_moic = max((s["moic"] for s in feasible), default=0)
        score += min(30, max_moic * 6)
        # TRL 성숙도 (20점)
        score += min(20, (d.get("trl",1) / 9) * 20)
        # 전략적 M&A 후보 보유 (20점)
        score += min(20, len(d.get("strategic_acquirer_candidates",[])) * 7)
        return round(min(score, 100), 1)

    def _build_output(self, d: dict, scenarios: list, score: float) -> dict:
        best = next((s for s in scenarios if s["feasible"]), scenarios[0] if scenarios else {})

        llm_text = self._llm(
            f"회사: {d.get('company_name','')}\n"
            f"ARR: ${d.get('arr_usd',0):,.0f}  성장률: {d.get('growth_rate_yoy_pct',0)}%\n"
            f"현재 기업가치: ${d.get('current_valuation_usd',0):,.0f}\n"
            f"추천 엑시트: {best.get('exit_label','')}\n"
            f"M&A 후보: {d.get('strategic_acquirer_candidates',[])}\n"
            f"목표 기간: {d.get('target_exit_years',5)}년\n\n"
            "엑시트 준비 로드맵 3단계와 투자자 설득 포인트 2가지를 JSON으로:\n"
            '{"roadmap":[],"investor_pitch_points":[]}',
            system="M&A·IPO 엑시트 전문가. 현실적인 엑시트 전략 수립. JSON 반환."
        )
        try:
            import json
            llm_out = json.loads(llm_text)
        except Exception:
            llm_out = {"roadmap": [], "investor_pitch_points": []}

        return {
            "exit_scenarios":    scenarios,
            "recommended_exit":  best,
            "exit_readiness": {
                "arr_usd":           d.get("arr_usd", 0),
                "growth_yoy_pct":    d.get("growth_rate_yoy_pct", 0),
                "ip_strength":       d.get("ip_strength_score", 0),
                "patent_count":      d.get("patent_count", 0),
                "strategic_targets": d.get("strategic_acquirer_candidates", []),
            },
            "exit_roadmap":      llm_out.get("roadmap", []),
            "investor_pitch":    llm_out.get("investor_pitch_points", []),
            "exit_score":        score,
        }

    def _next_actions(self, gate: str, scenarios: list, d: dict) -> list[str]:
        best = next((s for s in scenarios if s["feasible"]), None)
        actions = []
        if gate == "Go" and best:
            actions.append(f"엑시트 목표: {best['exit_label']} — 예상 기업가치 ${best['valuation_mid']:,.0f}")
            if best["exit_type"] == "strategic_ma" and d.get("strategic_acquirer_candidates"):
                actions.append(f"M&A 후보 접촉 시작: {', '.join(d['strategic_acquirer_candidates'][:2])}")
            actions.append("Exit Readiness 체크리스트 작성 (재무제표 감사·IP 실사 준비)")
        elif gate == "Hold":
            actions.append(f"ARR ${d.get('arr_usd',0):,.0f} → 목표 ARR $1M 달성 후 전략적 M&A 접근")
            actions.append("IP 포트폴리오 강화 (특허 추가 출원) 및 전략적 파트너십 구축")
        else:
            actions.append("엑시트 가능 상태 아님 — 제품·매출 확보 우선 (최소 PoC 계약 2건)")
        return actions
