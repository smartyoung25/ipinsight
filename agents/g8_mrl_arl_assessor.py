"""G8 MRL·ARL 3중 성숙도 평가 — DoD MRL + DOE ARL 5차원 독립 평가 + NIST MEP

DOE ARL 5차원 독립 평가 (v2 — 공식 표준 정합):
  market(25%)   : 시장 수요 증거 단계
  customer(25%) : 고객 행동 변화·채택 검증 단계
  regulatory(20%): 규제·인증 취득 진행도
  economic(20%) : 경제성·ROI 실증 단계
  ecosystem(10%): 생태계·인프라·파트너 단계

ARL 최종 = 5차원 가중평균 − 병목 패널티
병목 원칙: 단일 차원 ARL <= 2이면 전체 ARL 최대 4로 제한
"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# NIST MEP (Manufacturing Extension Partnership) 벤치마킹:
# 중소 제조업체 대상 공정개선·원가절감 체크리스트 (TRL 7~9 빠른 양산 진입)
_NIST_MEP_CHECKLIST = [
    {"item": "린(Lean) 제조 프로세스 적용", "mrl_impact": "+1"},
    {"item": "공급망 2~3개 이중화 확보", "mrl_impact": "+1"},
    {"item": "ISO 9001 또는 AS9100 품질시스템", "mrl_impact": "+1"},
    {"item": "단위 생산원가 < 목표가의 1.5배", "mrl_impact": "+1"},
    {"item": "초기 양산 50단위 이상 완료", "mrl_impact": "+2"},
    {"item": "불량률 < 2% (Six Sigma 3σ)", "mrl_impact": "+1"},
]


class MRLARLAssessor(BaseAgent):
    stage_id = "G8"
    stage_name = "MRL·ARL 3중 성숙도 평가"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          trl (int): 현재 TRL
          manufacturing_process_defined (bool), supply_chain_ready (bool),
          quality_system (str), unit_cost_usd, target_cost_usd,
          certifications_obtained (list), certifications_required (list),
          --- ARL 5차원 입력 (DOE 공식 기준) ---
          market_interview_count (int): 고객 인터뷰 건수
          market_tam_validated (bool): TAM 정량화 완료
          market_repeat_purchase_pct (float): 재구매율 %
          customer_loi_count (int): LoI/MOU 건수
          customer_poc_count (int): PoC 참여 고객수
          customer_nps (float, optional): NPS 점수
          regulatory_approved (bool): 주요 인증 취득 여부
          regulatory_submission_done (bool): 인증 신청 완료
          economic_pilot_revenue_usd (float): 파일럿 매출
          economic_break_even_modeled (bool): 손익분기 분석 완료
          economic_unit_economics_validated (bool): 실 Unit Economics 측정
          ecosystem_partner_count (int): 파트너 수
          ecosystem_integration_done (bool): 통합 구현 완료
        """
        mrl = self._assess_mrl(input_data)
        arl_5d = self._assess_arl_5d(input_data)
        arl = arl_5d["arl_final"]
        trl = input_data.get("trl", 1)

        # 3중 성숙도 복합 점수 (TRL 40%, MRL 30%, ARL 30%)
        score = round(trl / 9 * 40 + mrl / 10 * 30 + arl / 9 * 30, 1)

        # ── 규제 리스크 Gate 패널티 (EIC Accelerator 기준) ──
        # regulatory_paths.json 연동: 미취득 인증의 예상 소요월이 클수록 패널티
        reg_penalty, reg_risk_level = self._regulatory_gate_penalty(input_data)
        score = max(0, round(score - reg_penalty, 1))

        gate = self._gate_from_score(score)

        mrl_kb = self._load_knowledge("mrl_framework.json")
        arl_kb = self._load_knowledge("arl_framework.json")
        reg_kb = self._load_knowledge("regulatory_paths.json")

        mrl_info = next((l for l in mrl_kb.get("levels", []) if l["mrl"] == mrl), {})
        arl_info = next((l for l in arl_kb.get("levels", []) if l["arl"] == arl), {})

        cert_required = input_data.get("certifications_required", [])
        cert_obtained = input_data.get("certifications_obtained", [])
        cert_gap = [c for c in cert_required if c not in cert_obtained]

        reg_paths = []
        for cert in cert_gap:
            match = next(
                (r for r in reg_kb.get("certifications", []) if r.get("cert", "").lower() in cert.lower()),
                None
            )
            if match:
                reg_paths.append({
                    "cert": cert,
                    "duration_months": match.get("duration_months", {}).get("typical", 12),
                    "cost_note": str(match.get("cost_usd", match.get("cost_eur", match.get("cost_krw", "협의")))),
                    "body": match.get("body", ""),
                })

        output_doc = {
            "triple_maturity_assessment": {
                "trl": trl,
                "mrl": mrl,
                "arl": arl,
                "composite_score": score,
                "regulatory_risk_level": reg_risk_level,
                "regulatory_gate_penalty": reg_penalty,
                "readiness_summary": self._readiness_summary(trl, mrl, arl),
            },
            "mrl_assessment": {
                "mrl_level": mrl,
                "mrl_name": mrl_info.get("name", ""),
                "mrl_description": mrl_info.get("description", ""),
                "manufacturing_process": input_data.get("manufacturing_process_defined", False),
                "supply_chain_ready": input_data.get("supply_chain_ready", False),
                "quality_system": input_data.get("quality_system", ""),
                "cost_competitiveness": self._cost_check(input_data),
            },
            "arl_assessment": {
                "arl_level": arl,
                "arl_name": arl_info.get("name", ""),
                "arl_5d_detail": arl_5d,
                "bottleneck_dimension": arl_5d.get("bottleneck"),
                "adoption_risk_dimensions": self._adoption_risks_5d(arl_5d),
            },
            "certification_roadmap": {
                "obtained": cert_obtained,
                "required": cert_required,
                "gap": cert_gap,
                "regulatory_paths": reg_paths,
                "total_cert_months": sum(r["duration_months"] for r in reg_paths),
            },
            "nist_mep_checklist": {
                "items": _NIST_MEP_CHECKLIST,
                "note": "NIST MEP 기준: 중소 제조업체 TRL 7~9 빠른 양산 진입 체크리스트",
                "applicable": input_data.get("mrl_target", 8) >= 7,
            },
        }

        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output_doc,
            next_actions=self._next_actions(gate, mrl, arl, cert_gap),
        )

    def _assess_mrl(self, d: dict) -> int:
        trl = d.get("trl", 1)
        if not d.get("manufacturing_process_defined"):
            return min(trl, 3)
        if not d.get("supply_chain_ready"):
            return min(trl, 5)
        unit_cost = d.get("unit_cost_usd", 999999)
        target_cost = d.get("target_cost_usd", 1)
        if unit_cost > target_cost * 2:
            return min(trl, 6)
        if d.get("quality_system") in ["ISO9001", "ISO13485", "GMP"]:
            return min(10, trl + 1)
        return min(8, trl)

    def _assess_arl_5d(self, d: dict) -> dict:
        """DOE ARL 5차원 독립 평가 — 가중평균 + 병목 원칙"""
        m  = self._arl_market(d)
        c  = self._arl_customer(d)
        rg = self._arl_regulatory(d)
        ec = self._arl_economic(d)
        es = self._arl_ecosystem(d)

        # 가중평균 (knowledge/arl_framework.json dimension_weights)
        weighted = m * 0.25 + c * 0.25 + rg * 0.20 + ec * 0.20 + es * 0.10

        # 병목 원칙: 단일 차원 <=2 이면 전체 최대 4
        dims = {"market": m, "customer": c, "regulatory": rg, "economic": ec, "ecosystem": es}
        bottleneck = min(dims, key=dims.get)
        if dims[bottleneck] <= 2:
            arl_final = min(4, round(weighted))
            bottleneck_applied = True
        else:
            arl_final = max(1, min(9, round(weighted)))
            bottleneck_applied = False

        return {
            "arl_final": arl_final,
            "weighted_raw": round(weighted, 2),
            "bottleneck": bottleneck if bottleneck_applied else None,
            "bottleneck_applied": bottleneck_applied,
            "dimensions": {
                "market":     {"arl": m,  "weight": 0.25},
                "customer":   {"arl": c,  "weight": 0.25},
                "regulatory": {"arl": rg, "weight": 0.20},
                "economic":   {"arl": ec, "weight": 0.20},
                "ecosystem":  {"arl": es, "weight": 0.10},
            },
        }

    # ── ARL 차원별 평가 ──

    def _arl_market(self, d: dict) -> int:
        n = d.get("market_interview_count", d.get("customer_pilots", 0))
        tam_ok = d.get("market_tam_validated", False)
        repeat = d.get("market_repeat_purchase_pct", d.get("repeat_purchase_rate_pct", 0))
        if not tam_ok and n < 5:
            return 1
        if not tam_ok:
            return 2
        if n < 10:
            return 3
        if n < 30:
            return 4
        if repeat == 0:
            return 5
        if repeat > 20:
            return 7
        if repeat > 5:
            return 6
        return 5

    def _arl_customer(self, d: dict) -> int:
        loi = d.get("customer_loi_count", 0)
        poc = d.get("customer_poc_count", d.get("customer_pilots", 0))
        nps = d.get("customer_nps", -1)
        repeat = d.get("market_repeat_purchase_pct", d.get("repeat_purchase_rate_pct", 0))
        if loi == 0 and poc == 0:
            return 2
        if loi >= 1 and poc == 0:
            return 3
        if poc >= 3 and loi >= 1:
            base = 4
        elif poc >= 1:
            base = 4
        else:
            base = 3
        if repeat > 0:
            base = max(base, 5)
        if nps >= 30:
            base = max(base, 7)
        elif nps >= 0:
            base = max(base, 6)
        return min(9, base)

    def _arl_regulatory(self, d: dict) -> int:
        approved = d.get("regulatory_approved", False)
        submitted = d.get("regulatory_submission_done", False)
        cert_req = d.get("certifications_required", [])
        cert_got = set(d.get("certifications_obtained", []))
        if not cert_req:
            return 5  # 규제 불필요 = 장벽 없음
        coverage = len([c for c in cert_req if c in cert_got]) / len(cert_req)
        if coverage == 0 and not submitted:
            return 2
        if coverage == 0 and submitted:
            return 4
        if coverage < 1.0:
            return 5
        return 6 if approved else 5

    def _arl_economic(self, d: dict) -> int:
        pilot_rev = d.get("economic_pilot_revenue_usd", 0)
        be_modeled = d.get("economic_break_even_modeled", False)
        ue_validated = d.get("economic_unit_economics_validated", False)
        if not be_modeled:
            return 2
        if be_modeled and not ue_validated:
            return 3
        if ue_validated and pilot_rev == 0:
            return 4
        if pilot_rev > 0 and pilot_rev < 50_000:
            return 5
        if pilot_rev >= 50_000:
            return 6
        return 3

    def _arl_ecosystem(self, d: dict) -> int:
        partners = d.get("ecosystem_partner_count", 0)
        integrated = d.get("ecosystem_integration_done", False)
        if partners == 0:
            return 2
        if partners >= 1 and not integrated:
            return 4
        if integrated and partners >= 2:
            return 6
        if integrated:
            return 5
        return 3

    def _cost_check(self, d: dict) -> dict:
        unit = d.get("unit_cost_usd", 0)
        target = d.get("target_cost_usd", 1)
        ratio = round(unit / max(target, 0.01), 2)
        return {
            "unit_cost_usd": unit,
            "target_cost_usd": target,
            "cost_ratio": ratio,
            "status": "적정" if ratio <= 1.5 else "과다" if ratio <= 3 else "심각",
        }

    def _adoption_risks_5d(self, arl_5d: dict) -> dict:
        """ARL 점수 → 리스크 레벨 변환 (DOE 5차원 정합)"""
        def level(arl_score: int) -> str:
            if arl_score >= 6:
                return "Low"
            if arl_score >= 4:
                return "Medium"
            return "High"

        dims = arl_5d.get("dimensions", {})
        return {
            d: {"arl": v["arl"], "risk": level(v["arl"])}
            for d, v in dims.items()
        }

    def _readiness_summary(self, trl: int, mrl: int, arl: int) -> str:
        if trl >= 7 and mrl >= 7 and arl >= 6:
            return "상용화 준비 완료"
        if trl >= 5 and mrl >= 5 and arl >= 4:
            return "부분 준비 — 보완 후 상용화 가능"
        return "추가 개발·검증 필요"

    def _regulatory_gate_penalty(self, d: dict) -> tuple[float, str]:
        """규제 미취득 인증의 예상 소요 기간으로 Gate 패널티 산출 (EIC Accelerator 기준)
        - 총 소요 24개월 초과: High risk → -15점
        - 12~24개월: Medium → -8점
        - 12개월 미만: Low → 0점
        """
        reg_kb = self._load_knowledge("regulatory_paths.json")
        cert_required = d.get("certifications_required", [])
        cert_obtained = set(d.get("certifications_obtained", []))
        cert_gap = [c for c in cert_required if c not in cert_obtained]

        total_months = 0
        for cert in cert_gap:
            match = next(
                (r for r in reg_kb.get("certifications", [])
                 if r.get("cert", "").lower() in cert.lower()),
                None
            )
            if match:
                total_months += match.get("duration_months", {}).get("typical", 12)
            else:
                total_months += 12  # 미지정 인증은 보수적으로 12개월 가정

        if total_months > 24:
            return 15.0, "High"
        elif total_months > 12:
            return 8.0, "Medium"
        else:
            return 0.0, "Low"

    def _next_actions(self, gate: str, mrl: int, arl: int, cert_gap: list) -> list[str]:
        actions = []
        if gate == "Go":
            actions.append("G9 거래·투자 방식 결정 진행")
            actions.append("양산 파트너 최종 선정 및 계약")
        else:
            if mrl < 6:
                actions.append(f"MRL {mrl} → {mrl+2} 달성: 제조공정 확립·원가절감")
            if arl < 5:
                actions.append(f"ARL {arl} → {arl+2} 달성: 추가 파일럿 고객 확보")
            if cert_gap:
                actions.append(f"인증 취득 우선: {', '.join(cert_gap[:3])}")
        return actions
