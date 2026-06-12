"""G2-Patent 권리성 심화 평가 — 신규성·비자명성·실시가능성 3축"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# 권리성 3대 요건
_PATENTABILITY_CRITERIA = {
    "novelty": {
        "name": "신규성 (Novelty)",
        "standard": "선행기술 어디에도 동일 발명 없음",
        "risk_factors": ["동일 특허 공개", "자기 공개(grace period 초과)", "비밀유지 위반"],
    },
    "inventive_step": {
        "name": "진보성/비자명성 (Inventive Step / Non-Obviousness)",
        "standard": "해당 분야 통상의 기술자가 자명하게 도출할 수 없음",
        "risk_factors": ["단순 결합 발명", "공지 기술의 치환", "통상의 기술자에게 명백한 최적화"],
    },
    "enablement": {
        "name": "실시가능성 (Enablement / Industrial Applicability)",
        "standard": "명세서 기재 기반으로 통상의 기술자가 재현 가능",
        "risk_factors": ["불충분한 실시예", "기능적 청구항 과도한 범위", "재현 불가 실험"],
    },
}

# FTO 리스크 수준별 대응
_FTO_ACTIONS = {
    "low": "진행 — 출원 즉시 가능, 경쟁사 청구항 범위 모니터링 지속",
    "medium": "주의 — 회피설계(Design-Around) 옵션 검토 후 출원",
    "high": "경고 — 전문 특허 대리인 FTO 의견서 취득 후 결정. 라이선스 협상 또는 회피설계 선행",
}


class PatentabilityAssessor(BaseAgent):
    stage_id = "G2-Patent"
    stage_name = "권리성 심화 평가"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          tech_name (str): 기술명
          spec_analysis (str): 명세서 요약 (발명의 상세한 설명)
          independent_claims (list of str): 독립청구항 목록
          prior_art_legal_opinion (str): 선행기술 법률 의견 (선행기술조사 결과)
          closest_prior_art (str): 가장 근접한 선행기술 설명
          technical_difference (str): 선행기술 대비 기술적 차이점
          dependent_claims_strength (str): weak/medium/strong
          enablement_evidence (list): 실시 가능성 증빙 (실험 데이터, 실시예)
          fto_risk (str): low/medium/high (G1 FTO 결과 연계)
          self_disclosure_date (str, optional): 발명자 공개일 (신규성 상실 위험)
        """
        novelty = self._assess_novelty(input_data)
        inventive = self._assess_inventive_step(input_data)
        enablement = self._assess_enablement(input_data)

        score = round(novelty * 0.35 + inventive * 0.40 + enablement * 0.25, 1)
        gate = self._gate_from_score(score)
        output_doc = self._build_output(input_data, score, novelty, inventive, enablement)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output_doc,
            next_actions=self._next_actions(gate, input_data),
            warnings=self._warnings(input_data),
        )

    def _assess_novelty(self, d: dict) -> float:
        score = 100.0
        if not d.get("prior_art_legal_opinion"):
            score -= 30
        if not d.get("closest_prior_art"):
            score -= 20
        if not d.get("technical_difference"):
            score -= 20
        # 자기공개 위험
        if d.get("self_disclosure_date"):
            score -= 15
        return max(0, score)

    def _assess_inventive_step(self, d: dict) -> float:
        score = 50.0
        diff = d.get("technical_difference", "")
        score += 20 if len(diff) >= 100 else 10 if len(diff) >= 50 else 0
        # 종속항 강도
        strength_map = {"strong": 30, "medium": 15, "weak": 0}
        score += strength_map.get(d.get("dependent_claims_strength", "weak"), 0)
        return min(100, score)

    def _assess_enablement(self, d: dict) -> float:
        evidence = d.get("enablement_evidence", [])
        score = 0.0
        score += min(60, len(evidence) * 20)
        if d.get("spec_analysis") and len(d.get("spec_analysis", "")) >= 300:
            score += 40
        elif d.get("spec_analysis"):
            score += 20
        return min(100, score)

    def _build_output(self, d: dict, score: float,
                      novelty: float, inventive: float, enablement: float) -> dict:
        fto_risk = d.get("fto_risk", "medium")
        claims = d.get("independent_claims", [])

        llm_result = self._llm(
            f"기술: {d.get('tech_name', '')}\n"
            f"명세서 요약: {d.get('spec_analysis', '')[:300]}\n"
            f"가장 근접 선행기술: {d.get('closest_prior_art', '')}\n"
            f"기술적 차이점: {d.get('technical_difference', '')}\n"
            f"독립청구항: {claims[:3]}\n\n"
            "권리성 종합 법률 의견을 JSON으로:\n"
            '{"overall_opinion":"","novelty_analysis":"","inventive_step_analysis":"",'
            '"rejection_risks":[],"strengthening_recommendations":[]}',
            system="특허 권리성 평가 전문가. JSON만 반환."
        )
        try:
            import json
            legal_opinion = json.loads(llm_result)
        except Exception:
            legal_opinion = {
                "overall_opinion": f"신규성 {novelty:.0f}점, 진보성 {inventive:.0f}점, 실시가능성 {enablement:.0f}점",
                "rejection_risks": ["선행기술 대비 기술적 차이 명확화 필요"] if inventive < 60 else [],
            }

        return {
            "patentability_assessment": {
                "tech_name": d.get("tech_name", ""),
                "novelty_score": novelty,
                "inventive_step_score": inventive,
                "enablement_score": enablement,
                "composite_score": score,
                "criteria_detail": _PATENTABILITY_CRITERIA,
            },
            "legal_risk_matrix": {
                "fto_risk": fto_risk,
                "fto_action": _FTO_ACTIONS.get(fto_risk, ""),
                "self_disclosure_risk": bool(d.get("self_disclosure_date")),
                "claim_scope_risk": d.get("dependent_claims_strength", "weak") == "weak",
                "enablement_risk": len(d.get("enablement_evidence", [])) < 2,
            },
            "legal_opinion": legal_opinion,
            "independent_claims_reviewed": claims,
            "patentability_score": score,
        }

    def _next_actions(self, gate: str, d: dict) -> list[str]:
        if gate == "Go":
            return [
                "특허 출원 진행 — 청구항 최종 확정 후 대리인 의뢰",
                "G1-Portfolio와 연계하여 출원 국가 우선순위 확정",
                "등록 후 FTO 모니터링 프로그램 가동",
            ]
        if gate == "Hold":
            actions = []
            if not d.get("technical_difference"):
                actions.append("선행기술 대비 기술적 차이점 명확화 (200자 이상)")
            if not d.get("enablement_evidence"):
                actions.append("실시 가능성 증빙 추가: 실험 데이터, 실시예 최소 2건")
            if d.get("dependent_claims_strength") == "weak":
                actions.append("종속청구항 보강: 수치 한정, 재료 특정, 단계 구체화")
            return actions
        return [
            "권리성 불충분 — 청구항 전면 재설계 필요",
            "G1 IP구조화 단계로 복귀하여 청구항 재구성",
        ]

    def _warnings(self, d: dict) -> list[str]:
        warns = []
        if d.get("self_disclosure_date"):
            warns.append(f"자기공개 위험: {d['self_disclosure_date']} 공개 → 신규성 상실 가능. 즉시 출원 필요")
        if d.get("fto_risk") == "high":
            warns.append("FTO 고위험: 경쟁사 특허 침해 가능성. 전문가 의견서 취득 후 진행")
        if not d.get("enablement_evidence"):
            warns.append("실시 가능성 증빙 없음: 출원 후 거절이유 통지 위험")
        return warns
