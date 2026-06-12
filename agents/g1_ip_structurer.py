"""G1 IP 구조화·FTO 분석 — Stanford/MIT TLO 방식"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult


class IPStructurer(BaseAgent):
    stage_id = "G1"
    stage_name = "IP 구조화·FTO 분석"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data: patent_claims, spec_summary, prior_art_list,
                    competitor_patents, filing_status
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
        claims = d.get("patent_claims", [])
        # 독립항 존재 (30점)
        independent = [c for c in claims if c.get("type") == "independent"]
        score += min(30, len(independent) * 10)
        # 명세서 완성도 (25점)
        spec = d.get("spec_summary", "")
        score += 25 if len(spec) > 200 else len(spec) / 8
        # 선행기술 조사 여부 (20점)
        score += 20 if d.get("prior_art_list") else 0
        # 경쟁특허 분석 여부 (15점)
        score += 15 if d.get("competitor_patents") else 0
        # 출원 상태 (10점)
        status = d.get("filing_status", "")
        score += {"filed": 10, "provisional": 7, "pending": 5}.get(status, 0)
        return round(min(score, 100), 1)

    def _build_output(self, d: dict, score: float) -> dict:
        claims = d.get("patent_claims", [])
        independent = [c for c in claims if c.get("type") == "independent"]
        dependent = [c for c in claims if c.get("type") == "dependent"]

        llm_result = self._llm(
            f"특허 청구항 구조: {claims}\n선행기술: {d.get('prior_art_list', [])}\n\n"
            "FTO 1차 검토 결과를 JSON으로 반환:\n"
            '{"fto_risk":"low/medium/high", "key_risks":[], "evasion_design":[], "recommendation":""}',
            system="특허 전문가. JSON만 반환."
        )
        try:
            import json
            fto = json.loads(llm_result)
        except Exception:
            fto = {"fto_risk": "unknown", "key_risks": [], "evasion_design": [], "recommendation": llm_result}

        return {
            "ip_structure_report": {
                "total_claims": len(claims),
                "independent_claims": len(independent),
                "dependent_claims": len(dependent),
                "claim_mapping": [
                    {"claim_no": c.get("no"), "type": c.get("type"), "elements": c.get("elements", [])}
                    for c in claims
                ],
                "rights_scope_summary": d.get("spec_summary", "")[:500],
            },
            "prior_art_comparison": {
                "prior_arts_reviewed": len(d.get("prior_art_list", [])),
                "prior_art_list": d.get("prior_art_list", []),
                "novelty_assessment": "신규성 있음" if score >= 60 else "추가 검토 필요",
            },
            "fto_review": fto,
            "filing_status": d.get("filing_status", "미출원"),
            "ip_strength_score": score,
        }

    def _warnings(self, d: dict) -> list[str]:
        w = []
        if not d.get("prior_art_list"):
            w.append("선행기술 조사 미실시 — FTO 리스크 미평가")
        if not d.get("competitor_patents"):
            w.append("경쟁특허 분석 부재 — 침해 리스크 불명확")
        if d.get("filing_status", "") == "":
            w.append("미출원 상태 — 임시특허 즉시 출원 권고")
        return w

    def _next_actions(self, gate: str) -> list[str]:
        if gate == "Go":
            return [
                "G2 TRL 평가 진행",
                "PCT 출원 국가 선정 (핵심 12개국)",
                "독립항 중심 권리범위 최대화 전략 수립",
            ]
        if gate == "Hold":
            return [
                "독립항 보강 출원 (continuation/CIP)",
                "선행기술 추가 조사 실시",
                "FTO 전문 특허법인 검토 의뢰",
            ]
        return [
            "현 IP 구조로는 사업화 위험 — 전면 재설계 검토",
            "방어적 공개(Defensive Publication) 대안 검토",
        ]
