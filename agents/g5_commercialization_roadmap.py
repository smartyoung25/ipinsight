"""G5-CR: 사업화 로드맵 자동 생성
KIAT·KEIT 협약 표준 양식 + DOE Commercialization Plan 구조 기반.
G5 BMDesigner 완료 시 자동 트리거되거나 독립 실행 가능.

산출물 구조:
  Phase 1 — 기술검증 (TRL 4→6)
  Phase 2 — 시장진입 (TRL 6→8)
  Phase 3 — 스케일업 (TRL 8→9+)
  + 자금조달 계획 / KPI 목표 / 리스크 레지스터 / 추진체계
"""
from __future__ import annotations
import json
from datetime import date
from .base_agent import BaseAgent, StageResult

# 정부 비희석 자금 프로그램 (국내+해외)
_GOV_FUNDING_PROGRAMS = {
    "TIPS":         {"amount_krw": 500_000_000,  "type": "비희석",  "eligibility": "TRL 4+, 민간투자 연계"},
    "KEIT_R&D":     {"amount_krw": 1_000_000_000,"type": "비희석",  "eligibility": "중소·중견기업"},
    "창업도약패키지":{"amount_krw": 300_000_000,  "type": "비희석",  "eligibility": "3~7년차 스타트업"},
    "SBIR_Phase1":  {"amount_usd": 275_000,      "type": "비희석",  "eligibility": "미국 법인 or 합작"},
    "EIC_Accelerator":{"amount_eur": 2_500_000,  "type": "희석혼합","eligibility": "EU 또는 글로벌"},
    "규제샌드박스":  {"amount_krw": 0,            "type": "규제완화","eligibility": "신기술·신서비스"},
}

# TRL 단계별 표준 마일스톤 (INNOPOLIS TLO 기준)
_TRL_PHASE_MAP = {
    (1, 3): "기초연구",
    (4, 5): "기술검증",
    (6, 7): "파일럿·시범",
    (8, 9): "상용화",
}

# KIAT 협약 필수 지표
_MANDATORY_KPIS = [
    "기술이전 건수",
    "사업화 매출액 (억원)",
    "고용 창출 (명)",
    "투자 유치 (억원)",
    "특허 등록 건수",
]


def _quarter_label(base_year: int, offset_months: int) -> str:
    total_month = offset_months
    yr = base_year + total_month // 12
    q = (total_month % 12) // 3 + 1
    return f"{yr} Q{q}"


class CommercializationRoadmap(BaseAgent):
    stage_id   = "G5-CR"
    stage_name = "사업화 로드맵 자동 생성"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          tech_name (str)
          tech_id (str)
          current_trl (int): 현재 TRL (1~9)
          target_trl (int): 목표 TRL, 기본 9
          base_year (int): 로드맵 시작 연도, 기본 올해
          -- G5 BMDesigner 출력 연동 (선택) --
          bm_output (dict): BMDesigner.assess().output_doc
          -- 직접 입력 (선택) --
          revenue_model (list[str]): 수익모델
          tam_usd (float): 전체 시장 규모
          som_usd (float): 3년 실현 가능 시장
          gross_margin_pct (float): 매출총이익률
          loi_count (int): 확보 LoI 수
          poc_requests (int): PoC 요청 수
          team_size (int): 현재 팀 규모
          target_market (str): 목표 시장
          apply_programs (list[str]): 신청할 정부 프로그램
          industry_sector (str): 산업 도메인
        """
        score   = self._score(input_data)
        gate    = self._gate_from_score(score)
        output  = self._build_output(input_data, score)
        return StageResult(
            stage      = self.stage_id,
            score      = score,
            gate       = gate,
            output_doc = output,
            next_actions = self._next_actions(gate, input_data),
        )

    def _score(self, d: dict) -> float:
        score = 0.0
        # TRL 명확성 (20점)
        trl = d.get("current_trl", 0)
        if trl >= 6:   score += 20
        elif trl >= 4: score += 12
        elif trl >= 2: score += 6

        # 시장 근거 (20점)
        bm = d.get("bm_output", {})
        tam = d.get("tam_usd") or bm.get("competitive_landscape", {}).get("market_sizing", {}).get("tam_usd", 0)
        if tam >= 1_000_000_000: score += 20
        elif tam >= 100_000_000: score += 12
        elif tam > 0:            score += 6

        # LoI·PoC 실증 (20점)
        loi = d.get("loi_count") or bm.get("bm_score", 0) // 10
        poc = d.get("poc_requests", 0)
        score += min(20, loi * 5 + poc * 3)

        # 수익모델 구체성 (20점)
        rm = d.get("revenue_model") or bm.get("business_model_canvas", {}).get("revenue_streams", {})
        if rm: score += min(20, len(rm) * 5)

        # 자금조달 계획 (10점)
        programs = d.get("apply_programs", [])
        if programs: score += min(10, len(programs) * 3)
        elif trl >= 4: score += 4  # TIPS 기본 충족

        # 팀 준비도 (10점)
        ts = d.get("team_size", 0)
        if ts >= 5:   score += 10
        elif ts >= 3: score += 6
        elif ts >= 1: score += 3

        return round(min(score, 100), 1)

    def _build_output(self, d: dict, score: float) -> dict:
        bm   = d.get("bm_output", {})
        trl  = d.get("current_trl", 3)
        ttrl = d.get("target_trl", 9)
        year = d.get("base_year", date.today().year)
        name = d.get("tech_name", d.get("tech_id", "기술명 미입력"))

        # 시장 데이터 — BM output 또는 직접 입력 우선
        cmp  = bm.get("competitive_landscape", {})
        sizing = cmp.get("market_sizing", {})
        tam  = d.get("tam_usd") or sizing.get("tam_usd", 0)
        som  = d.get("som_usd") or sizing.get("som_usd", 0)
        gm   = d.get("gross_margin_pct") or bm.get("unit_economics", {}).get("gross_margin_pct", 60)

        # Phase 설계
        phases = self._build_phases(trl, ttrl, year, d, bm)

        # 자금조달 계획
        funding = self._build_funding_plan(trl, d)

        # KPI 목표 (연도별)
        kpis = self._build_kpi_targets(d, bm, year, som, gm)

        # 리스크 레지스터
        risks = self._build_risk_register(d, trl)

        # LLM 보강 — 산업별 특수 사항
        llm_ctx = self._llm(
            f"기술: {name}, TRL {trl}→{ttrl}, 시장규모 ${tam:,.0f}\n"
            f"산업: {d.get('industry_sector','')}, 수익모델: {d.get('revenue_model',bm.get('business_model_canvas',{}).get('revenue_streams',{}))}\n"
            f"목표시장: {d.get('target_market', bm.get('partnership_strategy',{}).get('target_markets',['']))}\n\n"
            "이 기술의 사업화에서 가장 중요한 병목 2가지와 핵심 성공요인(CSF) 3가지를 JSON으로:\n"
            '{"bottlenecks":[],"critical_success_factors":[],"differentiation_focus":""}',
            system="기술사업화 전략 전문가. 해당 산업에 특화된 실무적 JSON만 반환."
        )
        try:
            llm_out = json.loads(llm_ctx)
        except Exception:
            llm_out = {"bottlenecks": [], "critical_success_factors": [], "differentiation_focus": llm_ctx}

        return {
            "document_type": "사업화 로드맵 (Commercialization Roadmap)",
            "document_version": "v1.0",
            "generated_date": date.today().isoformat(),
            "tech_name": name,
            "tech_id": d.get("tech_id", ""),
            "trl_progression": {"current": trl, "target": ttrl},
            "roadmap_summary": {
                "total_phases": len(phases),
                "total_duration_months": sum(p["duration_months"] for p in phases),
                "total_budget_krw": sum(p.get("budget_krw", 0) for p in phases),
                "target_year1_revenue_krw": kpis.get("year1", {}).get("revenue_krw", 0),
                "target_year3_revenue_krw": kpis.get("year3", {}).get("revenue_krw", 0),
            },
            "phases": phases,
            "funding_plan": funding,
            "kpi_targets": kpis,
            "risk_register": risks,
            "strategic_insights": llm_out,
            "government_programs": self._match_programs(trl, d),
            "roadmap_score": score,
        }

    def _build_phases(self, trl: int, ttrl: int, year: int, d: dict, bm: dict) -> list[dict]:
        loi = d.get("loi_count", 0)
        bm_canvas = bm.get("business_model_canvas", {})
        rm = d.get("revenue_model") or list(bm_canvas.get("revenue_streams", {}).keys())

        phases = []

        if trl < 6:
            phases.append({
                "phase_no": 1,
                "phase_name": "Phase 1 — 기술검증 (Technology Validation)",
                "trl_start": trl, "trl_end": min(6, ttrl),
                "period_start": f"{year} Q1",
                "duration_months": 9,
                "budget_krw": 200_000_000,
                "key_activities": [
                    "PoC 설계 및 파일럿 환경 구축",
                    f"목표 고객 인터뷰 30건 이상 (현재 LoI {loi}건)",
                    "기술 성능 지표 달성 검증",
                    "핵심 특허 청구항 보강",
                    "TIPS 또는 KEIT R&D 과제 신청",
                ],
                "milestones": [
                    {"quarter": _quarter_label(year, 3),  "milestone": "PoC 완료 + 성능 목표 달성"},
                    {"quarter": _quarter_label(year, 6),  "milestone": f"LoI {max(loi+1, 3)}건 확보"},
                    {"quarter": _quarter_label(year, 9),  "milestone": "TRL 6 달성 + 파일럿 파트너 선정"},
                ],
                "required_resources": {
                    "team": ["개발·연구 2~3명", "기술영업 1명"],
                    "infra": ["실험·파일럿 환경", "클라우드 인프라"],
                    "external": ["파일럿 고객 1~2개사", "기술멘토"],
                },
                "gate_criteria": "TRL 6 달성 + 파일럿 고객 2개사 이상 + 정부과제 선정",
            })

        if ttrl >= 7:
            phases.append({
                "phase_no": len(phases) + 1,
                "phase_name": "Phase 2 — 시장진입 (Market Entry)",
                "trl_start": 6, "trl_end": min(8, ttrl),
                "period_start": _quarter_label(year, phases[-1]["duration_months"] if phases else 0),
                "duration_months": 12,
                "budget_krw": 500_000_000,
                "key_activities": [
                    "상업화 버전 제품·서비스 완성",
                    "파일럿 3개사 → 초기 고객 10개사 전환",
                    f"수익모델 검증: {', '.join(rm[:2]) if rm else '라이선싱/SaaS'}",
                    "파트너십·채널 계약 체결",
                    "Seed 또는 Series A 투자 유치",
                ],
                "milestones": [
                    {"quarter": _quarter_label(year, (phases[-1]["duration_months"] if phases else 0) + 3),
                     "milestone": "첫 상용 계약 체결 (ARR $50K+)"},
                    {"quarter": _quarter_label(year, (phases[-1]["duration_months"] if phases else 0) + 6),
                     "milestone": "고객 5개사 + Seed 투자 유치"},
                    {"quarter": _quarter_label(year, (phases[-1]["duration_months"] if phases else 0) + 12),
                     "milestone": "TRL 8 달성 + ARR $200K+ + 고객 10개사"},
                ],
                "required_resources": {
                    "team": ["개발 3~4명", "영업·마케팅 2명", "고객성공(CS) 1명"],
                    "infra": ["운영 서버·클라우드", "CRM 시스템"],
                    "external": ["채널 파트너 1~2개사", "투자자 네트워크"],
                },
                "gate_criteria": "ARR $200K+ + 고객 10개사 + Series A 투자 유치",
            })

        if ttrl >= 9:
            phases.append({
                "phase_no": len(phases) + 1,
                "phase_name": "Phase 3 — 스케일업 (Scale-Up)",
                "trl_start": 8, "trl_end": 9,
                "period_start": _quarter_label(year, sum(p["duration_months"] for p in phases)),
                "duration_months": 18,
                "budget_krw": 2_000_000_000,
                "key_activities": [
                    "국내 시장 30개사+ 확장",
                    "해외 1~2개국 진출 (KOTRA·EEN 채널)",
                    "기술이전·라이선싱 계약 병행",
                    "Series B 또는 전략적 M&A 검토",
                    "글로벌 인증·규제 취득",
                ],
                "milestones": [
                    {"quarter": _quarter_label(year, sum(p["duration_months"] for p in phases) + 6),
                     "milestone": "ARR $1M+ + 고객 30개사"},
                    {"quarter": _quarter_label(year, sum(p["duration_months"] for p in phases) + 12),
                     "milestone": "해외 법인 or 파트너십 1개국"},
                    {"quarter": _quarter_label(year, sum(p["duration_months"] for p in phases) + 18),
                     "milestone": "TRL 9 달성 + ARR $5M+ + 엑시트 옵션 확보"},
                ],
                "required_resources": {
                    "team": ["전 부문 20명+", "글로벌 영업 2명", "법무·IR 1명"],
                    "infra": ["글로벌 인프라", "ERP·데이터 플랫폼"],
                    "external": ["글로벌 파트너·SI", "증권사·M&A 어드바이저"],
                },
                "gate_criteria": "ARR $5M+ + 고객 30개사 + 글로벌 레퍼런스 1건",
            })

        return phases

    def _build_funding_plan(self, trl: int, d: dict) -> list[dict]:
        year = d.get("base_year", date.today().year)
        plan = []
        if trl <= 5:
            plan.append({"stage": "정부 R&D (TIPS/KEIT)", "timing": f"{year} Q1~Q3",
                          "amount_krw": 500_000_000, "dilution_pct": 0, "type": "비희석",
                          "action": "TIPS 프로그램 신청 — 민간 추천사 발굴 선행"})
        if trl <= 6:
            plan.append({"stage": "Seed 라운드", "timing": _quarter_label(year, 9),
                          "amount_krw": 2_000_000_000, "dilution_pct": 15, "type": "지분투자",
                          "action": "IR 덱 + 기술가치평가서 (G6) 선행 준비"})
        plan.append({"stage": "Series A", "timing": _quarter_label(year, 18),
                      "amount_krw": 10_000_000_000, "dilution_pct": 20, "type": "지분투자",
                      "action": "ARR $200K+ 달성 후 CVC·VC 미팅"})
        plan.append({"stage": "Series B / 전략적 투자", "timing": _quarter_label(year, 30),
                      "amount_krw": 50_000_000_000, "dilution_pct": 15, "type": "지분+전략",
                      "action": "글로벌 전략적 파트너 탐색 병행"})
        return plan

    def _build_kpi_targets(self, d: dict, bm: dict, year: int, som_usd: float, gm_pct: float) -> dict:
        som_krw = som_usd * 1_350  # USD→KRW 환산
        return {
            "year1": {
                "period": f"{year}~{year+1}",
                "revenue_krw": int(som_krw * 0.01),
                "customers": 10,
                "loi_or_contract": max(d.get("loi_count", 0) + 2, 3),
                "trl_target": min(d.get("current_trl", 3) + 2, 9),
                "patent_filings": 2,
                "team_headcount": max(d.get("team_size", 2) + 2, 5),
                "government_funding_krw": 500_000_000,
            },
            "year2": {
                "period": f"{year+1}~{year+2}",
                "revenue_krw": int(som_krw * 0.05),
                "customers": 30,
                "arr_usd": int(som_usd * 0.02),
                "gross_margin_pct": gm_pct,
                "investment_raised_krw": 2_000_000_000,
                "team_headcount": 15,
            },
            "year3": {
                "period": f"{year+2}~{year+3}",
                "revenue_krw": int(som_krw * 0.15),
                "customers": 80,
                "arr_usd": int(som_usd * 0.06),
                "global_countries": 2,
                "investment_raised_krw": 10_000_000_000,
                "team_headcount": 30,
            },
            "mandatory_kpis_kiat": {k: "목표치 협약 시 확정" for k in _MANDATORY_KPIS},
        }

    def _build_risk_register(self, d: dict, trl: int) -> list[dict]:
        risks = [
            {"id": "R1", "category": "기술", "risk": "TRL 달성 지연",
             "probability": "중", "impact": "상",
             "mitigation": "격주 기술 리뷰 + 대안 방법론 사전 준비", "owner": "CTO"},
            {"id": "R2", "category": "시장", "risk": "고객 도입 속도 저조",
             "probability": "중", "impact": "상",
             "mitigation": "얼리어답터 무료 파일럿 + 레퍼런스 생성 우선", "owner": "CSO"},
            {"id": "R3", "category": "자금", "risk": "투자 유치 실패 or 지연",
             "probability": "중", "impact": "상",
             "mitigation": "정부 비희석 자금 병행 + 런웨이 18개월 유지", "owner": "CEO"},
            {"id": "R4", "category": "IP", "risk": "경쟁사 회피설계 or 유사특허",
             "probability": "저", "impact": "상",
             "mitigation": "조기 특허 출원 + FTO 분석 (G1) 선행", "owner": "IP팀"},
            {"id": "R5", "category": "규제", "risk": "인증·허가 취득 지연",
             "probability": "중", "impact": "중",
             "mitigation": "규제 전문가 선임 + 규제 샌드박스 신청 병행", "owner": "규제팀"},
            {"id": "R6", "category": "팀", "risk": "핵심 인력 이탈",
             "probability": "중", "impact": "중",
             "mitigation": "스톡옵션 4년 베스팅 + 조직문화 투자", "owner": "CEO"},
        ]
        if trl < 5:
            risks.insert(0, {
                "id": "R0", "category": "기술성숙도", "risk": "TRL 낮음 — 상용화까지 시간 과소평가",
                "probability": "상", "impact": "상",
                "mitigation": f"현재 TRL {trl}: Phase 1 기술검증에 최소 9개월 예비 확보", "owner": "CTO",
            })
        return risks

    def _match_programs(self, trl: int, d: dict) -> list[dict]:
        matched = []
        sector = d.get("industry_sector", "").lower()
        if trl >= 3:
            matched.append({**_GOV_FUNDING_PROGRAMS["TIPS"], "program": "TIPS", "priority": 1,
                             "note": "민간 추천사(AC·VC) 선정 후 신청 가능"})
            matched.append({**_GOV_FUNDING_PROGRAMS["KEIT_R&D"], "program": "KEIT R&D", "priority": 2,
                             "note": "과제 공고 매 상반기·하반기"})
        if "bio" in sector or "의료" in sector or "헬스" in sector:
            matched.append({**_GOV_FUNDING_PROGRAMS["규제샌드박스"], "program": "규제샌드박스",
                             "priority": 2, "note": "의료기기·디지털헬스 적용 가능"})
        if d.get("target_market", "").lower() in ("us", "미국", "global", "글로벌"):
            matched.append({**_GOV_FUNDING_PROGRAMS["SBIR_Phase1"], "program": "SBIR Phase I (미국)",
                             "priority": 3, "note": "미국 법인 설립 또는 JV 필요"})
        if d.get("apply_programs"):
            for p in d["apply_programs"]:
                if p in _GOV_FUNDING_PROGRAMS and not any(m["program"] == p for m in matched):
                    matched.append({**_GOV_FUNDING_PROGRAMS[p], "program": p, "priority": 3,
                                    "note": "사용자 지정 프로그램"})
        return matched

    def _next_actions(self, gate: str, d: dict) -> list[str]:
        trl = d.get("current_trl", 3)
        loi = d.get("loi_count", 0)
        actions = []
        if gate == "Go":
            actions = [
                "로드맵 Phase 1 착수: PoC 설계 미팅 일정 확정",
                "TIPS 추천사(AC/VC) 발굴 — 현재 LoI 기반 추진력 활용",
                f"G6 기술가치평가 의뢰 (현재 TRL {trl} 기준 초기 평가)",
                "SMK(사업화시장키트) 최종화 후 잠재 파트너 배포",
            ]
        elif gate == "Hold":
            if loi == 0:
                actions.append("LoI 최소 1건 확보 — 파일럿 고객 무료 도입 제안")
            if trl < 5:
                actions.append(f"TRL {trl}→5 기술검증 로드맵 구체화 (6개월 스프린트)")
            actions.append("시장 규모(TAM/SOM) 데이터 보강 후 로드맵 재생성")
        else:
            actions = [
                "기술 방향 재검토 또는 Pivot — G0 수요조사서 재실시",
                "최소 TRL 4 달성 후 로드맵 재생성",
            ]
        return actions
