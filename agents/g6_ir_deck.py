"""G6-IR: IR Deck 자동 생성 — 투자자 유형별 12슬라이드 구조 + 피치 스크립트
VC·CVC·Angel·정부 4개 유형별 강조점 차별화.
"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

_INVESTOR_TYPES = {
    "vc":        {"label": "벤처캐피탈(VC)", "focus": ["시장규모","성장속도","팀","엑시트경로"], "metric": "ARR·MoM성장률"},
    "cvc":       {"label": "기업형VC(CVC)", "focus": ["전략적시너지","기술우위","파트너십가능성"], "metric": "기술성숙도·IP강도"},
    "angel":     {"label": "엔젤투자자",    "focus": ["창업팀역량","문제해결명확성","시장진입속도"], "metric": "Traction·CAC"},
    "government":{"label": "정부·공공펀드", "focus": ["사회임팩트","고용창출","기술국산화·수출"], "metric": "사회가치·고용지표"},
    "strategic": {"label": "전략적투자자",  "focus": ["기술보완성","M&A시너지","시장접근성"],    "metric": "특허포트폴리오·TRL"},
}

# 12슬라이드 표준 구조 (Sequoia·YC 벤치마크)
_SLIDE_STRUCTURE = [
    {"num": 1,  "title": "커버 / 엘리베이터 피치",    "purpose": "15초 내 핵심 가치 전달",                "key_elements": ["회사명","한줄설명","핵심지표","연락처"]},
    {"num": 2,  "title": "문제 정의",                  "purpose": "고객 고통(Pain)을 공감시킴",             "key_elements": ["현재 방식의 한계","비용·시간 낭비 수치","감정적 공감 포인트"]},
    {"num": 3,  "title": "솔루션",                    "purpose": "차별화된 해결책 제시",                   "key_elements": ["핵심 기술·제품","기존 대비 10배 개선","작동 원리 시각화"]},
    {"num": 4,  "title": "시장 규모 (TAM·SAM·SOM)",    "purpose": "충분히 큰 기회 증명",                   "key_elements": ["TAM·SAM·SOM 수치","시장성장률(CAGR)","출처 명시"]},
    {"num": 5,  "title": "제품·기술",                  "purpose": "기술 우위와 IP 방어막 시각화",           "key_elements": ["핵심 기술 스택","특허 현황","TRL 단계","데모/스크린샷"]},
    {"num": 6,  "title": "비즈니스 모델",               "purpose": "수익화 경로와 단위경제성",               "key_elements": ["수익모델","가격체계","LTV/CAC","마진구조"]},
    {"num": 7,  "title": "Traction / 견인력",          "purpose": "실행 증거로 리스크 해소",                "key_elements": ["매출·고객 수 추이","LoI·계약","주요 파트너","성장률MoM"]},
    {"num": 8,  "title": "경쟁 분석",                  "purpose": "포지셔닝과 해자(moat) 명확화",          "key_elements": ["2×2 경쟁 매트릭스","핵심 차별화 3가지","방어 장벽"]},
    {"num": 9,  "title": "팀",                         "purpose": "실행 역량 신뢰 형성",                   "key_elements": ["핵심 멤버 경력","도메인 전문성","자문단·투자자"]},
    {"num": 10, "title": "재무 계획 (3년)",             "purpose": "투자 수익성과 현실성",                  "key_elements": ["매출 예측","비용 구조","손익분기 시점","자금 소진 계획"]},
    {"num": 11, "title": "투자 요청 (The Ask)",         "purpose": "명확한 투자 조건 제시",                 "key_elements": ["조달 금액","사용 계획(Use of Funds)","마일스톤","예상 밸류에이션"]},
    {"num": 12, "title": "비전 / 엑시트 시나리오",       "purpose": "장기 가치와 투자 회수 경로",            "key_elements": ["5년 비전","M&A 후보군","IPO 경로","기대 멀티플"]},
]


class IRDeckGenerator(BaseAgent):
    stage_id   = "G6-IR"
    stage_name = "IR Deck 자동 생성"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          company_name (str)
          one_liner (str): 한 줄 설명
          investor_type (str): vc/cvc/angel/government/strategic
          problem_statement (str)
          solution_description (str)
          tam_usd (float)
          sam_usd (float)
          som_usd (float)
          growth_rate_pct (float)
          revenue_model (str)
          arr_usd (float): 연간 반복매출 (없으면 0)
          customer_count (int)
          cac_usd (float)
          ltv_usd (float)
          patent_count (int)
          trl (int)
          team_size (int)
          prior_exits (int)
          funding_ask_usd (float)
          use_of_funds (dict): {"R&D": 40, "영업": 30, "인프라": 20, "운영": 10}
          target_valuation_usd (float)
          revenue_3yr (list[float]): 3개년 매출 예측
          competitors (list[str])
          key_differentiators (list[str])
          exit_targets (list[str]): M&A 후보 기업
        """
        score  = self._score(input_data)
        gate   = self._gate_from_score(score)
        output = self._build_output(input_data, score)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output,
            next_actions=self._next_actions(gate, input_data),
        )

    def _score(self, d: dict) -> float:
        score = 0.0
        # 핵심 데이터 완성도 (각 10점)
        fields = ["company_name","one_liner","problem_statement","solution_description",
                  "tam_usd","revenue_model","funding_ask_usd"]
        score += sum(10 for f in fields if d.get(f))
        # 견인력 지표 (15점)
        if d.get("arr_usd", 0) > 0 or d.get("customer_count", 0) > 0:
            score += 15
        # 재무 계획 (15점)
        if d.get("revenue_3yr") and len(d["revenue_3yr"]) >= 3:
            score += 15
        return round(min(score, 100), 1)

    def _build_output(self, d: dict, score: float) -> dict:
        inv_type = d.get("investor_type", "vc")
        inv      = _INVESTOR_TYPES.get(inv_type, _INVESTOR_TYPES["vc"])

        # 슬라이드별 콘텐츠 생성
        slides = []
        for s in _SLIDE_STRUCTURE:
            content = self._fill_slide(s, d, inv)
            slides.append({**s, "content": content})

        # LLM: 투자자 유형별 맞춤 피치 스크립트 (핵심 3슬라이드)
        llm_text = self._llm(
            f"회사: {d.get('company_name','')}\n"
            f"한줄설명: {d.get('one_liner','')}\n"
            f"문제: {d.get('problem_statement','')}\n"
            f"솔루션: {d.get('solution_description','')}\n"
            f"투자자유형: {inv['label']} (관심: {inv['focus']})\n"
            f"조달 금액: ${d.get('funding_ask_usd',0):,.0f}\n"
            f"핵심차별화: {d.get('key_differentiators',[])}\n\n"
            f"{inv['label']} 대상 피치 오프닝(30초)·문제슬라이드 스크립트·클로징 멘트를 JSON으로:\n"
            '{"opening_30s":"","problem_script":"","closing_line":"","investor_hook":""}',
            system=f"스타트업 IR 전문가. {inv['label']} 투자자 관점에서 설득력 있는 피치 스크립트 작성. JSON만 반환."
        )
        try:
            import json
            pitch = json.loads(llm_text)
        except Exception:
            pitch = {"opening_30s": d.get("one_liner",""), "problem_script": "", "closing_line": "", "investor_hook": ""}

        # Use of Funds 파이
        uof = d.get("use_of_funds", {"R&D": 40, "영업마케팅": 30, "인프라": 20, "운영": 10})
        ask = d.get("funding_ask_usd", 0)
        uof_detail = {k: {"pct": v, "usd": round(ask * v / 100)} for k, v in uof.items()}

        return {
            "ir_deck": {
                "company_name":    d.get("company_name", ""),
                "investor_type":   inv["label"],
                "investor_focus":  inv["focus"],
                "key_metric":      inv["metric"],
                "slide_count":     len(slides),
                "slides":          slides,
            },
            "pitch_scripts": pitch,
            "use_of_funds":  uof_detail,
            "key_metrics_summary": {
                "tam_usd":         d.get("tam_usd", 0),
                "arr_usd":         d.get("arr_usd", 0),
                "customer_count":  d.get("customer_count", 0),
                "ltv_cac_ratio":   round(d.get("ltv_usd",0) / d.get("cac_usd",1), 2) if d.get("cac_usd") else 0,
                "trl":             d.get("trl", 0),
                "patent_count":    d.get("patent_count", 0),
                "funding_ask_usd": d.get("funding_ask_usd", 0),
                "target_valuation_usd": d.get("target_valuation_usd", 0),
            },
            "ir_readiness_score": score,
        }

    def _fill_slide(self, slide: dict, d: dict, inv: dict) -> dict:
        num = slide["num"]
        if num == 1:
            return {"headline": d.get("company_name",""), "subheadline": d.get("one_liner",""),
                    "key_stat": f"TRL {d.get('trl',0)} · 특허 {d.get('patent_count',0)}건"}
        elif num == 2:
            return {"headline": "문제", "body": d.get("problem_statement",""), "pain_intensity": "높음"}
        elif num == 3:
            return {"headline": "솔루션", "body": d.get("solution_description",""),
                    "differentiators": d.get("key_differentiators",[])}
        elif num == 4:
            return {"tam": d.get("tam_usd",0), "sam": d.get("sam_usd",0), "som": d.get("som_usd",0),
                    "cagr_pct": d.get("growth_rate_pct",0)}
        elif num == 5:
            return {"trl": d.get("trl",0), "patents": d.get("patent_count",0), "tech_stack": ""}
        elif num == 6:
            return {"model": d.get("revenue_model",""), "cac": d.get("cac_usd",0),
                    "ltv": d.get("ltv_usd",0)}
        elif num == 7:
            return {"arr": d.get("arr_usd",0), "customers": d.get("customer_count",0)}
        elif num == 8:
            return {"competitors": d.get("competitors",[]), "differentiators": d.get("key_differentiators",[])}
        elif num == 9:
            return {"team_size": d.get("team_size",0), "prior_exits": d.get("prior_exits",0)}
        elif num == 10:
            rev = d.get("revenue_3yr",[0,0,0])
            return {"y1": rev[0] if len(rev)>0 else 0, "y2": rev[1] if len(rev)>1 else 0,
                    "y3": rev[2] if len(rev)>2 else 0}
        elif num == 11:
            return {"ask_usd": d.get("funding_ask_usd",0),
                    "valuation_usd": d.get("target_valuation_usd",0),
                    "use_of_funds": d.get("use_of_funds",{})}
        else:
            return {"vision": "", "exit_targets": d.get("exit_targets",[])}

    def _next_actions(self, gate: str, d: dict) -> list[str]:
        actions = []
        if gate == "Go":
            actions.append("IR Deck PDF/PPT 변환 후 투자자 배포 준비")
            actions.append(f"{_INVESTOR_TYPES.get(d.get('investor_type','vc'),{}).get('label','')} 타겟 투자자 리스트 20개 선별")
            actions.append("데모데이·IR 행사 일정 등록")
        elif gate == "Hold":
            missing = [f for f in ["revenue_3yr","customer_count","key_differentiators"] if not d.get(f)]
            if missing:
                actions.append(f"누락 데이터 보완: {missing}")
            actions.append("Traction 지표 강화 후 Deck 완성")
        else:
            actions.append("제품·Traction 없는 상태 — Deck 작성 전 PoC/초기 고객 확보 우선")
        return actions
