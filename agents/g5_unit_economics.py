"""G5-UE: 단위경제성 평가 — CAC·LTV·Burn Rate·손익분기 분석
SaaS·라이선스·하드웨어·서비스 4개 수익모델별 단위경제성 산출.
"""
from __future__ import annotations
import math
from .base_agent import BaseAgent, StageResult

# 수익모델별 업계 평균 LTV/CAC 비율 기준
_LTV_CAC_BENCHMARKS = {
    "saas":         {"ltv_cac_target": 3.0, "payback_months_target": 12, "gross_margin_pct": 70},
    "license":      {"ltv_cac_target": 5.0, "payback_months_target": 18, "gross_margin_pct": 85},
    "hardware":     {"ltv_cac_target": 2.0, "payback_months_target": 24, "gross_margin_pct": 40},
    "service":      {"ltv_cac_target": 2.5, "payback_months_target": 18, "gross_margin_pct": 50},
    "marketplace":  {"ltv_cac_target": 4.0, "payback_months_target": 12, "gross_margin_pct": 60},
    "data":         {"ltv_cac_target": 6.0, "payback_months_target": 6,  "gross_margin_pct": 80},
    "hybrid":       {"ltv_cac_target": 3.5, "payback_months_target": 15, "gross_margin_pct": 60},
}


class UnitEconomicsAssessor(BaseAgent):
    stage_id   = "G5-UE"
    stage_name = "단위경제성(CAC·LTV·Burn) 평가"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          revenue_model (str): saas/license/hardware/service/marketplace/data/hybrid
          avg_contract_value_usd (float): 평균 계약 금액 (연간 또는 건당)
          avg_contract_months (int): 평균 계약 기간 (월)
          churn_rate_monthly_pct (float): 월별 이탈률 % (SaaS) 또는 계약 갱신율
          gross_margin_pct (float): 매출총이익률 %
          sales_marketing_spend_usd (float): 월 영업·마케팅 비용
          new_customers_per_month (int): 월 신규 고객 수
          monthly_burn_usd (float): 월 현금 소진 (운영비 전체)
          cash_on_hand_usd (float): 현재 보유 현금
          monthly_revenue_usd (float, optional): 현재 월 매출
          headcount (int, optional): 총 인원
        """
        metrics = self._compute_metrics(input_data)
        score   = self._score(metrics, input_data)
        gate    = self._gate_from_score(score)
        output  = self._build_output(input_data, metrics, score)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output,
            next_actions=self._next_actions(gate, metrics),
        )

    # ── 핵심 지표 계산 ───────────────────────────────────────────────────────
    def _compute_metrics(self, d: dict) -> dict:
        model   = d.get("revenue_model", "saas")
        bench   = _LTV_CAC_BENCHMARKS.get(model, _LTV_CAC_BENCHMARKS["saas"])

        acv     = d.get("avg_contract_value_usd", 0)
        months  = max(1, d.get("avg_contract_months", 12))
        churn   = d.get("churn_rate_monthly_pct", 2.0) / 100
        gm_pct  = d.get("gross_margin_pct", bench["gross_margin_pct"]) / 100
        sm_spend = d.get("sales_marketing_spend_usd", 0)
        new_cust = max(1, d.get("new_customers_per_month", 1))
        burn     = d.get("monthly_burn_usd", 0)
        cash     = d.get("cash_on_hand_usd", 0)
        rev      = d.get("monthly_revenue_usd", 0)

        # CAC
        cac = sm_spend / new_cust if new_cust > 0 else 0

        # LTV
        if model in ("saas", "marketplace", "data"):
            avg_lifetime_months = 1 / churn if churn > 0 else months
            mrr_per_customer    = acv / 12
            ltv = mrr_per_customer * gm_pct * avg_lifetime_months
        else:
            # 라이선스·하드웨어·서비스: 계약기간 기반
            ltv = acv * gm_pct * (months / 12)

        ltv_cac = ltv / cac if cac > 0 else float("inf")

        # Payback period (months)
        monthly_gm_per_customer = (acv / 12) * gm_pct if model in ("saas","marketplace","data") else (acv / months) * gm_pct
        payback_months = cac / monthly_gm_per_customer if monthly_gm_per_customer > 0 else float("inf")

        # Runway
        net_burn = max(0, burn - rev)
        runway_months = cash / net_burn if net_burn > 0 else float("inf")

        # Break-even MRR
        fixed_costs = burn - sm_spend
        breakeven_mrr = fixed_costs / gm_pct if gm_pct > 0 else 0
        breakeven_customers = math.ceil(breakeven_mrr / (acv / 12)) if acv > 0 else 0

        # Magic Number (SaaS)
        magic_number = (rev * gm_pct) / sm_spend if sm_spend > 0 and model in ("saas","data") else None

        return {
            "cac_usd":              round(cac),
            "ltv_usd":              round(ltv),
            "ltv_cac_ratio":        round(ltv_cac, 2) if ltv_cac != float("inf") else 999,
            "payback_months":       round(payback_months, 1) if payback_months != float("inf") else 999,
            "runway_months":        round(runway_months, 1) if runway_months != float("inf") else 999,
            "breakeven_mrr_usd":    round(breakeven_mrr),
            "breakeven_customers":  breakeven_customers,
            "magic_number":         round(magic_number, 2) if magic_number is not None else None,
            "gross_margin_pct":     round(gm_pct * 100, 1),
            "net_burn_usd":         round(net_burn),
            "benchmark":            bench,
            "revenue_model":        model,
        }

    # ── 점수 ─────────────────────────────────────────────────────────────────
    def _score(self, m: dict, d: dict) -> float:
        bench  = m["benchmark"]
        score  = 0.0

        # LTV/CAC 비율 (35점)
        ltv_cac = m["ltv_cac_ratio"]
        target  = bench["ltv_cac_target"]
        score += min(35, (ltv_cac / target) * 35)

        # Payback period (25점)
        payback = m["payback_months"]
        pb_tgt  = bench["payback_months_target"]
        if payback <= pb_tgt:
            score += 25
        elif payback < pb_tgt * 2:
            score += 12

        # 런웨이 (20점)
        runway = m["runway_months"]
        if runway >= 18:
            score += 20
        elif runway >= 12:
            score += 15
        elif runway >= 6:
            score += 8

        # 매출총이익률 (20점)
        gm = m["gross_margin_pct"]
        gm_tgt = bench["gross_margin_pct"]
        score += min(20, (gm / gm_tgt) * 20)

        return round(min(score, 100), 1)

    # ── 산출물 ───────────────────────────────────────────────────────────────
    def _build_output(self, d: dict, m: dict, score: float) -> dict:
        bench = m["benchmark"]

        # 상태 판정
        def status(val, good, warn):
            if val >= good: return "우수"
            if val >= warn: return "보통"
            return "위험"

        health = {
            "ltv_cac":   status(m["ltv_cac_ratio"], bench["ltv_cac_target"], bench["ltv_cac_target"] * 0.5),
            "payback":   status(bench["payback_months_target"], m["payback_months"], bench["payback_months_target"] * 1.5),
            "runway":    status(m["runway_months"], 18, 12),
            "margin":    status(m["gross_margin_pct"], bench["gross_margin_pct"], bench["gross_margin_pct"] * 0.7),
        }

        # LLM: 개선 시나리오
        llm_text = self._llm(
            f"수익모델: {m['revenue_model']}\n"
            f"LTV/CAC: {m['ltv_cac_ratio']} (목표: {bench['ltv_cac_target']})\n"
            f"Payback: {m['payback_months']}개월 (목표: {bench['payback_months_target']})\n"
            f"런웨이: {m['runway_months']}개월\n"
            f"매출총이익률: {m['gross_margin_pct']}%\n"
            f"CAC: ${m['cac_usd']:,}  LTV: ${m['ltv_usd']:,}\n"
            f"손익분기 고객수: {m['breakeven_customers']}\n\n"
            "단위경제성 개선 방안 3가지(CAC절감·LTV향상·비용최적화)를 JSON으로:\n"
            '{"improvements":[{"area":"","action":"","expected_impact":""}]}',
            system="SaaS·기술사업화 재무 전문가. 구체적 수치 기반 개선안을 JSON만 반환."
        )
        try:
            import json
            llm_out = json.loads(llm_text)
        except Exception:
            llm_out = {"improvements": []}

        return {
            "unit_economics": {
                "revenue_model":       m["revenue_model"],
                "cac_usd":             m["cac_usd"],
                "ltv_usd":             m["ltv_usd"],
                "ltv_cac_ratio":       m["ltv_cac_ratio"],
                "payback_months":      m["payback_months"],
                "gross_margin_pct":    m["gross_margin_pct"],
                "magic_number":        m["magic_number"],
            },
            "financial_health": {
                "runway_months":        m["runway_months"],
                "net_burn_usd":         m["net_burn_usd"],
                "breakeven_mrr_usd":    m["breakeven_mrr_usd"],
                "breakeven_customers":  m["breakeven_customers"],
            },
            "benchmark_comparison": {
                "ltv_cac_target":       bench["ltv_cac_target"],
                "payback_target_months": bench["payback_months_target"],
                "gross_margin_target_pct": bench["gross_margin_pct"],
                "ltv_cac_status":       health["ltv_cac"],
                "payback_status":       health["payback"],
                "runway_status":        health["runway"],
                "margin_status":        health["margin"],
            },
            "improvements": llm_out.get("improvements", []),
            "unit_economics_score": score,
        }

    def _next_actions(self, gate: str, m: dict) -> list[str]:
        actions = []
        bench   = m["benchmark"]
        if gate == "Go":
            actions.append("단위경제성 우수 — G6 가치평가 DCF 모델에 LTV/CAC 반영")
            actions.append(f"LTV/CAC {m['ltv_cac_ratio']} 유지하며 확장 마케팅 집행")
        elif gate == "Hold":
            if m["ltv_cac_ratio"] < bench["ltv_cac_target"]:
                actions.append(f"LTV/CAC {m['ltv_cac_ratio']} → {bench['ltv_cac_target']} 목표: CAC 절감 또는 계약 기간 연장")
            if m["runway_months"] < 12:
                actions.append(f"런웨이 {m['runway_months']}개월 위험 — 즉시 Bridge 자금 확보 또는 번 레이트 절감")
            if m["gross_margin_pct"] < bench["gross_margin_pct"] * 0.7:
                actions.append("원가 구조 재검토: 아웃소싱·자동화로 매출총이익률 개선")
        else:
            actions.append("단위경제성 전면 재설계: 수익모델 변경 또는 고객 세그먼트 재정의 필요")
            actions.append(f"현재 런웨이 {m['runway_months']}개월 — 긴급 자금 조달 또는 비용 50% 절감 필요")
        return actions
