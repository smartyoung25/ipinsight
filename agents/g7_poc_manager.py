"""G7 PoC·실증·위험저감 — Catapult Network·Fraunhofer 응용연구 모델"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult


class PoCManager(BaseAgent):
    stage_id = "G7"
    stage_name = "PoC·실증·위험저감"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data: tech_name, poc_objectives (list), poc_kpis (list of {name, target, actual}),
                    test_environment, customer_feedback (list), issues_found (list),
                    risk_mitigations (list), poc_duration_months
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
        kpis = d.get("poc_kpis", [])
        # KPI 달성률 (40점)
        if kpis:
            achieved = sum(1 for k in kpis if k.get("actual", 0) >= k.get("target", 1))
            score += 40 * (achieved / len(kpis))
        # 고객 피드백 (25점)
        feedbacks = d.get("customer_feedback", [])
        positive = sum(1 for f in feedbacks if f.get("sentiment", "") == "positive")
        score += 25 * (positive / max(len(feedbacks), 1))
        # 위험저감 조치 (20점)
        score += min(20, len(d.get("risk_mitigations", [])) * 5)
        # PoC 목표 명확성 (15점)
        score += 15 if d.get("poc_objectives") else 0
        return round(min(score, 100), 1)

    def _build_output(self, d: dict, score: float) -> dict:
        kpis = d.get("poc_kpis", [])
        kpi_results = []
        for k in kpis:
            target = k.get("target", 1)
            actual = k.get("actual", 0)
            achievement = round(actual / max(target, 0.001) * 100, 1)
            kpi_results.append({
                "name": k.get("name", ""),
                "target": target,
                "actual": actual,
                "achievement_pct": achievement,
                "status": "달성" if actual >= target else "미달성",
            })

        issues = d.get("issues_found", [])
        mitigations = d.get("risk_mitigations", [])

        llm_result = self._llm(
            f"PoC 결과: {kpi_results}\n"
            f"발견 이슈: {issues}\n"
            f"고객 피드백: {d.get('customer_feedback', [])}\n\n"
            "상용화 준비도와 개선 로드맵을 JSON으로:\n"
            '{"commercialization_readiness":"low/medium/high",'
            '"critical_issues":[], "improvement_roadmap":[], "next_poc_needed":true}',
            system="기술실증 전문가. JSON만 반환."
        )
        try:
            import json
            analysis = json.loads(llm_result)
        except Exception:
            analysis = {"commercialization_readiness": "medium", "improvement_roadmap": []}

        return {
            "poc_plan": {
                "tech_name": d.get("tech_name", ""),
                "objectives": d.get("poc_objectives", []),
                "test_environment": d.get("test_environment", ""),
                "duration_months": d.get("poc_duration_months", 0),
            },
            "poc_kpi_report": kpi_results,
            "performance_result": {
                "overall_score": score,
                "kpi_achievement_rate": round(sum(1 for k in kpi_results if k["status"] == "달성") / max(len(kpi_results), 1) * 100, 1),
                "customer_feedback_summary": d.get("customer_feedback", []),
            },
            "risk_mitigation_report": {
                "issues_found": issues,
                "mitigations_applied": mitigations,
                "residual_risks": [i for i in issues if i not in mitigations],
            },
            "commercialization_analysis": analysis,
        }

    def _next_actions(self, gate: str) -> list[str]:
        if gate == "Go":
            return [
                "G8 MRL·ARL 평가로 양산·채택 준비도 확인",
                "PoC 결과를 레퍼런스로 고객사 상용 계약 협의",
                "인증·규제 취득 로드맵 수립",
            ]
        if gate == "Hold":
            return [
                "미달성 KPI 개선 후 추가 PoC 실시",
                "핵심 이슈 해결을 위한 R&D 스프린트",
                "고객 피드백 기반 제품 수정",
            ]
        return [
            "PoC 실패 — 기술 근본 문제 재검토",
            "G2 TRL 평가 재실시 또는 기술 방향 전환",
        ]
