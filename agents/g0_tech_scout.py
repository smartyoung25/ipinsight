"""G0 기술후보 발굴·등록 — WIPO Lab-to-Market '혁신 식별 및 공개' 단계"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult


class TechScout(BaseAgent):
    stage_id = "G0"
    stage_name = "기술후보 발굴·등록"

    # IPC 대분류 → 산업 매핑
    _IPC_INDUSTRY = {
        "A": "생활필수품·농업",
        "B": "처리조작·운수",
        "C": "화학·야금",
        "D": "섬유·지류",
        "E": "고정구조물·건설",
        "F": "기계공학·조명·무기",
        "G": "물리학·컴퓨팅",
        "H": "전기·전자",
    }

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data 예시:
          tech_name, tech_description, owner, field_keywords,
          ipc_codes (list), problem_statement, existing_solutions
        """
        score = self._score(input_data)
        gate = self._gate_from_score(score)
        output_doc = self._build_output(input_data, score)
        next_actions = self._next_actions(gate)

        return StageResult(
            stage=self.stage_id,
            score=score,
            gate=gate,
            output_doc=output_doc,
            next_actions=next_actions,
        )

    def _score(self, d: dict) -> float:
        score = 0.0
        # 기술 설명 명확성 (25점)
        desc = d.get("tech_description", "")
        score += min(25, len(desc) / 20)
        # 문제 정의 명확성 (25점)
        problem = d.get("problem_statement", "")
        score += 25 if len(problem) > 50 else len(problem) / 2
        # IPC 분류 가능성 (20점)
        score += 20 if d.get("ipc_codes") else 5
        # 적용 산업 명확성 (15점)
        score += 15 if d.get("field_keywords") else 5
        # 기존 솔루션 인지 여부 (15점)
        score += 15 if d.get("existing_solutions") else 0
        return round(min(score, 100), 1)

    def _build_output(self, d: dict, score: float) -> dict:
        ipc_codes = d.get("ipc_codes", [])
        industries = []
        for code in ipc_codes:
            section = code[0].upper() if code else ""
            industries.append(self._IPC_INDUSTRY.get(section, "기타"))

        # LLM으로 기술 분류 보강
        llm_analysis = self._llm(
            f"기술명: {d.get('tech_name', '')}\n"
            f"기술설명: {d.get('tech_description', '')}\n"
            f"적용분야: {d.get('field_keywords', '')}\n\n"
            "다음을 JSON으로 반환하라:\n"
            "1. 핵심 기술 구성요소 3가지\n"
            "2. 주요 적용 제품군 3가지\n"
            "3. 차별점 한 문장\n"
            '예: {"components":[], "products":[], "differentiator":""}',
            system="기술사업화 전문가. JSON만 반환."
        )
        try:
            import json
            llm_data = json.loads(llm_analysis)
        except Exception:
            llm_data = {"components": [], "products": [], "differentiator": llm_analysis}

        return {
            "tech_registration_card": {
                "tech_name": d.get("tech_name", ""),
                "owner": d.get("owner", ""),
                "ipc_codes": ipc_codes,
                "industries": list(set(industries)),
                "problem_statement": d.get("problem_statement", ""),
                "existing_solutions": d.get("existing_solutions", ""),
                "core_components": llm_data.get("components", []),
                "applicable_products": llm_data.get("products", []),
                "differentiator": llm_data.get("differentiator", ""),
                "completeness_score": score,
            },
            "tech_classification": {
                "ipc_sections": ipc_codes,
                "industry_mapping": industries,
                "field_keywords": d.get("field_keywords", []),
            }
        }

    def _next_actions(self, gate: str) -> list[str]:
        if gate == "Go":
            return [
                "G1 단계로 진행: IP 구조화 및 선행기술 조사",
                "임시특허(Provisional) 출원 검토 (12개월 우선권 확보)",
                "발명자 보상 규정 확인",
            ]
        if gate == "Hold":
            return [
                "기술 설명서 보완 (문제정의·차별점 명확화)",
                "적용 산업 및 IPC 분류 재검토",
                "4주 내 재평가",
            ]
        return [
            "현 단계 기술사업화 중단",
            "기초 연구 추가 후 재등록 검토",
        ]
