"""G3-Eco: 생태계 파트너 매칭 — 기업·대학·연구소·VC·AC·정부 6개 카테고리
기술 도메인·TRL·사업화 목표 기반 파트너 후보 자동 추천.
"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# 파트너 카테고리 × 역할 매트릭스
_PARTNER_CATEGORIES = {
    "corporate_partner": {
        "label": "기업 파트너 (Venture Client·전략적 파트너)",
        "value": ["시장 접근","PoC 기회","공동개발(JDA)","기술이전 수요"],
        "fit_criteria": {"trl_min": 5, "commercialization_types": ["startup","spinout","transfer"]},
        "engagement_models": ["Venture Client 계약","공동연구 MOU","라이선스 옵션","JDA"],
    },
    "university_lab": {
        "label": "대학·연구실 협력",
        "value": ["기초연구 보완","우수 인재 채용","공동특허","장비 공유"],
        "fit_criteria": {"trl_min": 1, "commercialization_types": ["spinout","startup","transfer"]},
        "engagement_models": ["공동연구협약","기술이전 MOU","겸임교수","인턴십 프로그램"],
    },
    "research_institute": {
        "label": "정부출연연구소 (ETRI·KIST·KRICT 등)",
        "value": ["TRL 가속","CRADA","국가 R&D 공동수행","실증 인프라"],
        "fit_criteria": {"trl_min": 2, "commercialization_types": ["all"]},
        "engagement_models": ["CRADA","공동연구","기술사용 허가","TLO 협력"],
    },
    "vc_accelerator": {
        "label": "VC·액셀러레이터",
        "value": ["자금조달","멘토링","네트워크","후속 투자"],
        "fit_criteria": {"trl_min": 4, "commercialization_types": ["startup","spinout"]},
        "engagement_models": ["Pre-Seed·Seed 투자","AC 프로그램","TIPS","CVC 파트너십"],
    },
    "government_agency": {
        "label": "정부·공공기관",
        "value": ["비희석 R&D 자금","규제 샌드박스","실증 특구","공공조달"],
        "fit_criteria": {"trl_min": 1, "commercialization_types": ["all"]},
        "engagement_models": ["R&D 과제","규제특례","스마트시티 실증","조달청 혁신제품"],
    },
    "global_partner": {
        "label": "글로벌 파트너 (해외 기업·기관)",
        "value": ["해외 시장 진입","글로벌 라이선스","현지 규제 지원","공동 마케팅"],
        "fit_criteria": {"trl_min": 6, "commercialization_types": ["all"]},
        "engagement_models": ["MOU·LOI","현지 JV","글로벌 라이선스","OEM·ODM"],
    },
}

# 도메인별 주요 파트너 풀 (예시 DB)
_DOMAIN_PARTNERS = {
    "AgriTech":       ["LG CNS","KT","농진청","농업기술실용화재단","카길·Bayer Crop","BASF Venture"],
    "HealthTech":     ["삼성메디슨","GC녹십자","한국보건산업진흥원","식약처 규제샌드박스","Philips","Siemens Healthineers"],
    "Manufacturing":  ["현대자동차","포스코DX","한국기계연구원","KIMS","Bosch","Siemens"],
    "AI_Software":    ["NAVER","카카오","SKT","ETRI","AWS Activate","Microsoft for Startups"],
    "Energy_CleanTech":["한국에너지기술연구원","LS일렉트릭","두산에너빌리티","KEPCO","Siemens Energy","GE Vernova"],
    "BioTech":        ["셀트리온","종근당","한국화학연구원","KBIO","Novo Holdings","Johnson & Johnson Innovation"],
    "SpaceTech":      ["한화시스템","KAI","항우연","방사청","SpaceX 벤더","Airbus Ventures"],
    "SmartFarm":      ["그린플러스","팜에이트","농업기술원","KAASA","Priva","Ridder"],
}


class EcosystemMatcher(BaseAgent):
    stage_id   = "G3-Eco"
    stage_name = "생태계 파트너 매칭"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          tech_name (str)
          industry_sector (str): AgriTech/HealthTech/Manufacturing/AI_Software/Energy_CleanTech/BioTech/SmartFarm 등
          trl (int)
          commercialization_type (str): startup/spinout/transfer/licensing
          partnership_goals (list[str]): ["자금조달","시장진입","공동개발","규제지원","인재채용"]
          target_countries (list[str])
          budget_for_partnership_usd (float, optional)
          existing_partners (list[str], optional): 기존 파트너 목록
          exclude_competitors (list[str], optional)
        """
        score    = self._score(input_data)
        gate     = self._gate_from_score(score)
        matches  = self._match_partners(input_data)
        output   = self._build_output(input_data, matches, score)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output,
            next_actions=self._next_actions(gate, matches),
        )

    def _match_partners(self, d: dict) -> list[dict]:
        trl    = d.get("trl", 1)
        ctype  = d.get("commercialization_type", "startup")
        goals  = set(d.get("partnership_goals", []))
        sector = d.get("industry_sector", "")
        domain_pool = _DOMAIN_PARTNERS.get(sector, [])
        existing = set(d.get("existing_partners", []))
        exclude  = set(d.get("exclude_competitors", []))

        matches = []
        for cat_key, cat in _PARTNER_CATEGORIES.items():
            fit = cat["fit_criteria"]
            if trl < fit["trl_min"]:
                continue
            if "all" not in fit["commercialization_types"] and ctype not in fit["commercialization_types"]:
                continue

            # 목표 일치도 점수
            goal_match = sum(1 for v in cat["value"] if any(g in v for g in goals))
            priority   = "1순위" if goal_match >= 2 else "2순위" if goal_match >= 1 else "3순위"

            # 도메인별 후보 기업
            candidates = [p for p in domain_pool[:3] if p not in existing and p not in exclude]

            matches.append({
                "category":          cat_key,
                "category_label":    cat["label"],
                "value_proposition": cat["value"],
                "engagement_models": cat["engagement_models"],
                "priority":          priority,
                "goal_match_score":  goal_match,
                "candidates":        candidates,
                "trl_required":      fit["trl_min"],
            })

        matches.sort(key=lambda x: (-x["goal_match_score"], x["trl_required"]))
        return matches

    def _score(self, d: dict) -> float:
        score = 0.0
        trl   = d.get("trl", 1)
        goals = d.get("partnership_goals", [])
        # TRL 기반 파트너 접근성 (30점)
        score += min(30, (trl / 9) * 30)
        # 파트너십 목표 명확성 (25점)
        score += min(25, len(goals) * 8)
        # 산업 섹터 매핑 가능 여부 (25점)
        score += 25 if d.get("industry_sector") in _DOMAIN_PARTNERS else 10
        # 기존 파트너 보유 (20점)
        score += min(20, len(d.get("existing_partners", [])) * 7)
        return round(min(score, 100), 1)

    def _build_output(self, d: dict, matches: list, score: float) -> dict:
        top3 = [m for m in matches if m["priority"] == "1순위"][:3]

        llm_text = self._llm(
            f"기술: {d.get('tech_name','')}\n"
            f"산업: {d.get('industry_sector','')}\n"
            f"TRL: {d.get('trl',1)}\n"
            f"파트너십 목표: {d.get('partnership_goals',[])}\n"
            f"추천 카테고리: {[m['category_label'] for m in top3]}\n\n"
            "파트너십 접근 전략 3가지와 첫 접촉 메시지 초안을 JSON으로:\n"
            '{"approach_strategy":[],"first_contact_template":""}',
            system="기술사업화 파트너십 전문가. 실행 가능한 파트너링 전략. JSON 반환."
        )
        try:
            import json
            llm_out = json.loads(llm_text)
        except Exception:
            llm_out = {"approach_strategy": [], "first_contact_template": ""}

        return {
            "ecosystem_map": {
                "total_categories_matched": len(matches),
                "priority_1_count":         len([m for m in matches if m["priority"] == "1순위"]),
                "all_matches":              matches,
            },
            "top_recommendations":   top3,
            "outreach_strategy": {
                "approach_tips":        llm_out.get("approach_strategy", []),
                "first_contact_draft":  llm_out.get("first_contact_template", ""),
            },
            "domain_partner_pool":   _DOMAIN_PARTNERS.get(d.get("industry_sector",""), []),
            "ecosystem_score":       score,
        }

    def _next_actions(self, gate: str, matches: list) -> list[str]:
        actions = []
        top = next((m for m in matches if m["priority"] == "1순위"), None)
        if gate == "Go" and top:
            actions.append(f"즉시 착수: {top['category_label']} — {top['engagement_models'][0]}")
            actions.append(f"후보 기업 접촉: {', '.join(top['candidates'][:2])}")
            actions.append("파트너십 MOU 초안 준비 (G9 거래구조와 연계)")
        elif gate == "Hold":
            actions.append("파트너십 목표 구체화 (최소 2개 이상 설정)")
            actions.append("TRL 향상 후 기업 파트너 접근 가능")
        else:
            actions.append("TRL 3 이상 달성 후 파트너 매칭 재시도")
        return actions
