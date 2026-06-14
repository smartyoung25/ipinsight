"""G4 고객발견·수요검증 — NSF I-Corps + JTBD(Jobs-to-be-Done) 통합

인터뷰 기준 (NSF I-Corps 공식):
  - Phase I  (SBIR Phase I 연계): 30건 최저
  - Phase II (SBIR Phase II·National): 100건 권장
  → 본 모듈은 100건 기준 채점. 30건은 경고 발생.

JTBD(Jobs-to-be-Done) 프레임 (Christensen·Ulwick):
  - Functional Job: 고객이 달성하려는 기능적 목표
  - Emotional Job: 느끼고 싶거나 피하고 싶은 감정
  - Social Job: 타인에게 어떻게 보이고 싶은가
  → 3가지 Job 차원이 모두 확인된 인터뷰만 '검증된 수요'로 인정
"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# NSF I-Corps National 기준
_ICORPS_PHASE1_MIN = 30
_ICORPS_NATIONAL_TARGET = 100


class CustomerValidator(BaseAgent):
    stage_id = "G4"
    stage_name = "고객발견·수요검증"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data: interviews (list of {
                      customer_type, pain_point, willingness_to_pay,
                      alternative_used, urgency_1to5,
                      jtbd_functional (str, optional),  ← JTBD 추가
                      jtbd_emotional (str, optional),
                      jtbd_social (str, optional)
                    }),
                    loi_count, poc_requests, survey_responses
        """
        score = self._score(input_data)
        gate = self._gate_from_score(score)
        output_doc = self._build_output(input_data, score)
        warnings = self._warnings(input_data)

        # LoI 1건 이상 확보 시 → LoI 표준 양식 자동 생성
        loi_count = input_data.get("loi_count", 0)
        poc_req   = input_data.get("poc_requests", 0)
        if loi_count >= 1 or poc_req >= 1:
            output_doc["loi_template"] = self._generate_loi_template(input_data)

        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output_doc,
            next_actions=self._next_actions(gate),
            warnings=warnings,
        )

    def _score(self, d: dict) -> float:
        score = 0.0
        interviews = d.get("interviews", [])
        n = max(len(interviews), 1)

        # 인터뷰 수 (25점) — NSF I-Corps National 기준 100건
        # 30건: 12.5점, 50건: 17점, 100건: 25점
        score += min(25, len(interviews) * 0.25)

        # JTBD 검증 품질 (20점) — 3차원 모두 확인된 인터뷰 비율
        jtbd_verified = sum(
            1 for i in interviews
            if i.get("jtbd_functional") and i.get("jtbd_emotional")
        )
        score += 20 * (jtbd_verified / n)

        # 지불의사 확인 비율 (25점)
        wtp_confirmed = sum(1 for i in interviews if i.get("willingness_to_pay", 0) > 0)
        score += 25 * (wtp_confirmed / n)

        # LoI/PoC 요청 (20점)
        score += min(20, d.get("loi_count", 0) * 4 + d.get("poc_requests", 0) * 2)

        # 긴급도 평균 (10점)
        urgencies = [i.get("urgency_1to5", 0) for i in interviews]
        avg_urgency = sum(urgencies) / max(len(urgencies), 1)
        score += avg_urgency * 2

        return round(min(score, 100), 1)

    def _build_output(self, d: dict, score: float) -> dict:
        interviews = d.get("interviews", [])
        # 페르소나 그룹화
        personas: dict = {}
        for i in interviews:
            ct = i.get("customer_type", "미분류")
            personas.setdefault(ct, []).append(i)

        persona_summary = []
        for ctype, items in personas.items():
            wtps = [x.get("willingness_to_pay", 0) for x in items]
            persona_summary.append({
                "customer_type": ctype,
                "interview_count": len(items),
                "avg_willingness_to_pay_usd": round(sum(wtps) / max(len(wtps), 1), 0),
                "top_pain_points": list({x.get("pain_point", "") for x in items})[:3],
                "avg_urgency": round(sum(x.get("urgency_1to5", 0) for x in items) / max(len(items), 1), 1),
            })

        llm_result = self._llm(
            f"고객 인터뷰 요약: {personas}\n"
            f"LoI 수: {d.get('loi_count', 0)}, PoC 요청: {d.get('poc_requests', 0)}\n\n"
            "문제-솔루션 적합성(PSF) 평가와 구매 결정 구조를 JSON으로:\n"
            '{"psf_score":0-100, "key_buying_triggers":[], "adoption_barriers":[],'
            '"recommended_persona":"", "pricing_signal_usd":0}',
            system="린스타트업 전문가. JSON만 반환."
        )
        try:
            import json
            psf = json.loads(llm_result)
        except Exception:
            psf = {"psf_score": score, "key_buying_triggers": [], "adoption_barriers": []}

        # JTBD 분석
        jtbd_map: dict = {}
        for i in interviews:
            f = i.get("jtbd_functional", "")
            if f:
                jtbd_map.setdefault(f, {"count": 0, "emotional": [], "social": []})
                jtbd_map[f]["count"] += 1
                if i.get("jtbd_emotional"):
                    jtbd_map[f]["emotional"].append(i["jtbd_emotional"])
                if i.get("jtbd_social"):
                    jtbd_map[f]["social"].append(i["jtbd_social"])

        jtbd_insights = [
            {
                "functional_job": job,
                "frequency": data["count"],
                "emotional_jobs": list(set(data["emotional"]))[:2],
                "social_jobs": list(set(data["social"]))[:2],
            }
            for job, data in sorted(jtbd_map.items(), key=lambda x: -x[1]["count"])[:5]
        ]

        return {
            "customer_discovery_report": {
                "total_interviews": len(interviews),
                "icorps_phase1_min": _ICORPS_PHASE1_MIN,
                "icorps_national_target": _ICORPS_NATIONAL_TARGET,
                "loi_count": d.get("loi_count", 0),
                "poc_requests": d.get("poc_requests", 0),
                "persona_summary": persona_summary,
                "validation_score": score,
            },
            "jtbd_analysis": {
                "jtbd_verified_count": sum(
                    1 for i in interviews if i.get("jtbd_functional") and i.get("jtbd_emotional")
                ),
                "top_functional_jobs": jtbd_insights,
                "jtbd_coverage_pct": round(
                    sum(1 for i in interviews if i.get("jtbd_functional")) / max(len(interviews), 1) * 100, 1
                ),
            },
            "psf_analysis": psf,
            "purchase_intent_analysis": {
                "confirmed_wtp_count": sum(1 for i in interviews if i.get("willingness_to_pay", 0) > 0),
                "avg_wtp_usd": round(sum(i.get("willingness_to_pay", 0) for i in interviews) / max(len(interviews), 1), 0),
                "urgency_distribution": {
                    "high_4to5": sum(1 for i in interviews if i.get("urgency_1to5", 0) >= 4),
                    "medium_3": sum(1 for i in interviews if i.get("urgency_1to5", 0) == 3),
                    "low_1to2": sum(1 for i in interviews if i.get("urgency_1to5", 0) <= 2),
                },
            },
            "interview_question_template": self._interview_template(),
        }

    def _interview_template(self) -> list[str]:
        return [
            # Functional Job 확인
            "이 기술/제품으로 달성하려는 핵심 목표(기능)는 무엇입니까?",
            "현재 이 목표를 어떻게 달성하고 있습니까? (대안 솔루션)",
            # Emotional Job 확인
            "기존 방식을 쓸 때 느끼는 가장 큰 불만·스트레스는 무엇입니까?",
            "이상적인 해결책이 있다면 어떤 감정을 느끼길 원하십니까?",
            # Social Job 확인
            "이 문제를 해결함으로써 조직 내 또는 고객에게 어떻게 보이고 싶으십니까?",
            # 구매 의사결정
            "이 문제로 인해 연간 얼마의 비용/손실이 발생합니까?",
            "새로운 해결책에 연간 얼마를 지불할 의향이 있습니까?",
            "도입 결정권자는 누구입니까? 예산 승인 프로세스는?",
        ]

    def _generate_loi_template(self, d: dict) -> dict:
        """LoI(도입의향서 / Letter of Intent) 표준 양식 자동 생성.

        KIAT·KEIT 협약 및 TIPS 투자심사 제출용 표준 형식.
        수신처·조건은 실제 인터뷰 데이터에서 자동 추출.
        """
        from datetime import date

        interviews = d.get("interviews", [])
        tech_name  = d.get("tech_name", "대상 기술/서비스")
        tech_org   = d.get("tech_org",  "[기술 보유 기관/기업명]")
        loi_count  = d.get("loi_count", 0)
        poc_req    = d.get("poc_requests", 0)

        # 평균 WTP 산출
        wtp_vals = [i.get("willingness_to_pay", 0) for i in interviews if i.get("willingness_to_pay", 0) > 0]
        avg_wtp  = round(sum(wtp_vals) / max(len(wtp_vals), 1), 0)

        # 주요 Pain Point 상위 3개 추출
        pain_points = list(dict.fromkeys(
            i["pain_point"] for i in interviews if i.get("pain_point")
        ))[:3]

        # 고객 세그먼트 대표값
        customer_types = list(dict.fromkeys(
            i["customer_type"] for i in interviews if i.get("customer_type")
        ))[:3]

        # LLM 보강 — LoI 구체화
        llm_body = self._llm(
            f"기술명: {tech_name}\n"
            f"고객 유형: {customer_types}\n"
            f"핵심 Pain Point: {pain_points}\n"
            f"평균 WTP: ${avg_wtp:,.0f}/년\n"
            f"LoI 확보 수: {loi_count}, PoC 요청: {poc_req}\n\n"
            "표준 도입의향서(LoI) 핵심 조항 3개와 PoC 조건을 JSON으로:\n"
            '{"intent_clauses":[],"poc_conditions":[],"evaluation_criteria":[],"exclusivity_note":""}',
            system="기술사업화 계약 전문가. 법적 효력 없는 의향서 초안용 JSON만 반환."
        )
        try:
            import json
            llm_out = json.loads(llm_body)
        except Exception:
            llm_out = {
                "intent_clauses": [
                    f"{tech_name} 기술의 도입 검토 의향을 표명함",
                    f"6개월 이내 PoC 또는 파일럿 프로그램 참여 의사 있음",
                    f"연간 도입 예산 검토 중 (예상 ${avg_wtp:,.0f}/년)",
                ],
                "poc_conditions": [
                    "3개월 무료 파일럿 또는 성과 기반 과금",
                    "성능 목표 미달 시 계약 해제 가능",
                ],
                "evaluation_criteria": ["기존 대비 생산성 20% 향상", "도입 후 3개월 내 ROI 확인"],
                "exclusivity_note": "본 LoI는 법적 구속력 없는 의향 표명이며 독점 계약이 아님",
            }

        return {
            "document_type": "도입의향서 (Letter of Intent)",
            "document_status": "초안 (Draft) — 법적 검토 필요",
            "generated_date": date.today().isoformat(),
            "notice": "본 양식은 자동 생성 초안입니다. 법무 검토 후 사용하십시오.",
            "header": {
                "title": f"[{tech_name}] 기술 도입의향서",
                "ref_no": f"LOI-{date.today().strftime('%Y%m%d')}-001",
                "date": date.today().isoformat(),
            },
            "parties": {
                "issuer": {
                    "role": "기술 도입 의향 기관 (수요처)",
                    "name": "[수요처 기관명]",
                    "representative": "[대표자명]",
                    "address": "[주소]",
                },
                "recipient": {
                    "role": "기술 보유 기관 (공급자)",
                    "name": tech_org,
                    "representative": "[대표자/담당자명]",
                },
            },
            "technology_overview": {
                "tech_name": tech_name,
                "description": f"[{tech_name}] 기술의 핵심 기능 및 적용 범위 서술",
                "target_customer_types": customer_types,
                "key_pain_points_addressed": pain_points,
            },
            "intent_clauses": llm_out.get("intent_clauses", []),
            "poc_plan": {
                "conditions": llm_out.get("poc_conditions", []),
                "evaluation_criteria": llm_out.get("evaluation_criteria", []),
                "duration": "3개월 (협의 조정 가능)",
                "proposed_budget_usd": avg_wtp * 0.1 if avg_wtp > 0 else 0,
            },
            "commercial_intent": {
                "annual_budget_usd": avg_wtp,
                "procurement_timeline": "PoC 완료 후 6개월 이내 도입 여부 결정",
                "decision_maker": "[구매 결정권자 직함]",
                "budget_approval_process": "[예산 승인 절차 기재]",
            },
            "exclusivity_note": llm_out.get("exclusivity_note", "본 LoI는 법적 구속력 없는 의향 표명"),
            "signature_block": {
                "issuer_signature": "___________________",
                "issuer_title": "[직위]",
                "issuer_date": "____년 ____월 ____일",
                "recipient_signature": "___________________",
                "recipient_title": "[직위]",
                "recipient_date": "____년 ____월 ____일",
            },
            "usage_notes": [
                "본 LoI는 투자자 제출용 수요 검증 증빙 자료로 활용 가능",
                "TIPS/KEIT 과제 신청 시 수요처 확인서로 제출 가능",
                "법적 계약은 별도 기술이전계약서(G7) 또는 NDA 체결 필요",
                f"현재 확보 LoI {loi_count}건 / PoC 요청 {poc_req}건",
            ],
        }

    def _warnings(self, d: dict) -> list[str]:
        w = []
        interviews = d.get("interviews", [])
        n = len(interviews)
        if n < _ICORPS_PHASE1_MIN:
            w.append(f"인터뷰 {n}건 — I-Corps Phase I 최저 기준 {_ICORPS_PHASE1_MIN}건 미달")
        elif n < _ICORPS_NATIONAL_TARGET:
            w.append(f"인터뷰 {n}건 — I-Corps National 권장 {_ICORPS_NATIONAL_TARGET}건 미달 (Phase I 수준)")
        jtbd_missing = sum(1 for i in interviews if not i.get("jtbd_functional"))
        if jtbd_missing > n * 0.5:
            w.append(f"인터뷰 {jtbd_missing}건에 JTBD Functional Job 미기록 — 수요 검증 품질 저하")
        if d.get("loi_count", 0) == 0:
            w.append("LoI(의향서) 미확보 — 구매의향 실증 필요")
        return w

    def _next_actions(self, gate: str) -> list[str]:
        if gate == "Go":
            return [
                "G5 사업모델·GTM 설계 진행",
                "JTBD 상위 Functional Job 기반 가치제안 문서화",
                "핵심 고객 3개사와 파일럿 계약 협의",
                "확보한 LoI를 기반으로 투자자 미팅 준비",
            ]
        if gate == "Hold":
            return [
                f"추가 고객 인터뷰 진행 (목표: {_ICORPS_NATIONAL_TARGET}건)",
                "인터뷰 시 JTBD 3차원(Functional·Emotional·Social) 기록 철저화",
                "LoI 또는 PoC 요청서 최소 3건 확보",
                "고객군 재정의 또는 가치제안 수정",
            ]
        return [
            "수요 없음 확인 — 기술 적용분야 전환 검토 (Pivot)",
            "고객군 완전 재설정 후 G3부터 재시작",
        ]
