"""Layer 3 — 서비스: SMK(사업화시장키트, Start-up Market Kit) 자동 생성
G0~G5 파이프라인 결과 → 투자자·파트너·고객용 사업화 시장 분석 패키지 자동 생성.
산출물: 경쟁사 비교표·포지셔닝맵·GTM 전략·채널 전략·가격 전략
"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# GTM(Go-to-Market) 전략 유형
_GTM_MOTIONS = {
    "direct_sales":   {"label": "직접 영업",      "best_for": "B2B 고가 솔루션 (ACV > $20K)", "cac_level": "높음"},
    "product_led":    {"label": "제품 주도 성장",  "best_for": "셀프서비스 SaaS",               "cac_level": "낮음"},
    "partner_led":    {"label": "파트너 주도",     "best_for": "규제 산업·공공 시장",           "cac_level": "중간"},
    "channel_reseller":{"label":"리셀러·VAR",     "best_for": "지역 시장 빠른 확산",           "cac_level": "중간"},
    "community_led":  {"label": "커뮤니티 주도",   "best_for": "개발자·전문가 도구",            "cac_level": "낮음"},
}

# 경쟁 포지셔닝 축 (2×2 매트릭스용)
_POSITIONING_AXES = [
    ("가격(저↔고)", "성능(기본↔고성능)"),
    ("범용성(전문↔범용)", "설치 난이도(쉬움↔복잡)"),
    ("국산화율(수입↔국산)", "자동화 수준(수동↔자동)"),
]


class SMKGenerator(BaseAgent):
    stage_id   = "SMK"
    stage_name = "사업화시장키트(SMK) 자동 생성"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          tech_name (str)
          industry_sector (str)
          value_proposition (str): 핵심 가치 제안 한 줄
          tam_usd (float)
          sam_usd (float)
          som_usd (float)
          growth_rate_pct (float)
          revenue_model (str): SaaS/license/hardware/service/marketplace
          price_point_usd (float): 단위 가격 (월 구독료 또는 단가)
          competitors (list[dict]):
            [{"name": str, "strengths": list, "weaknesses": list, "price_usd": float}]
          differentiators (list[str]): 핵심 차별화 3가지
          target_segments (list[str])
          gtm_motion (str): direct_sales/product_led/partner_led/channel_reseller/community_led
          trl (int)
          pilot_customers (list[str])
        """
        rag_ctx = self._rag(f"{input_data.get('tech_name','')} 시장 경쟁 GTM 전략", top_k=3)
        score   = self._score(input_data)
        gate    = self._gate_from_score(score)
        output  = self._build_output(input_data, rag_ctx, score)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output,
            next_actions=self._next_actions(gate, input_data),
        )

    def _score(self, d: dict) -> float:
        score = 0.0
        score += 25 if d.get("value_proposition") else 0
        score += 20 if d.get("tam_usd", 0) > 0 else 0
        score += min(20, len(d.get("competitors", [])) * 7)
        score += min(20, len(d.get("differentiators", [])) * 7)
        score += 15 if d.get("gtm_motion") else 0
        return round(min(score, 100), 1)

    def _build_output(self, d: dict, rag_ctx: str, score: float) -> dict:
        gtm_key  = d.get("gtm_motion", "direct_sales")
        gtm_info = _GTM_MOTIONS.get(gtm_key, _GTM_MOTIONS["direct_sales"])

        # 경쟁사 비교표
        competitor_matrix = []
        for comp in d.get("competitors", []):
            competitor_matrix.append({
                "name":        comp.get("name", ""),
                "strengths":   comp.get("strengths", []),
                "weaknesses":  comp.get("weaknesses", []),
                "price_usd":   comp.get("price_usd", 0),
                "vs_us": {
                    "our_advantage": d.get("differentiators", [])[:2],
                    "their_advantage": comp.get("strengths", [])[:2],
                }
            })

        prompt = (
            f"기술명: {d.get('tech_name','')}\n"
            f"가치 제안: {d.get('value_proposition','')}\n"
            f"TAM: ${d.get('tam_usd',0):,.0f}\n"
            f"차별화: {d.get('differentiators',[])}\n"
            f"GTM: {gtm_info['label']}\n"
            f"경쟁사: {[c.get('name','') for c in d.get('competitors',[])]}\n"
            f"목표 세그먼트: {d.get('target_segments',[])}\n"
            f"\n{rag_ctx}\n\n"
            "SMK 핵심 항목 JSON 출력:\n"
            '{"positioning_statement":"","gtm_plan":[],"channel_strategy":[],"pricing_rationale":"",'
            '"sales_playbook_summary":"","market_entry_risks":[]}'
        )
        llm_text = self._llm(prompt, system="GTM·사업화 전략 전문가. 실행 가능한 SMK 작성. JSON 반환.")
        try:
            import json
            llm_out = json.loads(llm_text)
        except Exception:
            llm_out = {
                "positioning_statement": f"{d.get('tech_name','')}은 {d.get('value_proposition','')}으로 차별화",
                "gtm_plan": ["1개월: ICP 정의", "3개월: 파일럿 3개사", "6개월: 레퍼런스 확보"],
                "channel_strategy": [gtm_info["label"]],
                "pricing_rationale": "가치 기반 가격 책정",
                "sales_playbook_summary": "",
                "market_entry_risks": [],
            }

        return {
            "document_type":   "사업화시장키트 (SMK — Start-up Market Kit)",
            "tech_name":        d.get("tech_name", ""),
            "market_sizing": {
                "tam_usd":       d.get("tam_usd", 0),
                "sam_usd":       d.get("sam_usd", 0),
                "som_usd":       d.get("som_usd", 0),
                "cagr_pct":      d.get("growth_rate_pct", 0),
            },
            "competitive_matrix": competitor_matrix,
            "positioning_axes":   _POSITIONING_AXES[:2],
            "gtm_strategy": {
                "motion":        gtm_key,
                "label":         gtm_info["label"],
                "best_for":      gtm_info["best_for"],
                "cac_level":     gtm_info["cac_level"],
                "plan":          llm_out.get("gtm_plan", []),
            },
            "pricing": {
                "model":         d.get("revenue_model", ""),
                "price_usd":     d.get("price_point_usd", 0),
                "rationale":     llm_out.get("pricing_rationale", ""),
            },
            "channel_strategy":  llm_out.get("channel_strategy", []),
            "sales_playbook":    llm_out.get("sales_playbook_summary", ""),
            "positioning":       llm_out.get("positioning_statement", ""),
            "market_entry_risks":llm_out.get("market_entry_risks", []),
            "smk_score":         score,
        }

    def _next_actions(self, gate: str, d: dict) -> list[str]:
        gtm = _GTM_MOTIONS.get(d.get("gtm_motion",""), {})
        actions = []
        if gate == "Go":
            actions.append(f"SMK 기반 영업 플레이북 작성 — {gtm.get('label','')} 모션 적용")
            actions.append("경쟁사 비교 1페이저 제작 → 영업팀·파트너 배포")
            actions.append("파일럿 고객 레퍼런스 케이스 스터디 작성")
        elif gate == "Hold":
            if not d.get("differentiators"):
                actions.append("차별화 포인트 3가지 이상 정의 필요")
            if not d.get("competitors"):
                actions.append("주요 경쟁사 3개 이상 벤치마킹 후 SMK 갱신")
        else:
            actions.append("가치 제안·목표 시장 재정의 후 SMK 재작성")
        return actions
