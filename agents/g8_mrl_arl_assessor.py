"""G8 MRL·ARL 3중 성숙도 평가 — DoD MRL + DOE ARL + NIST MEP"""
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
        input_data: trl (int), manufacturing_process_defined (bool),
                    supply_chain_ready (bool), quality_system (str),
                    unit_cost_usd, target_cost_usd, certifications_obtained (list),
                    certifications_required (list), customer_pilots (int),
                    repeat_purchase_rate_pct, regulatory_approved (bool)
        """
        mrl = self._assess_mrl(input_data)
        arl = self._assess_arl(input_data)
        trl = input_data.get("trl", 1)

        # 3중 성숙도 복합 점수 (TRL 40%, MRL 30%, ARL 30%)
        score = round(trl / 9 * 40 + mrl / 10 * 30 + arl / 9 * 30, 1)
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
            match = next((r for r in reg_kb.get("certifications", []) if r.get("cert", "").lower() in cert.lower()), None)
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
                "customer_pilots": input_data.get("customer_pilots", 0),
                "repeat_purchase_rate_pct": input_data.get("repeat_purchase_rate_pct", 0),
                "regulatory_approved": input_data.get("regulatory_approved", False),
                "adoption_risk_dimensions": self._adoption_risks(input_data),
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

    def _assess_arl(self, d: dict) -> int:
        pilots = d.get("customer_pilots", 0)
        repeat = d.get("repeat_purchase_rate_pct", 0)
        approved = d.get("regulatory_approved", False)
        if pilots == 0:
            return 2
        if pilots < 3:
            return 3
        if pilots < 10:
            return 4 if not approved else 5
        if repeat > 30:
            return 7
        if repeat > 10:
            return 6
        return 5

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

    def _adoption_risks(self, d: dict) -> dict:
        return {
            "market_demand_risk": "Low" if d.get("customer_pilots", 0) >= 5 else "High",
            "regulatory_risk": "Low" if d.get("regulatory_approved") else "High",
            "ecosystem_risk": "Medium",
            "economic_risk": "Low" if d.get("repeat_purchase_rate_pct", 0) > 20 else "Medium",
        }

    def _readiness_summary(self, trl: int, mrl: int, arl: int) -> str:
        if trl >= 7 and mrl >= 7 and arl >= 6:
            return "상용화 준비 완료"
        if trl >= 5 and mrl >= 5 and arl >= 4:
            return "부분 준비 — 보완 후 상용화 가능"
        return "추가 개발·검증 필요"

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
