"""G7 PoC·실증·위험저감 — Catapult·Fraunhofer·TIPS·Venture Client + 외부 플랫폼 카탈로그"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# Venture Client Model (BMW i Ventures 벤치마킹):
# 기업이 스타트업의 첫 번째 고객이 되어 PoC 비용을 직접 부담.
_VENTURE_CLIENT_TEMPLATE = {
    "model": "Venture Client",
    "how": "파트너 기업이 PoC 비용 부담 + 구매의향서(LoI) 사전 체결",
    "benefit": "기술기업 매출+레퍼런스 동시 확보, 기업 측 지분 위험 없음",
    "typical_duration_months": 3,
    "criteria": ["기업 내 챔피언(실무추진자) 확보", "파일럿 예산 승인", "성공지표(KPI) 사전 합의"],
}

# 글로벌 PoC 플랫폼 카탈로그 (Catapult·Fraunhofer·TIPS·KSB 등)
POC_PLATFORM_CATALOG = [
    {
        "id": "catapult_digital",
        "name": "Catapult Digital (KTN, UK)",
        "region": ["EU", "GB"],
        "focus": ["AI", "IoT", "Software", "Manufacturing"],
        "model": "Venture Client + Co-funding",
        "duration_months": 3,
        "funding_available": True,
        "url": "https://ktn-uk.org/programme/catapult/",
        "eligibility": "TRL 4~7, UK 또는 EU 기반",
        "contact": "catapult@ktn-uk.org",
    },
    {
        "id": "fraunhofer_austria",
        "name": "Fraunhofer Austria (Research Austria)",
        "region": ["EU", "DE", "AT"],
        "focus": ["Manufacturing", "Energy", "Medical", "Software"],
        "model": "Contract R&D + PoC 공동실증",
        "duration_months": 6,
        "funding_available": True,
        "url": "https://www.fraunhofer.at/",
        "eligibility": "TRL 3~7, 유럽 기업 또는 글로벌 기업 EU법인",
        "contact": "office@fraunhofer.at",
    },
    {
        "id": "tips_kr",
        "name": "TIPS (Tech Incubator Program for Startup, 한국)",
        "region": ["KR"],
        "focus": ["Deeptech", "Biotech", "ICT", "Agritech"],
        "model": "민간 PoC 매칭 + 정부 R&D 보조금",
        "duration_months": 24,
        "funding_available": True,
        "url": "https://www.jointips.or.kr/",
        "eligibility": "7년 이내 창업기업, TRL 4~7",
        "contact": "tips@jointips.or.kr",
    },
    {
        "id": "ksb_pilot_kr",
        "name": "중소벤처기업부 실증특례 (KSB Pilot Exception)",
        "region": ["KR"],
        "focus": ["Smart Farm", "Healthcare", "Mobility", "Energy"],
        "model": "규제 샌드박스 + 실증 비용 지원",
        "duration_months": 12,
        "funding_available": True,
        "url": "https://www.sandbox.go.kr/",
        "eligibility": "한국 법인, 규제 저촉 기술",
        "contact": "sandbox@msit.go.kr",
    },
    {
        "id": "eic_accelerator_eu",
        "name": "EIC Accelerator (EU Horizon Europe)",
        "region": ["EU"],
        "focus": ["Deeptech", "Climate", "Health", "Digital"],
        "model": "보조금 €2.5M + 지분투자 최대 €15M",
        "duration_months": 18,
        "funding_available": True,
        "url": "https://eic.ec.europa.eu/eic-funding/eic-accelerator_en",
        "eligibility": "EU 기반 SME, TRL 5~8",
        "contact": "eic@eic.ec.europa.eu",
    },
    {
        "id": "nist_mep_us",
        "name": "NIST MEP (Manufacturing Extension Partnership, US)",
        "region": ["US"],
        "focus": ["Manufacturing", "Supply Chain", "Quality"],
        "model": "멘토링 + 파일럿 공장 연계",
        "duration_months": 6,
        "funding_available": False,
        "url": "https://www.nist.gov/mep",
        "eligibility": "US 기반 중소 제조기업",
        "contact": "mep@nist.gov",
    },
    {
        "id": "sbir_us",
        "name": "SBIR/STTR Phase II (NSF/DOE/DoD, US)",
        "region": ["US"],
        "focus": ["Deeptech", "Defense", "Energy", "Biotech"],
        "model": "Phase II: 최대 $1.5M R&D 보조금 + 실증",
        "duration_months": 24,
        "funding_available": True,
        "url": "https://www.sbir.gov/",
        "eligibility": "US 기반 중소기업, Phase I 통과",
        "contact": "sbir@sbir.gov",
    },
]


def match_poc_platforms(tech_type: str, regions: list[str], trl: int) -> list[dict]:
    """기술 유형·지역·TRL 기준 적합한 PoC 플랫폼 필터링"""
    results = []
    tech_lower = tech_type.lower()
    region_set = set(r.upper() for r in regions)
    for p in POC_PLATFORM_CATALOG:
        # 지역 매칭
        platform_regions = set(p.get("region", []))
        if not region_set.intersection(platform_regions):
            continue
        # TRL 범위 — 카탈로그에 명시된 범위 확인 (간이: 3~9 모두 허용)
        if trl < 3 or trl > 8:
            continue
        # 포커스 영역 키워드 매칭
        focus_keywords = " ".join(p.get("focus", [])).lower()
        keyword_map = {
            "agritech": ["agriculture", "farm", "food", "agri"],
            "medical_device": ["medical", "health", "biotech"],
            "software_saas": ["software", "ai", "iot", "digital", "ict"],
            "energy": ["energy", "climate", "clean"],
            "manufacturing": ["manufacturing", "supply chain", "quality"],
        }
        relevant_kws = keyword_map.get(tech_lower, [tech_lower])
        if any(kw in focus_keywords for kw in relevant_kws):
            results.append(p)
        elif len(results) < 2:  # 키워드 미매칭이어도 최소 2개 제안
            results.append(p)
    return results[:4]


class PoCManager(BaseAgent):
    stage_id = "G7"
    stage_name = "PoC·실증·위험저감"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data: tech_name, poc_objectives (list), poc_kpis (list of {name, target, actual}),
                    test_environment, customer_feedback (list), issues_found (list),
                    risk_mitigations (list), poc_duration_months,
                    venture_client_partner (str, optional): Venture Client 기업명
                    tech_type (str): agritech|medical_device|software_saas|energy|manufacturing
                    target_regions (list): KR|US|EU|JP 등
                    trl (int): 현재 TRL
                    external_poc_registered (bool): 외부 플랫폼 PoC 등록 여부
        """
        score = self._score(input_data)
        gate = self._gate_from_score(score)
        output_doc = self._build_output(input_data, score)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output_doc,
            next_actions=self._next_actions(gate),
        )

    def _score(self, d: dict) -> float:
        score = 0.0
        kpis = d.get("poc_kpis", [])
        # KPI 달성률 (35점)
        if kpis:
            achieved = sum(1 for k in kpis if k.get("actual", 0) >= k.get("target", 1))
            score += 35 * (achieved / len(kpis))
        # 고객 피드백 (20점)
        feedbacks = d.get("customer_feedback", [])
        positive = sum(1 for f in feedbacks if f.get("sentiment", "") == "positive")
        score += 20 * (positive / max(len(feedbacks), 1))
        # 위험저감 조치 (15점)
        score += min(15, len(d.get("risk_mitigations", [])) * 5)
        # PoC 목표 명확성 (10점)
        score += 10 if d.get("poc_objectives") else 0
        # 외부 플랫폼 PoC 등록/완료 (10점) — Catapult·Fraunhofer·TIPS 등
        if d.get("external_poc_registered"):
            score += 10
        elif d.get("venture_client_partner"):
            score += 7
        # 플랫폼 카탈로그 매칭 점수 (10점)
        platforms = match_poc_platforms(
            d.get("tech_type", "software_saas"),
            d.get("target_regions", ["KR"]),
            d.get("trl", 5),
        )
        score += min(10, len(platforms) * 3)
        return round(min(score, 100), 1)

    def _build_output(self, d: dict, score: float) -> dict:
        kpis = d.get("poc_kpis", [])
        kpi_results = []
        for k in kpis:
            target = k.get("target", 1)
            actual = k.get("actual", 0)
            achievement = round(actual / max(target, 0.001) * 100, 1)
            kpi_results.append({
                "name": k.get("name", ""),
                "target": target,
                "actual": actual,
                "achievement_pct": achievement,
                "status": "달성" if actual >= target else "미달성",
            })

        issues = d.get("issues_found", [])
        mitigations = d.get("risk_mitigations", [])

        llm_result = self._llm(
            f"PoC 결과: {kpi_results}\n"
            f"발견 이슈: {issues}\n"
            f"고객 피드백: {d.get('customer_feedback', [])}\n\n"
            "상용화 준비도와 개선 로드맵을 JSON으로:\n"
            '{"commercialization_readiness":"low/medium/high",'
            '"critical_issues":[], "improvement_roadmap":[], "next_poc_needed":true}',
            system="기술실증 전문가. JSON만 반환."
        )
        try:
            import json
            analysis = json.loads(llm_result)
        except Exception:
            analysis = {"commercialization_readiness": "medium", "improvement_roadmap": []}

        # Venture Client 옵션
        vc_partner = d.get("venture_client_partner", "")
        venture_client_plan = {**_VENTURE_CLIENT_TEMPLATE, "partner": vc_partner} if vc_partner else None

        # 외부 PoC 플랫폼 매칭
        matched_platforms = match_poc_platforms(
            d.get("tech_type", "software_saas"),
            d.get("target_regions", ["KR"]),
            d.get("trl", 5),
        )

        return {
            "poc_plan": {
                "tech_name": d.get("tech_name", ""),
                "objectives": d.get("poc_objectives", []),
                "test_environment": d.get("test_environment", ""),
                "duration_months": d.get("poc_duration_months", 0),
                "venture_client": venture_client_plan,
                "external_poc_registered": d.get("external_poc_registered", False),
            },
            "poc_platform_recommendations": {
                "matched_platforms": matched_platforms,
                "selection_criteria": f"tech_type={d.get('tech_type','')}, regions={d.get('target_regions',['KR'])}, TRL={d.get('trl',5)}",
                "total_catalog_size": len(POC_PLATFORM_CATALOG),
                "action": "가장 적합한 플랫폼에 PoC 신청서 제출 → external_poc_registered=true로 업데이트",
            },
            "poc_kpi_report": kpi_results,
            "performance_result": {
                "overall_score": score,
                "kpi_achievement_rate": round(sum(1 for k in kpi_results if k["status"] == "달성") / max(len(kpi_results), 1) * 100, 1),
                "customer_feedback_summary": d.get("customer_feedback", []),
            },
            "risk_mitigation_report": {
                "issues_found": issues,
                "mitigations_applied": mitigations,
                "residual_risks": [i for i in issues if i not in mitigations],
            },
            "commercialization_analysis": analysis,
        }

    def _next_actions(self, gate: str) -> list[str]:
        if gate == "Go":
            return [
                "G8 MRL·ARL 평가로 양산·채택 준비도 확인",
                "PoC 결과를 레퍼런스로 고객사 상용 계약 협의",
                "인증·규제 취득 로드맵 수립",
            ]
        if gate == "Hold":
            return [
                "미달성 KPI 개선 후 추가 PoC 실시",
                "핵심 이슈 해결을 위한 R&D 스프린트",
                "고객 피드백 기반 제품 수정",
            ]
        return [
            "PoC 실패 — 기술 근본 문제 재검토",
            "G2 TRL 평가 재실시 또는 기술 방향 전환",
        ]
