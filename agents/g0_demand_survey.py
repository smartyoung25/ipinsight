"""Layer 3 — 서비스: 수요조사서(Demand Survey) 자동 생성
기술 정보 + RAG 지식베이스 → 표준 수요조사서 양식 자동 생성.
산출물: 수요처 현황, 시장 수요, 도입 장벽, 잠재 고객 리스트, 도입 우선순위
"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# 산업별 수요처 유형 (수요조사서 표준 분류)
_DEMAND_SEGMENTS = {
    "AgriTech":    ["온실 농가", "영농조합법인", "스마트팜 기업", "농협·지자체", "해외 농업 법인"],
    "HealthTech":  ["종합병원", "의원·클리닉", "바이오 제약사", "의료기기 유통사", "보험사"],
    "Manufacturing":["대기업 제조사", "중견 제조사", "설비 유지보수 기업", "EPC 업체", "협력 공급사"],
    "AI_Software": ["IT 기업", "금융기관", "공공기관", "스타트업", "SaaS 재판매사(VAR)"],
    "Energy_CleanTech":["전력 공기업", "산업 에너지 다소비 기업", "지자체 에너지공단", "신재생 시공사"],
    "BioTech":     ["대형 제약사", "CRO·CMO", "병원 임상센터", "바이오 스타트업", "정부 연구기관"],
    "default":     ["대기업", "중소기업", "스타트업", "공공기관", "연구소"],
}

# 도입 장벽 유형 (수요조사서 표준 항목)
_ADOPTION_BARRIERS = {
    "cost":       "초기 도입 비용 부담",
    "integration":"기존 시스템 연동 복잡성",
    "regulation": "규제·인증 불확실성",
    "trust":      "기술 신뢰성 미검증",
    "skill":      "운용 인력 역량 부족",
    "roi":        "투자 회수 시점 불명확",
    "vendor_lock":"특정 벤더 종속 우려",
    "data":       "데이터 보안·프라이버시",
}


class DemandSurveyGenerator(BaseAgent):
    stage_id   = "G0-DS"
    stage_name = "수요조사서 자동 생성"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          tech_name (str)
          tech_description (str)
          industry_sector (str)
          trl (int)
          target_customer_types (list[str], optional)
          known_barriers (list[str], optional): cost/integration/regulation/trust/skill/roi
          interview_count (int, optional): 수행된 고객 인터뷰 수 (0이면 추정)
          pilot_customers (list[str], optional): LoI·파일럿 고객 목록
          geographic_focus (list[str], optional): 목표 지역 (KOR/USA/EU 등)
        """
        rag_ctx  = self._rag(input_data.get("tech_name","") + " " + input_data.get("tech_description",""), top_k=4, source_filter="market")
        score    = self._score(input_data)
        gate     = self._gate_from_score(score)
        output   = self._build_output(input_data, rag_ctx, score)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output,
            next_actions=self._next_actions(gate, input_data),
        )

    def _score(self, d: dict) -> float:
        score = 0.0
        score += 30 if d.get("tech_description") else 0
        score += 20 if d.get("industry_sector") else 0
        score += min(20, d.get("interview_count", 0) * 4)
        score += min(20, len(d.get("pilot_customers", [])) * 7)
        score += 10 if d.get("known_barriers") else 0
        return round(min(score, 100), 1)

    def _build_output(self, d: dict, rag_ctx: str, score: float) -> dict:
        sector   = d.get("industry_sector", "default")
        segments = _DEMAND_SEGMENTS.get(sector, _DEMAND_SEGMENTS["default"])
        barriers = {k: _ADOPTION_BARRIERS[k] for k in d.get("known_barriers", list(_ADOPTION_BARRIERS)[:3]) if k in _ADOPTION_BARRIERS}

        prompt = (
            f"기술명: {d.get('tech_name','')}\n"
            f"기술 설명: {d.get('tech_description','')}\n"
            f"TRL: {d.get('trl', 1)}\n"
            f"목표 산업: {sector}\n"
            f"수요 세그먼트 후보: {segments}\n"
            f"파일럿 고객: {d.get('pilot_customers',[])}\n"
            f"인터뷰 수: {d.get('interview_count',0)}건\n\n"
            f"{rag_ctx}\n\n"
            "표준 수요조사서 항목을 JSON으로 작성:\n"
            '{"executive_summary":"","demand_segments":[{"name":"","size_estimate":"","pain_level":1,"fit_score":1,"key_contacts":[]}],'
            '"value_proposition":"","adoption_barriers":[],"pilot_roadmap":[],"demand_score":0}'
        )
        llm_text = self._llm(prompt, system="기술사업화 수요조사 전문가. 표준 수요조사서 양식으로 JSON 출력.")
        try:
            import json
            llm_out = json.loads(llm_text)
        except Exception:
            llm_out = {
                "executive_summary": f"{d.get('tech_name','')} 기술의 수요 분석 결과.",
                "demand_segments": [{"name": s, "size_estimate": "미정", "pain_level": 3, "fit_score": 3, "key_contacts": []} for s in segments[:3]],
                "value_proposition": "",
                "adoption_barriers": list(barriers.values()),
                "pilot_roadmap": ["1단계: 파일럿 고객 3개사 선정", "2단계: 6개월 PoC", "3단계: 확산"],
                "demand_score": 50,
            }

        return {
            "document_type":     "수요조사서 (Demand Survey Report)",
            "tech_name":          d.get("tech_name", ""),
            "survey_scope": {
                "industry_sector":   sector,
                "demand_segments":   segments,
                "geographic_focus":  d.get("geographic_focus", ["KOR"]),
                "interview_count":   d.get("interview_count", 0),
                "pilot_customers":   d.get("pilot_customers", []),
            },
            "adoption_barriers": {k: v for k, v in barriers.items()},
            "llm_analysis":      llm_out,
            "readiness_score":   score,
        }

    def _next_actions(self, gate: str, d: dict) -> list[str]:
        actions = []
        if gate == "Go":
            actions.append("수요조사서 기반 SMK(사업화시장키트) 자동 생성 진행")
            actions.append(f"파일럿 고객 {len(d.get('pilot_customers',[]))}개사 → 정식 LoI 체결 추진")
        elif gate == "Hold":
            cnt = d.get("interview_count", 0)
            if cnt < 5:
                actions.append(f"고객 인터뷰 {5 - cnt}건 추가 수행 후 재평가")
            actions.append("파일럿 고객 최소 1개사 확보 후 수요조사서 갱신")
        else:
            actions.append("기술 설명·목표 고객 구체화 후 수요조사서 재작성")
        return actions
