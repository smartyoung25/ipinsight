"""G5 사업모델·GTM 전략 설계 — BMC + Lean Startup + EIC BM 검증"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult


class BMDesigner(BaseAgent):
    stage_id = "G5"
    stage_name = "사업모델·GTM 전략 설계"

    _REVENUE_MODELS = {
        "license": "라이선싱 (선급금 + 로열티)",
        "saas": "SaaS 구독 (월/연 구독료)",
        "hardware_sale": "하드웨어 판매 + 유지보수",
        "service": "기술서비스·컨설팅",
        "platform": "플랫폼 수수료",
        "joint_dev": "공동개발 비용분담",
        "public_procurement": "공공조달·정부사업",
    }

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data: tech_name, customer_segments, value_proposition,
                    channels, revenue_model (list), cost_structure,
                    key_partners, gtm_target_market, gtm_timeline_months
        """
        score = self._score(input_data)
        gate = self._gate_from_score(score)
        output_doc = self._build_output(input_data, score)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output_doc,
            next_actions=self._next_actions(gate),
        )

    def _score(self, d: dict) -> float:
        score = 0.0
        # 가치제안 명확성 (25점)
        vp = d.get("value_proposition", "")
        score += 25 if len(vp) > 30 else len(vp) * 0.8
        # 수익모델 선택 (20점)
        score += 20 if d.get("revenue_model") else 0
        # 고객 세그먼트 (20점)
        score += 20 if d.get("customer_segments") else 0
        # 채널 전략 (15점)
        score += 15 if d.get("channels") else 0
        # GTM 계획 (20점)
        score += 20 if d.get("gtm_target_market") and d.get("gtm_timeline_months") else 0
        return round(min(score, 100), 1)

    def _build_output(self, d: dict, score: float) -> dict:
        revenue_models = d.get("revenue_model", [])
        model_details = {m: self._REVENUE_MODELS.get(m, m) for m in revenue_models}

        llm_result = self._llm(
            f"기술: {d.get('tech_name', '')}\n"
            f"고객: {d.get('customer_segments', '')}\n"
            f"가치제안: {d.get('value_proposition', '')}\n"
            f"수익모델: {revenue_models}\n"
            f"GTM 목표시장: {d.get('gtm_target_market', '')}\n\n"
            "최적 가격전략과 GTM 실행계획을 JSON으로:\n"
            '{"pricing_strategy":"","price_point_usd":0,"gtm_phases":[],'
            '"beachhead_market":"","key_milestones":[],"partnership_targets":[]}',
            system="GTM 전략 전문가. JSON만 반환."
        )
        try:
            import json
            gtm = json.loads(llm_result)
        except Exception:
            gtm = {"pricing_strategy": llm_result, "gtm_phases": []}

        royalty_kb = self._load_knowledge("royalty_benchmarks.json")

        return {
            "business_model_canvas": {
                "customer_segments": d.get("customer_segments", []),
                "value_proposition": d.get("value_proposition", ""),
                "channels": d.get("channels", []),
                "revenue_streams": model_details,
                "cost_structure": d.get("cost_structure", {}),
                "key_partners": d.get("key_partners", []),
            },
            "revenue_model_design": {
                "selected_models": revenue_models,
                "model_descriptions": model_details,
                "royalty_benchmarks": royalty_kb.get("deal_structures", {}),
            },
            "gtm_strategy": gtm,
            "partnership_strategy": {
                "target_markets": [d.get("gtm_target_market", "")],
                "global_support_channels": ["KOTRA", "EEN (Enterprise Europe Network)", "Enterprise Singapore"],
                "timeline_months": d.get("gtm_timeline_months", 12),
            },
            "bm_score": score,
        }

    def _next_actions(self, gate: str) -> list[str]:
        if gate == "Go":
            return [
                "G6 IP·기술 가치평가 진행",
                "Beachhead 고객 3개사 파일럿 계약 체결",
                "파트너십 NDA 체결 및 협상 시작",
            ]
        if gate == "Hold":
            return [
                "수익모델 재설계 (시장 피드백 반영)",
                "가격전략 A/B 테스트 설계",
                "채널 파트너 후보 발굴",
            ]
        return [
            "사업모델 부재 — 기술 적용분야 Pivot 검토",
            "G4 고객검증 재실시 후 BM 재설계",
        ]
