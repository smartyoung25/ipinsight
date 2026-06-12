"""G9 거래·투자·사업화 방식 결정 — TLO 라이선싱·SBIR·EIC·FLC/CRADA 투자연계"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# FLC Federal Lab Consortium (미국 국립연구소 기술이전 표준절차):
# - CRADA (Cooperative R&D Agreement): 국립연구소 + 기업 공동 R&D
# - License Agreement: 연구소 IP 독점/비독점 라이선스
# - Work For Others (WFO): 기업이 연구소에 용역 의뢰
_FLC_CRADA_OPTIONS = [
    {"type": "CRADA", "description": "국립연구소와 공동 R&D 협약, 비용 분담·공동 IP", "timeline_months": 12},
    {"type": "License", "description": "연구소 보유 IP 독점/비독점 라이선스 취득", "timeline_months": 6},
    {"type": "WFO", "description": "기업 자금으로 연구소에 특화 R&D 의뢰", "timeline_months": 9},
]


class DealStructurer(BaseAgent):
    stage_id = "G9"
    stage_name = "거래·투자·사업화 방식 결정"

    _DEAL_TYPES = {
        "license": {
            "name": "라이선싱",
            "timeline_months": 6,
            "capital_required": "낮음",
            "control": "낮음",
            "upside": "중간",
            "best_for": "IP 권리성 강하고 직접 사업화 역량이 약한 경우",
        },
        "transfer": {
            "name": "기술양도",
            "timeline_months": 3,
            "capital_required": "없음",
            "control": "없음",
            "upside": "일시 수익",
            "best_for": "유지관리보다 일괄 수익을 선호하는 경우",
        },
        "joint_dev": {
            "name": "공동개발(JDA)",
            "timeline_months": 12,
            "capital_required": "중간 (분담)",
            "control": "공동",
            "upside": "높음",
            "best_for": "기술 유망하나 실증·제품화 파트너 필요 시",
        },
        "spinoff": {
            "name": "창업·스핀오프",
            "timeline_months": 24,
            "capital_required": "높음 ($2~5M 시드)",
            "control": "높음",
            "upside": "매우 높음 (Exit 시)",
            "best_for": "기술팀과 시장기회가 모두 명확한 경우",
        },
        "jv": {
            "name": "합작투자(JV)",
            "timeline_months": 18,
            "capital_required": "높음 (공동출자)",
            "control": "공동",
            "upside": "높음",
            "best_for": "해외진출·대형설비·장기 공동투자 필요 시",
        },
        "public_procurement": {
            "name": "공공조달·실증",
            "timeline_months": 9,
            "capital_required": "낮음",
            "control": "낮음",
            "upside": "중간 (시장 레퍼런스)",
            "best_for": "공공문제 해결형 또는 인프라 기술",
        },
    }

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data: tech_name, trl, mrl, arl, ip_strength_score,
                    valuation_usd, team_commercialization_capability (1-5),
                    preferred_deal_type, potential_partners (list),
                    target_countries (list), negotiation_terms
        """
        recommended = self._recommend_deal(input_data)
        score = self._score(input_data)
        gate = self._gate_from_score(score)
        output_doc = self._build_output(input_data, recommended, score)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output_doc,
            next_actions=self._next_actions(gate, recommended),
        )

    def _recommend_deal(self, d: dict) -> str:
        ip_score = d.get("ip_strength_score", 50)
        team_cap = d.get("team_commercialization_capability", 3)
        trl = d.get("trl", 5)
        val = d.get("valuation_usd", 0)

        if team_cap >= 4 and trl >= 7 and val >= 5_000_000:
            return "spinoff"
        if ip_score >= 70 and team_cap <= 3:
            return "license"
        if trl < 6:
            return "joint_dev"
        if "공공" in d.get("tech_name", "") or "인프라" in d.get("tech_name", ""):
            return "public_procurement"
        return "license"

    def _score(self, d: dict) -> float:
        score = 0.0
        score += 25 if d.get("potential_partners") else 0
        score += 20 if d.get("valuation_usd", 0) > 0 else 0
        score += 20 if d.get("target_countries") else 0
        score += 20 if d.get("ip_strength_score", 0) >= 60 else 10
        score += 15 if d.get("negotiation_terms") else 0
        return round(min(score, 100), 1)

    def _build_output(self, d: dict, recommended: str, score: float) -> dict:
        deal_info = self._DEAL_TYPES.get(recommended, {})
        royalty_kb = self._load_knowledge("royalty_benchmarks.json")
        country_kb = self._load_knowledge("country_programs.json")

        # 국가별 지원 프로그램 추천
        target_countries = d.get("target_countries", [])
        funding_options = []
        for prog in country_kb.get("programs", []):
            if prog.get("country") in target_countries or not target_countries:
                if "G9" in prog.get("apply_stage", []):
                    funding_options.append({
                        "program": prog["name"],
                        "country": prog["country"],
                        "notes": prog.get("notes", ""),
                    })

        # 라이선스 조건 설계
        sector = d.get("industry_sector", "")
        royalty_bench = next(
            (i for i in royalty_kb.get("industries", []) if sector.lower() in i.get("sector", "").lower()),
            {"royalty_rate_pct": {"typical": 4}}
        )

        llm_result = self._llm(
            f"사업화 방식: {recommended}\n"
            f"잠재 파트너: {d.get('potential_partners', [])}\n"
            f"목표 국가: {target_countries}\n"
            f"기술가치: ${d.get('valuation_usd', 0):,.0f}\n\n"
            "협상 전략과 핵심 조건을 JSON으로:\n"
            '{"negotiation_strategy":"","key_terms":[],'
            '"walk_away_conditions":[],"partner_due_diligence":[]}',
            system="기술거래 협상 전문가. JSON만 반환."
        )
        try:
            import json
            negotiation = json.loads(llm_result)
        except Exception:
            negotiation = {"negotiation_strategy": llm_result}

        return {
            "deal_type_recommendation": {
                "recommended": recommended,
                "deal_info": deal_info,
                "rationale": deal_info.get("best_for", ""),
                "all_options": {k: v["name"] for k, v in self._DEAL_TYPES.items()},
            },
            "licensing_strategy": {
                "royalty_rate_benchmark_pct": royalty_bench.get("royalty_rate_pct", {}),
                "deal_structure_options": royalty_kb.get("deal_structures", {}),
                "suggested_upfront_usd": royalty_bench.get("upfront_fee_usd", {}).get("typical", 0),
                "license_type": royalty_bench.get("license_type", "비독점"),
            },
            "investment_strategy": {
                "valuation_usd": d.get("valuation_usd", 0),
                "target_countries": target_countries,
                "funding_options": funding_options[:5],
            },
            "negotiation_guide": negotiation,
            "partner_shortlist": d.get("potential_partners", []),
            "deal_score": score,
            "flc_crada_options": _FLC_CRADA_OPTIONS if "국립연구소" in str(d.get("potential_partners", [])) or d.get("use_national_lab") else [],
        }

    def _next_actions(self, gate: str, deal_type: str) -> list[str]:
        deal_name = self._DEAL_TYPES.get(deal_type, {}).get("name", "")
        if gate == "Go":
            return [
                f"{deal_name} 방식으로 파트너 최종 협상 진행",
                "법무팀 검토: 계약서 초안 작성",
                "G10 성과관리 시스템 구축 준비",
            ]
        if gate == "Hold":
            return [
                "잠재 파트너 추가 발굴 (최소 5개사 롱리스트)",
                "기술가치 평가 업데이트 (G6 재실시)",
                "협상 조건 조정",
            ]
        return [
            "거래 가능성 낮음 — 사업화 방식 근본 재검토",
            "공공기술 이전 또는 정부 R&D 과제 참여 대안 검토",
        ]
