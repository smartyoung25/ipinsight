"""G5 사업모델·GTM 전략 설계 — BMC + Lean Startup + EIC BM 검증 + Unit Economics"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# SaaS 벤치마크 (a16z, ChartMogul 2024 기준)
_UNIT_ECON_BENCHMARKS = {
    "ltv_cac_ratio": {"good": 3.0, "excellent": 5.0, "unit": "x"},
    "payback_months": {"good": 18, "excellent": 12, "unit": "months"},
    "gross_margin_pct": {"good": 60, "excellent": 80, "unit": "%"},
    "ndr_pct": {"good": 100, "excellent": 120, "unit": "%"},  # Net Dollar Retention
}

_COMPETITIVE_POSITIONS = {
    "market_leader":   "시장 리더 (>30% 점유율)",
    "challenger":      "도전자 (10~30%)",
    "niche":           "틈새 특화 (<10%, 특정 세그먼트 지배)",
    "new_entrant":     "신규 진입 (점유율 미확보)",
    "disruptor":       "파괴적 혁신 (신시장 창출)",
}


class BMDesigner(BaseAgent):
    stage_id = "G5"
    stage_name = "사업모델·GTM 전략 설계"

    _REVENUE_MODELS = {
        "license": "라이선싱 (선급금 + 로열티)",
        "saas": "SaaS 구독 (월/연 구독료)",
        "hardware_sale": "하드웨어 판매 + 유지보수",
        "service": "기술서비스·컨설팅",
        "platform": "플랫폼 수수료",
        "joint_dev": "공동개발 비용분담",
        "public_procurement": "공공조달·정부사업",
    }

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data: tech_name, customer_segments, value_proposition,
                    channels, revenue_model (list), cost_structure,
                    key_partners, gtm_target_market, gtm_timeline_months,
                    --- Unit Economics (선택) ---
                    cac_usd (float): 고객 획득 비용
                    ltv_usd (float): 고객 생애가치
                    arpu_usd (float): 평균 객단가/월
                    churn_rate_pct (float): 월 이탈률 %
                    gross_margin_pct (float): 매출총이익률 %
                    ndr_pct (float): 순 달러 유지율 %
                    --- 경쟁 매핑 (선택) ---
                    competitors (list of {name, strength, weakness, market_share_pct})
                    competitive_position (str): market_leader|challenger|niche|new_entrant|disruptor
                    --- 시장 규모 (선택) ---
                    tam_usd (float): 전체 시장 규모
                    sam_usd (float): 서비스 가능 시장
                    som_usd (float): 실현 가능 시장 (3년)
        """
        score = self._score(input_data)
        gate = self._gate_from_score(score)
        output_doc = self._build_output(input_data, score)

        # G5 완료 시 → 사업화 로드맵 자동 트리거
        roadmap_doc = None
        if gate in ("Go", "Hold"):
            try:
                from .g5_commercialization_roadmap import CommercializationRoadmap
                cr_input = {
                    **{k: input_data[k] for k in (
                        "tech_name", "tech_id", "current_trl", "target_trl",
                        "base_year", "loi_count", "poc_requests",
                        "team_size", "target_market", "industry_sector",
                        "apply_programs", "tam_usd", "som_usd",
                        "gross_margin_pct", "revenue_model",
                    ) if k in input_data},
                    "bm_output": output_doc,
                }
                roadmap_doc = CommercializationRoadmap().assess(cr_input).output_doc
            except Exception:
                roadmap_doc = None

        # G5 완료 시 → SMK 자동 생성 (G3/G4/G5 통합)
        smk_doc = None
        if gate == "Go":
            try:
                from .smk_generator import SMKGenerator
                smk_input = {
                    "tech_name": input_data.get("tech_name", ""),
                    "industry_sector": input_data.get("industry_sector", ""),
                    "value_proposition": input_data.get("value_proposition", ""),
                    "tam_usd": input_data.get("tam_usd", 0),
                    "sam_usd": input_data.get("sam_usd", 0),
                    "som_usd": input_data.get("som_usd", 0),
                    "revenue_model": (input_data.get("revenue_model") or ["saas"])[0]
                        if input_data.get("revenue_model") else "saas",
                    "price_point_usd": input_data.get("arpu_usd", 500),
                    "growth_rate_pct": input_data.get("growth_rate_pct", 20),
                    # G4 인터뷰 컨텍스트
                    "g4_loi_count": input_data.get("loi_count", 0),
                    "g4_poc_requests": input_data.get("poc_requests", 0),
                    "customer_segments": input_data.get("customer_segments", []),
                    # G5 competitive landscape
                    "g5_competitive_position": input_data.get("competitive_position", "new_entrant"),
                    "g5_competitors": input_data.get("competitors", []),
                    "g5_gtm_strategy": output_doc.get("gtm_strategy", {}),
                    "bm_output": output_doc,
                }
                smk_doc = SMKGenerator().assess(smk_input).output_doc
            except Exception:
                smk_doc = None

        if roadmap_doc:
            output_doc["commercialization_roadmap"] = roadmap_doc
        if smk_doc:
            output_doc["smk"] = smk_doc

        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output_doc,
            next_actions=self._next_actions(gate),
        )

    def _score(self, d: dict) -> float:
        score = 0.0
        # 가치제안 명확성 (20점)
        vp = d.get("value_proposition", "")
        score += 20 if len(vp) > 30 else len(vp) * 0.65
        # 수익모델 선택 (15점)
        score += 15 if d.get("revenue_model") else 0
        # 고객 세그먼트 (15점)
        score += 15 if d.get("customer_segments") else 0
        # 채널 전략 (10점)
        score += 10 if d.get("channels") else 0
        # GTM 계획 (15점)
        score += 15 if d.get("gtm_target_market") and d.get("gtm_timeline_months") else 0
        # Unit Economics (15점) — LTV:CAC ≥ 3x 목표
        ue = self._calc_unit_economics(d)
        ltv_cac = ue.get("ltv_cac_ratio", 0)
        if ltv_cac >= 5:
            score += 15
        elif ltv_cac >= 3:
            score += 10
        elif ltv_cac >= 1:
            score += 5
        elif d.get("gross_margin_pct", 0) >= 50:
            score += 3
        # 경쟁 매핑 (10점)
        competitors = d.get("competitors", [])
        if competitors:
            score += min(10, len(competitors) * 3)
        elif d.get("competitive_position"):
            score += 5
        return round(min(score, 100), 1)

    def _calc_unit_economics(self, d: dict) -> dict:
        """LTV, CAC, LTV:CAC, 회수기간 산출"""
        cac = d.get("cac_usd", 0)
        ltv = d.get("ltv_usd", 0)
        arpu = d.get("arpu_usd", 0)
        churn = d.get("churn_rate_pct", 0)
        gm = d.get("gross_margin_pct", 0)
        ndr = d.get("ndr_pct", 100)

        # LTV 자동 계산 (arpu + churn 있으면)
        if ltv == 0 and arpu > 0 and churn > 0:
            ltv = round(arpu * (gm / 100 if gm else 1) / (churn / 100), 0)

        ltv_cac = round(ltv / cac, 2) if cac > 0 and ltv > 0 else 0
        payback = round(cac / (arpu * (gm / 100 if gm else 1)), 1) if arpu > 0 and gm > 0 else None

        def _grade(val, metric):
            b = _UNIT_ECON_BENCHMARKS.get(metric, {})
            if not b:
                return "N/A"
            if metric == "payback_months":
                if val and val <= b["excellent"]:
                    return "Excellent"
                if val and val <= b["good"]:
                    return "Good"
                return "Needs Work"
            if val >= b.get("excellent", 9999):
                return "Excellent"
            if val >= b.get("good", 9999):
                return "Good"
            return "Needs Work"

        return {
            "cac_usd": cac,
            "ltv_usd": ltv,
            "ltv_cac_ratio": ltv_cac,
            "payback_months": payback,
            "gross_margin_pct": gm,
            "ndr_pct": ndr,
            "grades": {
                "ltv_cac": _grade(ltv_cac, "ltv_cac_ratio"),
                "payback": _grade(payback, "payback_months"),
                "gross_margin": _grade(gm, "gross_margin_pct"),
                "ndr": _grade(ndr, "ndr_pct"),
            },
            "benchmarks": _UNIT_ECON_BENCHMARKS,
            "note": "LTV 자동 계산: ARPU × GM% / 월 이탈률" if ltv and not d.get("ltv_usd") else "",
        }

    def _build_competitive_map(self, d: dict) -> dict:
        """경쟁자 매핑 + TAM/SAM/SOM"""
        competitors = d.get("competitors", [])
        position = d.get("competitive_position", "new_entrant")
        tam = d.get("tam_usd", 0)
        sam = d.get("sam_usd", 0)
        som = d.get("som_usd", 0)

        total_share = sum(c.get("market_share_pct", 0) for c in competitors)
        our_share = max(0, 100 - total_share) if competitors else 0

        return {
            "competitive_position": position,
            "position_label": _COMPETITIVE_POSITIONS.get(position, position),
            "competitors": competitors,
            "our_estimated_share_pct": round(our_share, 1),
            "market_sizing": {
                "tam_usd": tam,
                "sam_usd": sam,
                "som_usd": som,
                "tam_label": f"${tam/1e9:.1f}B" if tam >= 1e9 else (f"${tam/1e6:.0f}M" if tam >= 1e6 else str(tam)),
                "som_to_sam_pct": round(som / sam * 100, 1) if sam > 0 else None,
            },
            "differentiation_gaps": [
                c.get("weakness", "") for c in competitors if c.get("weakness")
            ][:5],
        }

    def _build_output(self, d: dict, score: float) -> dict:
        import json
        revenue_models = d.get("revenue_model", [])
        model_details = {m: self._REVENUE_MODELS.get(m, m) for m in revenue_models}

        ue = self._calc_unit_economics(d)
        competitive_map = self._build_competitive_map(d)

        llm_result = self._llm(
            f"기술: {d.get('tech_name', '')}\n"
            f"고객: {d.get('customer_segments', '')}\n"
            f"가치제안: {d.get('value_proposition', '')}\n"
            f"수익모델: {revenue_models}\n"
            f"Unit Economics LTV:CAC={ue.get('ltv_cac_ratio',0):.1f}x, "
            f"GM={ue.get('gross_margin_pct',0)}%, Payback={ue.get('payback_months')}mo\n"
            f"경쟁 포지션: {competitive_map.get('position_label','')}\n"
            f"GTM 목표시장: {d.get('gtm_target_market', '')}\n\n"
            "최적 가격전략과 GTM 실행계획을 JSON으로:\n"
            '{"pricing_strategy":"","price_point_usd":0,"gtm_phases":[],'
            '"beachhead_market":"","key_milestones":[],"partnership_targets":[],'
            '"unit_econ_improvement_actions":[]}',
            system="GTM 전략 전문가. JSON만 반환."
        )
        try:
            gtm = json.loads(llm_result)
        except Exception:
            gtm = {"pricing_strategy": llm_result, "gtm_phases": [],
                   "unit_econ_improvement_actions": [
                       "CAC 절감: 콘텐츠 마케팅 + 파트너 채널 우선",
                       "LTV 증대: 추가 모듈 Upsell + 연간 계약 전환",
                       "이탈률 감소: 온보딩 강화 + QBR 정례화",
                   ]}

        royalty_kb = self._load_knowledge("royalty_benchmarks.json")

        return {
            "business_model_canvas": {
                "customer_segments": d.get("customer_segments", []),
                "value_proposition": d.get("value_proposition", ""),
                "channels": d.get("channels", []),
                "revenue_streams": model_details,
                "cost_structure": d.get("cost_structure", {}),
                "key_partners": d.get("key_partners", []),
            },
            "revenue_model_design": {
                "selected_models": revenue_models,
                "model_descriptions": model_details,
                "royalty_benchmarks": royalty_kb.get("deal_structures", {}),
            },
            "unit_economics": ue,
            "competitive_landscape": competitive_map,
            "gtm_strategy": gtm,
            "partnership_strategy": {
                "target_markets": [d.get("gtm_target_market", "")],
                "global_support_channels": ["KOTRA", "EEN (Enterprise Europe Network)", "Enterprise Singapore"],
                "timeline_months": d.get("gtm_timeline_months", 12),
            },
            "bm_score": score,
        }

    def _next_actions(self, gate: str) -> list[str]:
        if gate == "Go":
            return [
                "G6 IP·기술 가치평가 진행",
                "Beachhead 고객 3개사 파일럿 계약 체결",
                "파트너십 NDA 체결 및 협상 시작",
            ]
        if gate == "Hold":
            return [
                "수익모델 재설계 (시장 피드백 반영)",
                "가격전략 A/B 테스트 설계",
                "채널 파트너 후보 발굴",
            ]
        return [
            "사업모델 부재 — 기술 적용분야 Pivot 검토",
            "G4 고객검증 재실시 후 BM 재설계",
        ]
