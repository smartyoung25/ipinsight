"""G2 TRL 자동 평가 — NASA TRL 1~9 Evidence-based"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult


class TRLAssessor(BaseAgent):
    stage_id = "G2"
    stage_name = "기술성숙도(TRL) 평가"

    _TRL_EVIDENCE = {
        1: ["학술논문", "연구노트", "이론 계산서"],
        2: ["개념 보고서", "타당성 검토서"],
        3: ["실험 결과", "시뮬레이션 데이터", "PoC 보고서"],
        4: ["시험성적서", "성능평가 보고서", "실험실 검증 결과"],
        5: ["환경시험 결과", "시제품 보고서", "외부 검증 결과"],
        6: ["프로토타입", "시연 영상", "성능 비교표"],
        7: ["파일럿 테스트 결과", "현장 테스트 보고서", "고객 피드백"],
        8: ["인증서", "품질검사 결과", "계약서", "양산 계획"],
        9: ["매출 실적", "고객 레퍼런스", "양산 실적", "A/S 이력"],
    }

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data: tech_description, evidence_list (각 항목: type, description, date),
                    claimed_trl, target_trl
        """
        current_trl = self._determine_trl(input_data)
        target_trl = input_data.get("target_trl", 9)
        gap = target_trl - current_trl
        score = (current_trl / 9) * 100
        gate = self._gate_from_score(score)

        trl_kb = self._load_knowledge("trl_framework.json")
        trl_info = next((l for l in trl_kb.get("levels", []) if l["trl"] == current_trl), {})

        funding_match = self._match_funding(current_trl)

        output_doc = {
            "trl_assessment": {
                "current_trl": current_trl,
                "target_trl": target_trl,
                "trl_gap": gap,
                "trl_name": trl_info.get("name", ""),
                "trl_description": trl_info.get("description", ""),
                "expected_duration_months": trl_info.get("typical_duration_months", 0) * gap,
            },
            "evidence_mapping": self._map_evidence(input_data.get("evidence_list", []), current_trl),
            "gap_analysis": {
                "missing_evidence": self._TRL_EVIDENCE.get(current_trl + 1, []),
                "required_activities": self._gap_activities(current_trl, target_trl),
                "estimated_cost_krw": gap * 200_000_000,
            },
            "risk_report": self._risk_report(current_trl),
            "funding_recommendations": funding_match,
            "trl_score": round(score, 1),
        }

        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output_doc,
            next_actions=self._next_actions(current_trl, gate),
        )

    def _determine_trl(self, d: dict) -> int:
        evidence_list = d.get("evidence_list", [])
        claimed = d.get("claimed_trl", 0)

        evidence_types = {e.get("type", "").lower() for e in evidence_list}
        inferred = 1
        for trl in range(1, 10):
            required = [ev.lower() for ev in self._TRL_EVIDENCE.get(trl, [])]
            if any(r in " ".join(evidence_types) for r in required):
                inferred = trl

        # 클레임과 추론값의 보수적 선택
        return min(claimed, inferred) if claimed > 0 else inferred

    def _map_evidence(self, evidence_list: list, current_trl: int) -> list:
        result = []
        for ev in evidence_list:
            result.append({
                "type": ev.get("type", ""),
                "description": ev.get("description", ""),
                "date": ev.get("date", ""),
                "supports_trl": current_trl,
                "verified": bool(ev.get("description")),
            })
        return result

    def _gap_activities(self, current: int, target: int) -> list[str]:
        activities = {
            3: ["실험실 PoC 수행", "시제품 제작 계획 수립"],
            4: ["시험성적서 취득", "외부 기관 성능 검증"],
            5: ["실제 환경 모사 테스트", "시제품 성능 한계 시험"],
            6: ["프로토타입 현장 시연", "고객사 방문 시연"],
            7: ["파일럿 사이트 확보", "현장 검증 계약"],
            8: ["인증 취득 (KC/CE/FDA)", "양산 계획 수립"],
            9: ["초기 고객 계약 체결", "양산 라인 가동"],
        }
        result = []
        for trl in range(current + 1, min(target + 1, 10)):
            result.extend(activities.get(trl, []))
        return result

    def _risk_report(self, current_trl: int) -> dict:
        risk_level = "High" if current_trl <= 3 else "Medium" if current_trl <= 6 else "Low"
        return {
            "overall_risk": risk_level,
            "technical_risk": "High" if current_trl <= 4 else "Low",
            "performance_risk": "Medium" if current_trl <= 6 else "Low",
            "certification_risk": "High" if current_trl <= 5 else "Medium",
        }

    def _match_funding(self, trl: int) -> list[str]:
        programs = self._load_knowledge("country_programs.json").get("programs", [])
        matched = []
        for p in programs:
            trl_range = p.get("trl_range", [0, 0])
            if trl_range[0] <= trl <= trl_range[1]:
                matched.append(f"{p['country']} — {p['name']}: {p.get('notes', '')}")
        return matched[:5]

    def _next_actions(self, trl: int, gate: str) -> list[str]:
        if gate == "Go":
            return [
                f"현재 TRL {trl} → 다음 TRL {trl+1} 달성 계획 수립",
                "G3 시장성 평가 병행 시작",
                f"TRL {trl} 기반 정부지원 프로그램 신청",
            ]
        return [
            f"TRL {trl} 증빙자료 보강",
            "외부 전문기관 기술검증 의뢰",
            "3개월 내 재평가",
        ]
