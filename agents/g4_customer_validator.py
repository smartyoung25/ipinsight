"""G4 고객발견·수요검증 — NSF I-Corps Customer Discovery 방법론"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult


class CustomerValidator(BaseAgent):
    stage_id = "G4"
    stage_name = "고객발견·수요검증"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data: interviews (list of {customer_type, pain_point, willingness_to_pay,
                    alternative_used, urgency_1to5}),
                    loi_count, poc_requests, survey_responses
        """
        score = self._score(input_data)
        gate = self._gate_from_score(score)
        output_doc = self._build_output(input_data, score)
        warnings = self._warnings(input_data)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output_doc,
            next_actions=self._next_actions(gate),
            warnings=warnings,
        )

    def _score(self, d: dict) -> float:
        score = 0.0
        interviews = d.get("interviews", [])
        # 인터뷰 수 (30점) — I-Corps는 최소 100건 요구, 30건을 기준
        score += min(30, len(interviews) * 1.0)
        # 지불의사 확인 비율 (25점)
        wtp_confirmed = sum(1 for i in interviews if i.get("willingness_to_pay", 0) > 0)
        score += 25 * (wtp_confirmed / max(len(interviews), 1))
        # LoI/PoC 요청 (25점)
        score += min(25, d.get("loi_count", 0) * 5 + d.get("poc_requests", 0) * 3)
        # 긴급도 평균 (20점)
        urgencies = [i.get("urgency_1to5", 0) for i in interviews]
        avg_urgency = sum(urgencies) / max(len(urgencies), 1)
        score += avg_urgency * 4
        return round(min(score, 100), 1)

    def _build_output(self, d: dict, score: float) -> dict:
        interviews = d.get("interviews", [])
        # 페르소나 그룹화
        personas: dict = {}
        for i in interviews:
            ct = i.get("customer_type", "미분류")
            personas.setdefault(ct, []).append(i)

        persona_summary = []
        for ctype, items in personas.items():
            wtps = [x.get("willingness_to_pay", 0) for x in items]
            persona_summary.append({
                "customer_type": ctype,
                "interview_count": len(items),
                "avg_willingness_to_pay_usd": round(sum(wtps) / max(len(wtps), 1), 0),
                "top_pain_points": list({x.get("pain_point", "") for x in items})[:3],
                "avg_urgency": round(sum(x.get("urgency_1to5", 0) for x in items) / max(len(items), 1), 1),
            })

        llm_result = self._llm(
            f"고객 인터뷰 요약: {personas}\n"
            f"LoI 수: {d.get('loi_count', 0)}, PoC 요청: {d.get('poc_requests', 0)}\n\n"
            "문제-솔루션 적합성(PSF) 평가와 구매 결정 구조를 JSON으로:\n"
            '{"psf_score":0-100, "key_buying_triggers":[], "adoption_barriers":[],'
            '"recommended_persona":"", "pricing_signal_usd":0}',
            system="린스타트업 전문가. JSON만 반환."
        )
        try:
            import json
            psf = json.loads(llm_result)
        except Exception:
            psf = {"psf_score": score, "key_buying_triggers": [], "adoption_barriers": []}

        return {
            "customer_discovery_report": {
                "total_interviews": len(interviews),
                "loi_count": d.get("loi_count", 0),
                "poc_requests": d.get("poc_requests", 0),
                "persona_summary": persona_summary,
                "validation_score": score,
            },
            "psf_analysis": psf,
            "purchase_intent_analysis": {
                "confirmed_wtp_count": sum(1 for i in interviews if i.get("willingness_to_pay", 0) > 0),
                "avg_wtp_usd": round(sum(i.get("willingness_to_pay", 0) for i in interviews) / max(len(interviews), 1), 0),
                "urgency_distribution": {
                    "high_4to5": sum(1 for i in interviews if i.get("urgency_1to5", 0) >= 4),
                    "medium_3": sum(1 for i in interviews if i.get("urgency_1to5", 0) == 3),
                    "low_1to2": sum(1 for i in interviews if i.get("urgency_1to5", 0) <= 2),
                },
            },
            "interview_question_template": self._interview_template(),
        }

    def _interview_template(self) -> list[str]:
        return [
            "현재 이 문제를 어떻게 해결하고 있습니까?",
            "기존 해결책의 가장 큰 불만은 무엇입니까?",
            "이 문제로 인해 연간 얼마의 비용/손실이 발생합니까?",
            "새로운 해결책에 연간 얼마를 지불할 의향이 있습니까?",
            "도입 결정권자는 누구입니까? 예산 규모는?",
            "도입 시 가장 큰 우려사항은 무엇입니까?",
        ]

    def _warnings(self, d: dict) -> list[str]:
        w = []
        interviews = d.get("interviews", [])
        if len(interviews) < 10:
            w.append(f"인터뷰 {len(interviews)}건 — I-Corps 기준 최소 30건 필요")
        if d.get("loi_count", 0) == 0:
            w.append("LoI(의향서) 미확보 — 구매의향 실증 필요")
        return w

    def _next_actions(self, gate: str) -> list[str]:
        if gate == "Go":
            return [
                "G5 사업모델·GTM 설계 진행",
                "핵심 고객 3개사와 파일럿 계약 협의",
                "확보한 LoI를 기반으로 투자자 미팅 준비",
            ]
        if gate == "Hold":
            return [
                "추가 고객 인터뷰 진행 (목표: 30건 이상)",
                "LoI 또는 PoC 요청서 최소 3건 확보",
                "고객군 재정의 또는 가치제안 수정",
            ]
        return [
            "수요 없음 확인 — 기술 적용분야 전환 검토 (Pivot)",
            "고객군 완전 재설정 후 G3부터 재시작",
        ]
