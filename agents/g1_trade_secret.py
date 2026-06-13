"""G1-TS: 트레이드시크릿 vs 특허 경제성 비교 결정 지원
공개·비공개 전략의 비용·수익·위험을 정량화하여 최적 IP 보호 전략 추천.
"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# 보호 전략별 특성
_PROTECTION_STRATEGIES = {
    "patent": {
        "label": "특허 출원",
        "protection_years": 20,
        "cost_usd": {"filing": 5_000, "prosecution": 15_000, "maintenance_annual": 3_000, "enforcement": 100_000},
        "pros": ["법적 독점권(20년)","공개로 기술 신뢰성","기술이전·라이선싱 용이","VC 투자 우대"],
        "cons": ["출원 후 공개(18개월)","유지비 부담","출원~등록 2~5년 소요","역공학 가능"],
        "best_for": ["TRL 5 이상","반복 제조 가능","라이선싱 목표","경쟁사 모방 용이한 기술"],
    },
    "trade_secret": {
        "label": "영업비밀(트레이드시크릿)",
        "protection_years": 999,  # 비밀 유지 시 무기한
        "cost_usd": {"filing": 0, "prosecution": 0, "maintenance_annual": 10_000, "enforcement": 50_000},
        "pros": ["기간 제한 없음","즉시 보호","비용 저렴","경쟁사 취득 불가(합법적으로)"],
        "cons": ["역공학으로 무력화 가능","유출 시 보호 소멸","이전·거래 어려움","입증 부담"],
        "best_for": ["알고리즘·공정·비법","역공학 어려운 기술","내부 사용 중심","출원하면 공개되는 기술"],
    },
    "hybrid": {
        "label": "특허 + 영업비밀 병행",
        "protection_years": 20,
        "cost_usd": {"filing": 5_000, "prosecution": 15_000, "maintenance_annual": 12_000, "enforcement": 120_000},
        "pros": ["핵심 인터페이스 특허 + 구현 세부사항 비밀","최강 방어막","라이선싱 + 운영 이중 보호"],
        "cons": ["비용 최대","관리 복잡","분리 기준 설계 필요"],
        "best_for": ["복합 기술 제품","SaaS(UI특허+알고리즘비밀)","공정+배합 제조업"],
    },
    "copyright_design": {
        "label": "저작권·디자인권",
        "protection_years": 70,
        "cost_usd": {"filing": 500, "prosecution": 0, "maintenance_annual": 0, "enforcement": 30_000},
        "pros": ["자동 발생(저작권)","저비용","디자인 외관 보호"],
        "cons": ["기능적 혁신 보호 불가","아이디어 보호 안 됨","SW 표현만 보호"],
        "best_for": ["UI·그래픽","소프트웨어 코드(저작권)","제품 외관 디자인"],
    },
}

# 기술 특성 → 전략 추천 매트릭스
_RECOMMENDATION_MATRIX = [
    {"condition": lambda d: d.get("reverse_engineerable") is False and d.get("trl",1) >= 5,
     "strategy": "trade_secret", "reason": "역공학 어렵고 TRL 높음 — 영업비밀로 무기한 보호"},
    {"condition": lambda d: d.get("licensing_goal") is True,
     "strategy": "patent",       "reason": "라이선싱 목표 — 특허로 법적 독점권 확보 필수"},
    {"condition": lambda d: d.get("trl",1) >= 6 and d.get("competitor_count",0) >= 3,
     "strategy": "patent",       "reason": "경쟁사 多, TRL 성숙 — 특허로 선점"},
    {"condition": lambda d: d.get("complex_product") is True,
     "strategy": "hybrid",       "reason": "복합 기술 제품 — 특허+영업비밀 병행이 최강"},
    {"condition": lambda d: d.get("software_only") is True,
     "strategy": "hybrid",       "reason": "SW 전용 — 알고리즘 영업비밀 + UI/API 특허"},
]


class TradeSecretAnalyzer(BaseAgent):
    stage_id   = "G1-TS"
    stage_name = "트레이드시크릿 vs 특허 경제성 비교"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          tech_name (str)
          tech_type (str): process/product/software/algorithm/formula
          trl (int)
          reverse_engineerable (bool): 역공학으로 기술 취득 가능 여부
          licensing_goal (bool): 라이선싱·기술이전 목표 여부
          competitor_count (int): 경쟁사 수
          complex_product (bool): 특허+비밀 병행 가능 복합 제품 여부
          software_only (bool): 소프트웨어 전용 기술
          annual_revenue_protected_usd (float): 이 기술로 창출되는 연간 매출
          analysis_years (int): 분석 기간 (기본 10년)
          employee_nda_in_place (bool): 직원 NDA·비밀유지 계약 체결 여부
          key_person_dependency (bool): 핵심 인물 이탈 시 비밀 소멸 위험
        """
        recommended = self._recommend(input_data)
        comparison  = self._compare(input_data)
        score       = self._score(input_data, recommended)
        gate        = self._gate_from_score(score)
        output      = self._build_output(input_data, recommended, comparison, score)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output,
            next_actions=self._next_actions(gate, recommended, input_data),
        )

    def _recommend(self, d: dict) -> str:
        for rule in _RECOMMENDATION_MATRIX:
            try:
                if rule["condition"](d):
                    return rule["strategy"]
            except Exception:
                continue
        return "patent"  # 기본값

    def _compare(self, d: dict) -> dict:
        years   = d.get("analysis_years", 10)
        revenue = d.get("annual_revenue_protected_usd", 0)
        result  = {}
        for strat_key, strat in _PROTECTION_STRATEGIES.items():
            c = strat["cost_usd"]
            total_cost = c["filing"] + c["prosecution"] + c["maintenance_annual"] * min(years, strat["protection_years"])
            protection_value = revenue * min(years, strat["protection_years"]) * 0.15  # 15% 가치 기여 추정
            roi = (protection_value - total_cost) / max(total_cost, 1)
            result[strat_key] = {
                "label":             strat["label"],
                "total_cost_usd":    round(total_cost),
                "protection_value_usd": round(protection_value),
                "roi_ratio":         round(roi, 2),
                "protection_years":  strat["protection_years"],
                "pros":              strat["pros"],
                "cons":              strat["cons"],
                "best_for":          strat["best_for"],
            }
        return result

    def _score(self, d: dict, recommended: str) -> float:
        score = 40.0  # 기본 전략 선택 점수
        # NDA 체결 (20점)
        score += 20 if d.get("employee_nda_in_place") else 0
        # 핵심인물 비의존 (15점)
        score += 15 if not d.get("key_person_dependency") else 0
        # 역공학 어려움 (15점) — 트레이드시크릿 유효성
        score += 15 if not d.get("reverse_engineerable") else 0
        # 라이선싱 목표 + 특허 선택 (10점)
        if d.get("licensing_goal") and recommended == "patent":
            score += 10
        return round(min(score, 100), 1)

    def _build_output(self, d: dict, recommended: str, comparison: dict, score: float) -> dict:
        rec_strategy = _PROTECTION_STRATEGIES.get(recommended, {})

        # 추천 이유
        rec_reason = next(
            (r["reason"] for r in _RECOMMENDATION_MATRIX
             if self._safe_condition(r["condition"], d) and r["strategy"] == recommended),
            "기술 특성 종합 분석 결과"
        )

        llm_text = self._llm(
            f"기술: {d.get('tech_name','')}\n"
            f"기술 유형: {d.get('tech_type','')}\n"
            f"추천 전략: {rec_strategy.get('label','')}\n"
            f"추천 이유: {rec_reason}\n"
            f"역공학 가능: {d.get('reverse_engineerable', True)}\n"
            f"라이선싱 목표: {d.get('licensing_goal', False)}\n"
            f"NDA 체결: {d.get('employee_nda_in_place', False)}\n\n"
            "구체적인 IP 보호 실행 계획 3단계와 주의사항 2가지를 JSON으로:\n"
            '{"action_plan":[],"cautions":[]}',
            system="IP 전략 전문가. 실행 가능한 보호 전략 수립. JSON 반환."
        )
        try:
            import json
            llm_out = json.loads(llm_text)
        except Exception:
            llm_out = {"action_plan": [], "cautions": []}

        return {
            "recommended_strategy": {
                "strategy":   recommended,
                "label":      rec_strategy.get("label", ""),
                "reason":     rec_reason,
                "pros":       rec_strategy.get("pros", []),
                "cons":       rec_strategy.get("cons", []),
                "best_for":   rec_strategy.get("best_for", []),
            },
            "cost_benefit_comparison": comparison,
            "risk_assessment": {
                "reverse_engineering_risk": "높음" if d.get("reverse_engineerable") else "낮음",
                "key_person_risk":          "있음" if d.get("key_person_dependency") else "없음",
                "nda_coverage":             "완비" if d.get("employee_nda_in_place") else "미흡",
                "licensing_feasibility":    "가능" if d.get("licensing_goal") and recommended in ("patent","hybrid") else "제한",
            },
            "action_plan":    llm_out.get("action_plan", []),
            "cautions":       llm_out.get("cautions", []),
            "ts_score":       score,
        }

    def _safe_condition(self, cond, d):
        try:
            return cond(d)
        except Exception:
            return False

    def _next_actions(self, gate: str, recommended: str, d: dict) -> list[str]:
        strat = _PROTECTION_STRATEGIES.get(recommended, {})
        actions = []
        if gate in ("Go", "Hold"):
            actions.append(f"채택 전략: {strat.get('label','')}")
            if recommended in ("trade_secret", "hybrid") and not d.get("employee_nda_in_place"):
                actions.append("즉시: 전 직원 NDA·비밀유지 계약 체결 (영업비밀 보호 선행 조건)")
            if recommended in ("patent", "hybrid"):
                actions.append("특허 변리사 선임 후 명세서 초안 작성 착수")
        else:
            actions.append("IP 보호 전략 미결정 — 전문 변리사 상담 후 재평가")
        return actions
