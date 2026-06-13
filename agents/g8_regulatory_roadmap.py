"""G8-Reg: 도메인별 규제·인증 로드맵 — 바이오·의료기기·SaMD·하드웨어·소프트웨어
실제 인증 경로, 소요 기간, 비용, 전략적 우선순위를 정량화.
"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# 도메인별 규제 경로 DB
_DOMAIN_REGULATIONS = {
    "medical_device": {
        "label": "의료기기",
        "certifications": {
            "KOR": {"body": "식품의약품안전처(MFDS)", "class": ["1등급","2등급","3등급","4등급"],
                    "months": [3, 6, 12, 24], "cost_usd": [2_000, 15_000, 60_000, 150_000]},
            "USA": {"body": "FDA", "class": ["Class I(510k면제)","Class II(510k)","Class III(PMA)"],
                    "months": [3, 12, 36], "cost_usd": [5_000, 50_000, 500_000]},
            "EU":  {"body": "CE(MDR 2017/745)", "class": ["Class I","Class IIa","Class IIb","Class III"],
                    "months": [6, 12, 18, 36], "cost_usd": [10_000, 30_000, 80_000, 200_000]},
            "JPN": {"body": "PMDA(薬機法)", "class": ["一般医療機器","管理医療機器","高度管理医療機器"],
                    "months": [6, 12, 24], "cost_usd": [15_000, 50_000, 200_000]},
        },
        "key_risks": ["임상 데이터 요구", "QMS(ISO 13485) 구축 필수", "생체적합성 시험"],
        "iso_standards": ["ISO 13485", "IEC 62304(소프트웨어)", "ISO 14971(위험관리)"],
    },
    "samd": {
        "label": "SaMD(의료용 소프트웨어/AI)",
        "certifications": {
            "KOR": {"body": "MFDS AI·소프트웨어 의료기기 가이드라인",
                    "class": ["독립형SW 2등급","독립형SW 3등급"],
                    "months": [6, 18], "cost_usd": [10_000, 80_000]},
            "USA": {"body": "FDA(Software as Medical Device)", "class": ["Non-Device Software","Class II(De Novo)","Class III"],
                    "months": [6, 18, 36], "cost_usd": [0, 80_000, 500_000]},
            "EU":  {"body": "CE(MDR+IVDR)", "class": ["Class I SW","Class IIa/IIb"],
                    "months": [9, 24], "cost_usd": [15_000, 100_000]},
        },
        "key_risks": ["알고리즘 편향성 검증", "Real-World Performance 모니터링 의무",
                      "사이버보안(IEC 81001-5-1)", "Explainability 요구"],
        "iso_standards": ["IEC 62304", "ISO 14971", "IEC 82304-1", "ISO/IEC 27001"],
    },
    "biotech_pharma": {
        "label": "바이오·제약",
        "certifications": {
            "KOR": {"body": "MFDS(식약처)", "class": ["임상1상","임상2상","임상3상","품목허가"],
                    "months": [18, 36, 60, 12], "cost_usd": [500_000, 3_000_000, 15_000_000, 200_000]},
            "USA": {"body": "FDA(IND→NDA/BLA)", "class": ["IND","Phase I","Phase II","Phase III","NDA/BLA"],
                    "months": [3, 24, 36, 60, 18], "cost_usd": [50_000, 2_000_000, 10_000_000, 50_000_000, 2_000_000]},
            "EU":  {"body": "EMA(IMPD→MAA)", "class": ["CTA","Phase I-III","MAA"],
                    "months": [2, 84, 18], "cost_usd": [30_000, 30_000_000, 3_000_000]},
        },
        "key_risks": ["임상 실패율 90%+", "GMP 제조시설 필수", "가격 협상(보험등재)"],
        "iso_standards": ["ICH Q10", "GLP", "GCP", "GMP(ICH Q7)"],
    },
    "hardware_iot": {
        "label": "하드웨어·IoT",
        "certifications": {
            "KOR": {"body": "국립전파연구원(KCC) + KC인증",
                    "class": ["전자파적합성(EMC)","안전인증"],
                    "months": [3, 4], "cost_usd": [5_000, 8_000]},
            "USA": {"body": "FCC Part 15 + UL",
                    "class": ["FCC(전파)","UL(안전)"],
                    "months": [3, 6], "cost_usd": [10_000, 20_000]},
            "EU":  {"body": "CE Marking(RED/LVD/EMC)",
                    "class": ["RED(무선)","LVD(저전압)","EMC"],
                    "months": [4, 4, 3], "cost_usd": [15_000, 10_000, 8_000]},
        },
        "key_risks": ["공급망 리스크(칩부족)", "RoHS·REACH 유해물질", "사이버보안 의무화(EU CRA)"],
        "iso_standards": ["IEC 61000(EMC)", "IEC 60950/62368(안전)", "ISO/IEC 27001(보안)"],
    },
    "agri_food_tech": {
        "label": "농업·식품기술",
        "certifications": {
            "KOR": {"body": "농촌진흥청·식약처",
                    "class": ["농약등록","비료등록","식품위생허가"],
                    "months": [24, 12, 6], "cost_usd": [100_000, 30_000, 10_000]},
            "USA": {"body": "USDA·EPA·FDA",
                    "class": ["EPA농약등록","USDA유기인증","FDA식품허가"],
                    "months": [36, 12, 18], "cost_usd": [500_000, 15_000, 50_000]},
            "EU":  {"body": "EFSA·EU 식물보호제 규정",
                    "class": ["식물보호제승인","신식품(Novel Food)"],
                    "months": [36, 18], "cost_usd": [1_000_000, 200_000]},
        },
        "key_risks": ["장기 필드 트라이얼 필요", "환경 영향 평가", "GMO 규제"],
        "iso_standards": ["ISO 22000(식품안전)", "HACCP", "GlobalG.A.P"],
    },
    "software_general": {
        "label": "일반 소프트웨어·SaaS",
        "certifications": {
            "KOR": {"body": "한국인터넷진흥원(KISA)·개인정보위",
                    "class": ["ISMS-P인증","GS인증"],
                    "months": [6, 3], "cost_usd": [20_000, 5_000]},
            "USA": {"body": "SOC 2 Type II·FedRAMP",
                    "class": ["SOC 2","FedRAMP(정부)"],
                    "months": [6, 18], "cost_usd": [30_000, 500_000]},
            "EU":  {"body": "GDPR·NIS2·사이버복원력법(CRA)",
                    "class": ["GDPR 준수","NIS2(필수서비스)"],
                    "months": [3, 12], "cost_usd": [10_000, 50_000]},
        },
        "key_risks": ["개인정보 규제(GDPR·개인정보보호법)", "AI법(EU AI Act) 고위험 분류",
                      "공급망 보안(SBOM 의무화 추세)"],
        "iso_standards": ["ISO/IEC 27001", "ISO/IEC 27701(개인정보)", "ISO 42001(AI 관리)"],
    },
}

_DEFAULT_DOMAIN = "software_general"


class RegulatoryRoadmapAgent(BaseAgent):
    stage_id   = "G8-Reg"
    stage_name = "도메인별 규제·인증 로드맵"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          domain (str): medical_device/samd/biotech_pharma/hardware_iot/agri_food_tech/software_general
          product_class (str): 제품 등급/분류 (예: '2등급', 'Class II', 'Phase II')
          target_countries (list[str]): 진입 우선 국가 ['KOR','USA','EU','JPN']
          trl (int): 현재 TRL
          has_clinical_data (bool): 임상·현장 데이터 보유 여부
          has_qms (bool): 품질관리시스템 구축 여부 (ISO 13485 등)
          regulatory_budget_usd (float): 인증 예산
          timeline_target_months (int): 목표 인증 완료 기간
          previous_approvals (list[str]): 기보유 인증 목록
        """
        domain   = input_data.get("domain", _DEFAULT_DOMAIN)
        reg_data = _DOMAIN_REGULATIONS.get(domain, _DOMAIN_REGULATIONS[_DEFAULT_DOMAIN])
        roadmap  = self._build_roadmap(input_data, reg_data)
        score    = self._score(input_data, roadmap)
        gate     = self._gate_from_score(score)
        output   = self._build_output(input_data, reg_data, roadmap, score)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output,
            next_actions=self._next_actions(gate, input_data, roadmap),
        )

    # ── 로드맵 구성 ──────────────────────────────────────────────────────────
    def _build_roadmap(self, d: dict, reg: dict) -> list[dict]:
        countries = d.get("target_countries", ["KOR"])
        budget    = d.get("regulatory_budget_usd", float("inf"))
        timeline  = d.get("timeline_target_months", 999)
        previous  = set(d.get("previous_approvals", []))
        roadmap   = []

        for country in countries:
            if country not in reg.get("certifications", {}):
                continue
            cert = reg["certifications"][country]
            classes   = cert.get("class", [])
            months    = cert.get("months", [])
            costs     = cert.get("cost_usd", [])

            for i, cls in enumerate(classes):
                if cls in previous:
                    continue
                m = months[i] if i < len(months) else months[-1]
                c = costs[i]  if i < len(costs)  else costs[-1]
                feasible = (c <= budget) and (m <= timeline)
                roadmap.append({
                    "country":       country,
                    "body":          cert["body"],
                    "certification": cls,
                    "months":        m,
                    "cost_usd":      c,
                    "feasible":      feasible,
                    "priority":      "1순위" if country == countries[0] and i == 0 else f"{country} 확장",
                })

        # 비용·기간 기준 정렬
        roadmap.sort(key=lambda x: (not x["feasible"], x["cost_usd"]))
        return roadmap

    # ── 점수 ─────────────────────────────────────────────────────────────────
    def _score(self, d: dict, roadmap: list) -> float:
        score = 0.0
        domain = d.get("domain", _DEFAULT_DOMAIN)

        # TRL 준비도 (25점)
        trl = d.get("trl", 1)
        score += min(25, (trl / 9) * 25)

        # 실현 가능 인증 수 (25점)
        feasible = [r for r in roadmap if r["feasible"]]
        score += min(25, len(feasible) * 8)

        # QMS 구축 (20점) — 의료기기·바이오 필수
        if domain in ("medical_device", "samd", "biotech_pharma"):
            score += 20 if d.get("has_qms") else 0
        else:
            score += 15  # 비필수 도메인 기본 점수

        # 임상·현장 데이터 (15점)
        if domain in ("medical_device", "samd", "biotech_pharma", "agri_food_tech"):
            score += 15 if d.get("has_clinical_data") else 0
        else:
            score += 10

        # 예산 충분성 (15점)
        budget = d.get("regulatory_budget_usd", 0)
        min_cost = min((r["cost_usd"] for r in roadmap), default=0)
        if budget >= min_cost * 1.5:
            score += 15
        elif budget >= min_cost:
            score += 8

        return round(min(score, 100), 1)

    # ── 산출물 ───────────────────────────────────────────────────────────────
    def _build_output(self, d: dict, reg: dict, roadmap: list, score: float) -> dict:
        domain = d.get("domain", _DEFAULT_DOMAIN)
        total_feasible_cost = sum(r["cost_usd"] for r in roadmap if r["feasible"])
        total_feasible_months = max((r["months"] for r in roadmap if r["feasible"]), default=0)

        llm_text = self._llm(
            f"도메인: {reg['label']}\n"
            f"목표 국가: {d.get('target_countries', ['KOR'])}\n"
            f"현재 TRL: {d.get('trl', 1)}\n"
            f"QMS 구축: {d.get('has_qms', False)}\n"
            f"임상 데이터: {d.get('has_clinical_data', False)}\n"
            f"예산: ${d.get('regulatory_budget_usd', 0):,.0f}\n"
            f"주요 리스크: {reg['key_risks']}\n"
            f"필수 표준: {reg['iso_standards']}\n\n"
            "규제 전략 핵심 조언 3가지와 흔한 실수 2가지를 JSON으로:\n"
            '{"strategy_tips":[],"common_mistakes":[]}',
            system="규제·인증 전문가. 도메인별 실제 경험 기반 조언. JSON 반환."
        )
        try:
            import json
            llm_out = json.loads(llm_text)
        except Exception:
            llm_out = {"strategy_tips": [], "common_mistakes": []}

        # 준비 격차
        gaps = []
        if domain in ("medical_device", "samd") and not d.get("has_qms"):
            gaps.append({"item": "QMS(ISO 13485) 미구축", "urgency": "필수", "months_to_resolve": 12})
        if domain in ("medical_device", "samd", "biotech_pharma") and not d.get("has_clinical_data"):
            gaps.append({"item": "임상·현장 데이터 미확보", "urgency": "필수", "months_to_resolve": 18})
        if d.get("trl", 1) < 6 and domain != "software_general":
            gaps.append({"item": f"TRL {d.get('trl',1)} 낮음 — TRL 6 이상 요구", "urgency": "선행조건", "months_to_resolve": 12})

        return {
            "regulatory_roadmap": {
                "domain":          reg["label"],
                "certifications":  roadmap,
                "total_cost_usd":  total_feasible_cost,
                "max_months":      total_feasible_months,
                "feasible_count":  len([r for r in roadmap if r["feasible"]]),
            },
            "compliance_framework": {
                "required_standards":  reg["iso_standards"],
                "key_risks":           reg["key_risks"],
                "has_qms":             d.get("has_qms", False),
                "has_clinical_data":   d.get("has_clinical_data", False),
            },
            "readiness_gaps":   gaps,
            "strategy_tips":    llm_out.get("strategy_tips", []),
            "common_mistakes":  llm_out.get("common_mistakes", []),
            "regulatory_score": score,
        }

    def _next_actions(self, gate: str, d: dict, roadmap: list) -> list[str]:
        domain  = d.get("domain", _DEFAULT_DOMAIN)
        actions = []
        if gate == "Go":
            first = next((r for r in roadmap if r["feasible"]), None)
            if first:
                actions.append(f"즉시 착수: {first['country']} {first['certification']} 인증 — ${first['cost_usd']:,} / {first['months']}개월")
            actions.append("인증 전문 컨설턴트 선정 및 계약")
        elif gate == "Hold":
            if domain in ("medical_device", "samd") and not d.get("has_qms"):
                actions.append("QMS(ISO 13485) 구축 즉시 착수 — 인증 선행 조건")
            if not d.get("has_clinical_data") and domain in ("medical_device", "samd", "biotech_pharma"):
                actions.append("임상·현장 데이터 확보 계획 수립 (IRB 승인 포함)")
            actions.append("규제 예산 증액 또는 우선 국가 1개로 집중 전략 수정")
        else:
            actions.append("현재 TRL·예산으로는 규제 통과 불가 — TRL 향상 후 재평가")
            actions.append("낮은 비용의 국가·등급부터 순차 접근 전략으로 변경")
        return actions
