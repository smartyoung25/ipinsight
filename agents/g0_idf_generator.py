"""G0-1 발명공개서(IDF) 생성 — 1단계 IP개발 산출물 완성"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

_SECURITY_LEVELS = {
    "public": "공개 가능 — 즉시 출원 또는 공개 발표 가능",
    "internal": "내부 한정 — 출원 전 외부 공개 금지, NDA 필요",
    "confidential": "기밀 — 출원 전 임직원 한정, 기술유출 위험 관리 필요",
    "restricted": "극비 — 별도 보안 승인 절차, 방산·의료 등 규제 분야",
}

_LICENSING_POTENTIAL = {
    "exclusive": "독점 라이선스 — 단일 파트너에 전속 공여, 최고 로열티",
    "non_exclusive": "비독점 라이선스 — 복수 파트너 허용, 광범위 확산",
    "field_of_use": "사용분야 한정 — 산업별·지역별 분리 라이선스",
    "spinoff": "창업(Spinoff) 우선 — 자체 사업화 후 라이선스",
    "cross_license": "크로스 라이선스 — 경쟁사와 IP 상호 공유",
}


class IDFGenerator(BaseAgent):
    stage_id = "G0-IDF"
    stage_name = "발명공개서(IDF) 생성"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          tech_name (str): 기술명
          tech_detail (str): 기술 상세 설명 (작동원리, 핵심 구성요소)
          inventor_info (list of {name, affiliation, contribution_pct}): 발명자 정보
          problem_solved (str): 해결한 기술적 문제
          key_features (list): 핵심 기술적 특징 (청구항 후보)
          prior_art_known (list): 발명자가 인지한 선행기술
          security_classification (str): public/internal/confidential/restricted
          licensing_potential (str): exclusive/non_exclusive/field_of_use/spinoff/cross_license
          disclosure_date (str, optional): 발명공개 기준일 (YYYY-MM-DD)
          related_patents (list, optional): 관련 특허번호
          research_funding (str, optional): 연구비 출처 (정부과제 시 IP 귀속 주의)
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
        score = 0.0
        # 기술 상세 설명 완성도 (25점)
        detail = d.get("tech_detail", "")
        score += 25 if len(detail) >= 200 else 15 if len(detail) >= 100 else 5
        # 발명자 정보 (20점)
        inventors = d.get("inventor_info", [])
        if inventors:
            total_pct = sum(i.get("contribution_pct", 0) for i in inventors)
            score += 20 if total_pct >= 95 else 10
        # 핵심 기술 특징 (25점)
        features = d.get("key_features", [])
        score += min(25, len(features) * 5)
        # 선행기술 인지 (15점)
        score += 15 if d.get("prior_art_known") else 0
        # 보안 분류 + 라이선싱 방향 (15점)
        score += 8 if d.get("security_classification") else 0
        score += 7 if d.get("licensing_potential") else 0
        return round(min(score, 100), 1)

    def _build_output(self, d: dict, score: float) -> dict:
        inventors = d.get("inventor_info", [])
        security = d.get("security_classification", "internal")
        licensing = d.get("licensing_potential", "non_exclusive")

        llm_result = self._llm(
            f"기술명: {d.get('tech_name', '')}\n"
            f"기술 설명: {d.get('tech_detail', '')}\n"
            f"해결 문제: {d.get('problem_solved', '')}\n"
            f"핵심 특징: {d.get('key_features', [])}\n\n"
            "발명공개서(IDF) 초안을 JSON으로 작성:\n"
            '{"executive_summary":"","technical_background":"","invention_description":"",'
            '"novel_aspects":[],"potential_applications":[],"commercialization_notes":""}',
            system="특허 전문가. 발명공개서 초안을 간결하고 명확하게 작성. JSON만 반환."
        )
        try:
            import json
            idf_content = json.loads(llm_result)
        except Exception:
            idf_content = {
                "executive_summary": d.get("tech_detail", "")[:200],
                "novel_aspects": d.get("key_features", []),
                "commercialization_notes": _LICENSING_POTENTIAL.get(licensing, ""),
            }

        # 정부 연구비 IP 귀속 경고
        funding_warning = []
        research_funding = d.get("research_funding", "")
        if research_funding and any(kw in research_funding for kw in ["정부", "국가", "IITP", "NRF", "ETRI", "연구재단"]):
            funding_warning.append("정부 연구비 지원 기술: 기술료 납부 의무 및 기관 귀속 조건 확인 필요")
            funding_warning.append("국유특허 여부 확인: 기술이전진흥법 제11조 적용 가능")

        return {
            "idf_document": {
                "tech_name": d.get("tech_name", ""),
                "disclosure_date": d.get("disclosure_date", "미정"),
                "inventors": [
                    {
                        "name": i.get("name", ""),
                        "affiliation": i.get("affiliation", ""),
                        "contribution_pct": i.get("contribution_pct", 0),
                    }
                    for i in inventors
                ],
                "problem_solved": d.get("problem_solved", ""),
                "key_features": d.get("key_features", []),
                "prior_art_known": d.get("prior_art_known", []),
                "related_patents": d.get("related_patents", []),
                "research_funding": research_funding,
                **idf_content,
            },
            "ip_classification": {
                "security_level": security,
                "security_description": _SECURITY_LEVELS.get(security, ""),
                "licensing_direction": licensing,
                "licensing_description": _LICENSING_POTENTIAL.get(licensing, ""),
            },
            "inventor_compensation_guide": {
                "total_inventors": len(inventors),
                "contribution_verified": sum(i.get("contribution_pct", 0) for i in inventors) >= 95,
                "note": "발명자 기여도 합계는 100%가 되어야 보상 산정 가능 (직무발명보상규정 적용)",
            },
            "funding_warnings": funding_warning,
            "idf_score": score,
        }

    def _next_actions(self, gate: str, d: dict) -> list[str]:
        actions = []
        if gate == "Go":
            actions.append("G1 IP구조화: 청구항 초안 작성 진행")
            actions.append("G1-Portfolio: 특허 포트폴리오 구성 전략 수립")
            actions.append("IDF 기관 내부 승인 후 특허출원 의뢰")
        elif gate == "Hold":
            if not d.get("inventor_info"):
                actions.append("공동발명자 기여도 확인 및 발명자 목록 완성")
            if not d.get("key_features"):
                actions.append("핵심 기술 특징 최소 3개 이상 구체화")
            actions.append("기술 상세 설명 200자 이상으로 보완")
        else:
            actions.append("기술 상세 설명 전면 재작성 후 재제출")
        return actions
