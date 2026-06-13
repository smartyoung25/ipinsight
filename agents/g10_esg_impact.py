"""G10-ESG: ESG·사회임팩트 평가 — SDG 매핑 + 임팩트 투자자용 정량화
UN SDG 17개 목표 × E·S·G 3축 점수 + 사회적 가치 화폐화.
"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# UN SDG 17개 목표 (기술사업화 연관 중심)
_SDG_MAP = {
    1:  {"name": "빈곤 종식",          "tech_keywords": ["저소득","접근성","포용"]},
    2:  {"name": "기아 종식",           "tech_keywords": ["농업","식품","스마트팜","수확"]},
    3:  {"name": "건강·웰빙",           "tech_keywords": ["의료","헬스","진단","치료","예방"]},
    4:  {"name": "교육",               "tech_keywords": ["교육","학습","EdTech","훈련"]},
    6:  {"name": "깨끗한 물",           "tech_keywords": ["수처리","관개","정수","절수"]},
    7:  {"name": "청정에너지",          "tech_keywords": ["태양광","풍력","배터리","에너지저장","그린수소"]},
    8:  {"name": "양질의 일자리·경제성장","tech_keywords": ["고용","일자리","생산성","스타트업"]},
    9:  {"name": "산업·혁신·인프라",    "tech_keywords": ["제조","자동화","AI","IoT","스마트"]},
    11: {"name": "지속가능한 도시",     "tech_keywords": ["스마트시티","모빌리티","건물","도시"]},
    12: {"name": "지속가능한 소비·생산", "tech_keywords": ["순환경제","재활용","폐기물","자원효율"]},
    13: {"name": "기후행동",            "tech_keywords": ["탄소","온실가스","탄소중립","기후","넷제로"]},
    14: {"name": "해양 생태계",         "tech_keywords": ["해양","수산","플라스틱","오염"]},
    15: {"name": "육상 생태계",         "tech_keywords": ["산림","생물다양성","토지"]},
    17: {"name": "글로벌 파트너십",     "tech_keywords": ["국제협력","ODA","기술이전"]},
}

# ESG 평가 차원
_ESG_DIMENSIONS = {
    "E": {
        "label": "환경(Environmental)",
        "factors": {
            "carbon_reduction":   {"weight": 30, "desc": "탄소 감축 기여"},
            "resource_efficiency":{"weight": 25, "desc": "자원·에너지 효율"},
            "pollution_prevention":{"weight": 25, "desc": "오염·유해물질 저감"},
            "biodiversity":       {"weight": 20, "desc": "생태계·생물다양성"},
        }
    },
    "S": {
        "label": "사회(Social)",
        "factors": {
            "job_creation":       {"weight": 30, "desc": "고용 창출·유지"},
            "accessibility":      {"weight": 25, "desc": "취약계층 접근성"},
            "health_safety":      {"weight": 25, "desc": "안전·보건 개선"},
            "community_impact":   {"weight": 20, "desc": "지역사회 기여"},
        }
    },
    "G": {
        "label": "거버넌스(Governance)",
        "factors": {
            "transparency":       {"weight": 35, "desc": "정보 투명성"},
            "board_diversity":    {"weight": 25, "desc": "이사회 다양성"},
            "ethics_compliance":  {"weight": 25, "desc": "윤리·컴플라이언스"},
            "ip_governance":      {"weight": 15, "desc": "IP·데이터 거버넌스"},
        }
    },
}


class ESGImpactAssessor(BaseAgent):
    stage_id   = "G10-ESG"
    stage_name = "ESG·사회임팩트 평가"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          tech_name (str)
          tech_description (str): 기술 설명 (SDG 자동 매핑에 사용)
          industry_sector (str)

          # E 환경
          carbon_reduction_tco2_per_year (float): 연간 탄소 감축량 (tCO₂)
          energy_efficiency_improvement_pct (float): 에너지 효율 개선율 %
          uses_hazardous_materials (bool): 유해물질 사용 여부
          biodiversity_impact (str): positive/neutral/negative

          # S 사회
          jobs_created (int): 직접 고용 창출 수
          target_vulnerable_groups (bool): 취약계층(농촌·장애인·저소득) 대상
          health_safety_improvement (str): 개선 설명 (없으면 "")
          community_programs (bool): 지역사회 프로그램 운영

          # G 거버넌스
          publishes_impact_report (bool): 임팩트 보고서 공개
          board_female_pct (float): 여성 이사 비율 %
          has_ethics_policy (bool): 윤리 정책 수립
          data_privacy_certified (bool): 개인정보 인증(ISMS·ISO 27001 등)

          # 정량화
          beneficiaries_count (int): 수혜자 수
          sdvr_usd (float, optional): 사회적 가치 화폐 추정 (SROI 기반 사전 계산값)
        """
        sdg_matches = self._match_sdgs(input_data)
        esg_scores  = self._calc_esg(input_data)
        score       = self._score(esg_scores)
        gate        = self._gate_from_score(score)
        output      = self._build_output(input_data, sdg_matches, esg_scores, score)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output,
            next_actions=self._next_actions(gate, esg_scores),
        )

    def _match_sdgs(self, d: dict) -> list[dict]:
        text = (d.get("tech_description","") + " " + d.get("industry_sector","")).lower()
        matches = []
        for sdg_num, sdg in _SDG_MAP.items():
            hit = sum(1 for kw in sdg["tech_keywords"] if kw in text)
            if hit > 0:
                matches.append({
                    "sdg_num":    sdg_num,
                    "sdg_name":   sdg["name"],
                    "relevance":  "주요" if hit >= 2 else "연관",
                    "keyword_hits": hit,
                })
        matches.sort(key=lambda x: -x["keyword_hits"])
        return matches[:5]  # Top 5

    def _calc_esg(self, d: dict) -> dict:
        scores = {}

        # E 점수
        e = 0.0
        co2 = d.get("carbon_reduction_tco2_per_year", 0)
        e += min(30, co2 / 100 * 10) if co2 > 0 else 0
        e += min(25, d.get("energy_efficiency_improvement_pct", 0) * 1.5)
        e += 0 if d.get("uses_hazardous_materials") else 25
        bio = d.get("biodiversity_impact", "neutral")
        e += 20 if bio == "positive" else 10 if bio == "neutral" else 0
        scores["E"] = round(min(e, 100))

        # S 점수
        s = 0.0
        jobs = d.get("jobs_created", 0)
        s += min(30, jobs * 2)
        s += 25 if d.get("target_vulnerable_groups") else 0
        s += 25 if d.get("health_safety_improvement") else 0
        s += 20 if d.get("community_programs") else 0
        scores["S"] = round(min(s, 100))

        # G 점수
        g = 0.0
        g += 35 if d.get("publishes_impact_report") else 0
        female = d.get("board_female_pct", 0)
        g += min(25, female * 0.8)
        g += 25 if d.get("has_ethics_policy") else 0
        g += 15 if d.get("data_privacy_certified") else 0
        scores["G"] = round(min(g, 100))

        return scores

    def _score(self, esg: dict) -> float:
        # E·S·G 가중 평균 (E 40% · S 40% · G 20%)
        return round(esg.get("E",0)*0.4 + esg.get("S",0)*0.4 + esg.get("G",0)*0.2, 1)

    def _build_output(self, d: dict, sdgs: list, esg: dict, score: float) -> dict:
        # SROI (Social Return on Investment) 간이 추정
        beneficiaries = d.get("beneficiaries_count", 0)
        sdvr = d.get("sdvr_usd", 0) or (beneficiaries * 500)  # 1인당 $500 기본값

        llm_text = self._llm(
            f"기술: {d.get('tech_name','')}\n"
            f"ESG 점수: E={esg['E']} S={esg['S']} G={esg['G']}\n"
            f"SDG 매핑: {[s['sdg_name'] for s in sdgs]}\n"
            f"수혜자: {beneficiaries}명\n"
            f"탄소감축: {d.get('carbon_reduction_tco2_per_year',0)} tCO₂/년\n"
            f"고용창출: {d.get('jobs_created',0)}명\n\n"
            "임팩트 투자자 대상 ESG 강점 3가지와 개선 우선순위 2가지를 JSON으로:\n"
            '{"strengths":[],"improvements":[],"impact_narrative":""}',
            system="임팩트 투자·ESG 전문가. 측정 가능한 임팩트 중심으로 서술. JSON 반환."
        )
        try:
            import json
            llm_out = json.loads(llm_text)
        except Exception:
            llm_out = {"strengths": [], "improvements": [], "impact_narrative": ""}

        return {
            "sdg_alignment": {
                "matched_sdgs": sdgs,
                "primary_sdg":  sdgs[0]["sdg_name"] if sdgs else "미매핑",
                "sdg_count":    len(sdgs),
            },
            "esg_scorecard": {
                "E_environmental": esg["E"],
                "S_social":        esg["S"],
                "G_governance":    esg["G"],
                "composite_score": score,
                "rating": (
                    "임팩트 리더 (A)" if score >= 80 else
                    "ESG 우수 (B+)" if score >= 60 else
                    "ESG 기초 (B)"  if score >= 40 else
                    "개선 필요 (C)"
                ),
            },
            "social_value_quantification": {
                "beneficiaries":    beneficiaries,
                "carbon_tco2_yr":   d.get("carbon_reduction_tco2_per_year", 0),
                "jobs_created":     d.get("jobs_created", 0),
                "estimated_sroi_usd": sdvr,
                "sroi_ratio":       round(sdvr / max(1, d.get("funding_ask_usd", sdvr/3)), 2),
            },
            "impact_narrative":  llm_out.get("impact_narrative", ""),
            "esg_strengths":     llm_out.get("strengths", []),
            "esg_improvements":  llm_out.get("improvements", []),
            "investor_fit": {
                "impact_vc":     score >= 60,
                "esg_fund":      esg["E"] >= 50 or esg["S"] >= 50,
                "government_nf": len(sdgs) >= 2,
                "un_sdg_aligned": len(sdgs) >= 1,
            },
        }

    def _next_actions(self, gate: str, esg: dict) -> list[str]:
        actions = []
        if gate == "Go":
            actions.append("임팩트 투자자 IR 자료에 SDG 배지·ESG 점수 추가")
            actions.append("GRI·SASB 기준 임팩트 보고서 작성 (정부·공공 입찰 우대)")
        elif gate == "Hold":
            if esg.get("G", 0) < 40:
                actions.append("거버넌스 강화: 임팩트 보고서 공개 + 윤리 정책 수립")
            if esg.get("E", 0) < 40 and esg.get("S", 0) < 40:
                actions.append("E 또는 S 중 1개 핵심 임팩트 지표 정량화 후 재평가")
        else:
            actions.append("임팩트 측정 지표 설정 필요 — IRIS+·B Impact Assessment 활용")
        return actions
