"""G2-Funding: 자금조달 시나리오 플래너
Bootstrap → Angel → Seed → Series A/B → Growth 단계별 경로 + 지분 희석 시뮬레이션.
"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# 단계별 자금조달 기준표 (글로벌 중앙값 기준)
_FUNDING_STAGES = [
    {
        "stage":         "Bootstrap / 자체 자금",
        "trl_range":     [1, 4],
        "typical_usd":   [0, 200_000],
        "dilution_pct":  0,
        "valuation_range_usd": [0, 500_000],
        "sources":       ["창업자 자기자본", "가족·지인(FFF)", "정부 비희석 R&D 지원"],
        "key_milestone": "TRL 3~4 달성, 개념검증(PoC) 완료",
        "timeline_months": 6,
    },
    {
        "stage":         "Angel / Pre-Seed",
        "trl_range":     [3, 5],
        "typical_usd":   [100_000, 1_000_000],
        "dilution_pct":  10,
        "valuation_range_usd": [1_000_000, 5_000_000],
        "sources":       ["엔젤 투자자", "창업 AC(액셀러레이터)", "정부 TIPS·창업도약 등"],
        "key_milestone": "MVP 완성, 초기 고객 확보(LoI 3건 이상)",
        "timeline_months": 6,
    },
    {
        "stage":         "Seed",
        "trl_range":     [4, 6],
        "typical_usd":   [500_000, 3_000_000],
        "dilution_pct":  15,
        "valuation_range_usd": [3_000_000, 15_000_000],
        "sources":       ["시드 VC", "CVC", "정부 스케일업", "기술보증기금 보증부 투자"],
        "key_milestone": "Product-Market Fit 초기 증거, MRR $10K+ 또는 PoC 계약 2건",
        "timeline_months": 12,
    },
    {
        "stage":         "Series A",
        "trl_range":     [6, 8],
        "typical_usd":   [2_000_000, 15_000_000],
        "dilution_pct":  20,
        "valuation_range_usd": [10_000_000, 60_000_000],
        "sources":       ["VC(Series A)", "전략적 투자자", "Venture Client 계약"],
        "key_milestone": "반복 가능한 영업 모델, ARR $1M+ 또는 라이선스 계약 5건+",
        "timeline_months": 18,
    },
    {
        "stage":         "Series B+",
        "trl_range":     [8, 9],
        "typical_usd":   [10_000_000, 50_000_000],
        "dilution_pct":  15,
        "valuation_range_usd": [40_000_000, 200_000_000],
        "sources":       ["성장 VC", "글로벌 CVC", "PE(사모펀드)", "전략적 M&A 전 단계"],
        "key_milestone": "시장 지배력 확보, ARR $10M+ 또는 다국가 라이선스 확장",
        "timeline_months": 24,
    },
]

# 기술이전 전용 자금 조달 경로 (희석 없음)
_TLO_FUNDING = [
    {"name": "정부 R&D(비희석)", "trl": [1,6], "usd": [50_000, 3_000_000], "dilution": 0},
    {"name": "기술이전 선급금",   "trl": [4,9], "usd": [100_000, 2_000_000], "dilution": 0},
    {"name": "로열티 수익 선지급(Royalty Advance)", "trl": [6,9], "usd": [200_000, 5_000_000], "dilution": 0},
    {"name": "CRADA/공동연구계약", "trl": [3,7], "usd": [200_000, 5_000_000], "dilution": 0},
]


class FundingPlanner(BaseAgent):
    stage_id   = "G2-Funding"
    stage_name = "자금조달 시나리오 플래너"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          current_trl (int): 현재 TRL 1~9
          target_trl (int): 목표 TRL
          commercialization_type (str): startup / technology_transfer / spinout / licensing
          current_valuation_usd (float): 현재 추정 기업가치 (0이면 미산정)
          current_cash_usd (float): 현재 보유 현금
          monthly_burn_usd (float): 월 현금 소진
          total_funding_needed_usd (float): 목표 TRL까지 필요 총 자금
          founder_equity_pct (float): 창업자 현재 지분율 (100이면 미희석)
          preferred_sources (list[str]): 선호 자금 조달 방식 키워드
          country (str): 주요 자금 조달 국가 (KOR/USA/EU/SGP 등)
          has_revenue (bool): 매출 발생 여부
        """
        trl  = input_data.get("current_trl", 1)
        plan = self._build_plan(input_data)
        score = self._score(input_data, plan)
        gate  = self._gate_from_score(score)
        output = self._build_output(input_data, plan, score)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output,
            next_actions=self._next_actions(gate, input_data, plan),
        )

    # ── 자금조달 경로 계획 ───────────────────────────────────────────────────
    def _build_plan(self, d: dict) -> list[dict]:
        trl      = d.get("current_trl", 1)
        trl_tgt  = d.get("target_trl", 9)
        ctype    = d.get("commercialization_type", "startup")
        total    = d.get("total_funding_needed_usd", 0)
        equity   = d.get("founder_equity_pct", 100.0)
        monthly  = d.get("monthly_burn_usd", 0)

        plan = []
        remaining = total
        current_equity = equity

        # 기술이전 전용 경로
        if ctype in ("technology_transfer", "licensing"):
            for f in _TLO_FUNDING:
                if f["trl"][0] <= trl_tgt and f["trl"][1] >= trl:
                    plan.append({
                        "stage":      f["name"],
                        "amount_usd": min(f["usd"][1], remaining),
                        "dilution_pct": 0,
                        "equity_after_pct": current_equity,
                        "timeline_months": 6,
                        "sources":    [f["name"]],
                        "milestone":  f"TRL {trl} → {min(trl+2, trl_tgt)} 달성",
                        "type":       "non_dilutive",
                    })
                    remaining -= min(f["usd"][1], remaining)
                    if remaining <= 0:
                        break
            return plan

        # 스타트업/스핀아웃 지분 희석 경로
        for fs in _FUNDING_STAGES:
            if fs["trl_range"][1] < trl:
                continue
            if remaining <= 0:
                break

            amount = min(fs["typical_usd"][1], max(fs["typical_usd"][0], remaining * 0.4))
            dilution = fs["dilution_pct"] if remaining > fs["typical_usd"][0] else fs["dilution_pct"] * 0.5
            current_equity = current_equity * (1 - dilution / 100)

            months_cover = int(amount / monthly) if monthly > 0 else fs["timeline_months"]

            plan.append({
                "stage":              fs["stage"],
                "amount_usd":         round(amount),
                "dilution_pct":       round(dilution, 1),
                "equity_after_pct":   round(current_equity, 1),
                "valuation_range_usd": fs["valuation_range_usd"],
                "timeline_months":    fs["timeline_months"],
                "runway_cover_months": min(months_cover, 36),
                "sources":            fs["sources"],
                "milestone":          fs["key_milestone"],
                "type":               "dilutive",
            })
            remaining -= amount
            if remaining <= 0:
                break

        return plan

    # ── 점수 ─────────────────────────────────────────────────────────────────
    def _score(self, d: dict, plan: list) -> float:
        score = 0.0
        monthly = d.get("monthly_burn_usd", 1)
        cash    = d.get("current_cash_usd", 0)
        runway  = cash / monthly if monthly > 0 else 0

        # 런웨이 충분성 (30점)
        score += min(30, runway * 1.5)

        # 자금조달 경로 명확성 (25점)
        score += min(25, len(plan) * 8)

        # 총 자금 조달 목표 설정 (20점)
        score += 20 if d.get("total_funding_needed_usd", 0) > 0 else 0

        # 지분 희석 관리 (15점) — 창업자 지분 50% 이상 유지 목표
        if plan:
            final_equity = plan[-1].get("equity_after_pct", 100)
            score += min(15, (final_equity / 50) * 15)

        # 자금 조달 다양화 (10점)
        sources = set()
        for p in plan:
            sources.update(p.get("sources", []))
        score += min(10, len(sources) * 2)

        return round(min(score, 100), 1)

    # ── 산출물 ───────────────────────────────────────────────────────────────
    def _build_output(self, d: dict, plan: list, score: float) -> dict:
        monthly = d.get("monthly_burn_usd", 1)
        cash    = d.get("current_cash_usd", 0)
        runway  = round(cash / monthly, 1) if monthly > 0 else 999
        total_plan = sum(p["amount_usd"] for p in plan)
        total_dilution = 100 - plan[-1].get("equity_after_pct", 100) if plan else 0

        llm_text = self._llm(
            f"현재 TRL: {d.get('current_trl',1)}, 목표 TRL: {d.get('target_trl',9)}\n"
            f"사업화 유형: {d.get('commercialization_type','startup')}\n"
            f"현재 런웨이: {runway}개월\n"
            f"총 필요 자금: ${d.get('total_funding_needed_usd',0):,.0f}\n"
            f"자금조달 계획 단계수: {len(plan)}\n"
            f"최종 창업자 지분: {plan[-1].get('equity_after_pct',100) if plan else 100}%\n\n"
            "자금조달 전략 핵심 조언 3가지와 주의사항 2가지를 JSON으로:\n"
            '{"key_advice":[],"cautions":[]}',
            system="스타트업 투자·기술사업화 재무 전문가. 실행 가능한 조언만. JSON 반환."
        )
        try:
            import json
            llm_out = json.loads(llm_text)
        except Exception:
            llm_out = {"key_advice": [], "cautions": []}

        return {
            "funding_plan": {
                "stages":              plan,
                "total_plan_usd":      round(total_plan),
                "total_dilution_pct":  round(total_dilution, 1),
                "founder_equity_final_pct": plan[-1].get("equity_after_pct", 100) if plan else 100,
                "total_stages":        len(plan),
            },
            "current_status": {
                "runway_months":       runway,
                "current_cash_usd":    d.get("current_cash_usd", 0),
                "monthly_burn_usd":    monthly,
                "has_revenue":         d.get("has_revenue", False),
            },
            "funding_strategy": {
                "commercialization_type": d.get("commercialization_type", "startup"),
                "recommended_next_stage": plan[0]["stage"] if plan else "계획 수립 필요",
                "immediate_target_usd":   plan[0]["amount_usd"] if plan else 0,
                "key_advice":            llm_out.get("key_advice", []),
                "cautions":              llm_out.get("cautions", []),
            },
            "dilution_simulation": [
                {
                    "round":          p["stage"],
                    "amount_usd":     p["amount_usd"],
                    "dilution_pct":   p.get("dilution_pct", 0),
                    "equity_pct":     p.get("equity_after_pct", 100),
                }
                for p in plan
            ],
            "funding_score": score,
        }

    def _next_actions(self, gate: str, d: dict, plan: list) -> list[str]:
        actions = []
        monthly = d.get("monthly_burn_usd", 1)
        cash    = d.get("current_cash_usd", 0)
        runway  = cash / monthly if monthly > 0 else 999

        if gate == "Go":
            if plan:
                actions.append(f"즉시 착수: {plan[0]['stage']} — ${plan[0]['amount_usd']:,.0f} 조달")
                actions.append(f"마일스톤: {plan[0].get('milestone','')}")
            actions.append("투자자 IR 자료 준비 (R6 IR Deck 생성 권고)")
        elif gate == "Hold":
            if runway < 12:
                actions.append(f"긴급: 런웨이 {runway:.0f}개월 — Bridge Loan 또는 정부 비희석 지원 즉시 신청")
            actions.append("자금 조달 목표 금액 구체화 후 재평가")
        else:
            actions.append("자금 조달 계획 전면 재수립: 총 필요 자금 및 마일스톤 정의 필요")
            if runway < 6:
                actions.append("런웨이 6개월 미만 위기 — 즉시 비용 구조 재검토 및 Bridge 자금 확보")
        return actions
