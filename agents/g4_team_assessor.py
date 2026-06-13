"""G4-Team: 팀·실행 역량 평가 — I-Corps / Lean LaunchPad 벤치마킹
창업팀 또는 기술이전팀의 실행 역량을 5차원으로 정량화.
"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# 역할별 가중치 (합계 100)
_ROLE_WEIGHTS = {
    "technical_lead":      25,  # CTO급: 기술 구현 가능성
    "business_lead":       25,  # CEO급: 시장 실행 경험
    "domain_expert":       20,  # 산업 도메인 전문성
    "ip_commercialization": 15, # 기술이전·특허 라이선싱 경험
    "financial_ops":       15,  # 재무·운영 경험 (CFO/COO)
}

# 팀 구성 유형
_TEAM_TYPES = {
    "spinout":       "대학/연구소 → 창업 (연구자 창업)",
    "corporate":     "기업 내부 → 분사 (CVC·전략적 분사)",
    "transfer":      "기술이전 전담팀 (TLO)",
    "startup":       "외부 창업팀 (IP 라이선스 취득)",
    "consortium":    "복수 기관 컨소시엄",
}

# 실행 경험 점수 매핑
_EXP_SCORE = {
    "none":     0,
    "academic": 5,
    "startup_early": 10,
    "startup_growth": 15,
    "enterprise": 12,
    "serial":   20,
}


class TeamAssessor(BaseAgent):
    stage_id   = "G4-Team"
    stage_name = "팀·실행 역량 평가"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          team_type (str): spinout/corporate/transfer/startup/consortium
          members (list of {
            role: str,                          # technical_lead 등
            name: str (optional),
            background: str,                    # 학력·경력 요약
            startup_experience: str,            # none/academic/startup_early/startup_growth/enterprise/serial
            domain_years: int,                  # 해당 산업 경력 연수
            ip_deals_count: int,                # 기술이전·라이선스 딜 수행 경험 건수
            has_network: bool,                  # 핵심 고객·투자자·파트너 네트워크
          }):
          advisors (list of {role, affiliation}): 자문단
          prior_exits (int): 팀 합산 엑시트(M&A·IPO) 경험 수
          full_time_committed (int): 전임(full-time) 인원 수
          total_team_size (int):
          missing_roles (list[str]): 팀에 없는 핵심 역할
        """
        score  = self._score(input_data)
        gate   = self._gate_from_score(score)
        output = self._build_output(input_data, score)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output,
            next_actions=self._next_actions(gate, input_data),
        )

    # ── 점수 산출 ────────────────────────────────────────────────────────────
    def _score(self, d: dict) -> float:
        members = d.get("members", [])
        score   = 0.0

        # 1. 역할 커버리지 (25점)
        covered = {m.get("role") for m in members}
        role_cover_pct = len(covered & set(_ROLE_WEIGHTS)) / len(_ROLE_WEIGHTS)
        score += role_cover_pct * 25

        # 2. 창업/실행 경험 (25점)
        exp_total = sum(_EXP_SCORE.get(m.get("startup_experience", "none"), 0) for m in members)
        score += min(25, exp_total)

        # 3. 도메인 전문성 (20점)
        total_domain_years = sum(m.get("domain_years", 0) for m in members)
        score += min(20, total_domain_years * 1.5)

        # 4. IP·기술이전 경험 (15점)
        ip_deals = sum(m.get("ip_deals_count", 0) for m in members)
        score += min(15, ip_deals * 3)

        # 5. 네트워크·자문·전임 (15점)
        network_count = sum(1 for m in members if m.get("has_network"))
        advisor_count = len(d.get("advisors", []))
        ft_committed  = d.get("full_time_committed", 0)
        prior_exits   = d.get("prior_exits", 0)
        score += min(6, network_count * 2)
        score += min(4, advisor_count)
        score += min(3, ft_committed)
        score += min(2, prior_exits * 2)

        # 페널티: 핵심 역할 공백
        missing = d.get("missing_roles", [])
        if "technical_lead" in missing:
            score -= 15
        if "business_lead" in missing:
            score -= 10

        return round(max(0, min(score, 100)), 1)

    # ── 산출물 ───────────────────────────────────────────────────────────────
    def _build_output(self, d: dict, score: float) -> dict:
        members  = d.get("members", [])
        covered  = {m.get("role") for m in members}
        missing  = d.get("missing_roles", list(set(_ROLE_WEIGHTS) - covered))

        # 5차원 프로파일
        dim_scores = {
            "역할커버리지":    round(len(covered & set(_ROLE_WEIGHTS)) / len(_ROLE_WEIGHTS) * 100),
            "창업_실행경험":   min(100, sum(_EXP_SCORE.get(m.get("startup_experience","none"),0) for m in members) * 5),
            "도메인전문성":    min(100, sum(m.get("domain_years",0) for m in members) * 7),
            "IP_기술이전경험": min(100, sum(m.get("ip_deals_count",0) for m in members) * 20),
            "네트워크_자문":   min(100, (sum(1 for m in members if m.get("has_network")) + len(d.get("advisors",[]))) * 15),
        }

        # LLM: 팀 강점·약점·실행 권고
        llm_text = self._llm(
            f"팀 유형: {_TEAM_TYPES.get(d.get('team_type',''), d.get('team_type',''))}\n"
            f"팀원 수: {d.get('total_team_size', len(members))} (전임: {d.get('full_time_committed',0)})\n"
            f"역할 커버: {sorted(covered)}\n"
            f"공백 역할: {missing}\n"
            f"엑시트 경험: {d.get('prior_exits', 0)}건\n"
            f"자문단: {len(d.get('advisors',[]))}명\n"
            f"5차원 점수: {dim_scores}\n\n"
            "팀 강점 3가지, 약점 2가지, 즉시 보완 액션 3가지를 JSON으로:\n"
            '{"strengths":[],"weaknesses":[],"actions":[]}',
            system="기술사업화 전문가. 팀 역량을 객관적으로 평가하고 실행 가능한 조언을 제공. JSON만 반환."
        )
        try:
            import json
            llm_out = json.loads(llm_text)
        except Exception:
            llm_out = {"strengths": [], "weaknesses": [], "actions": []}

        # 채용 우선순위
        hiring_priority = []
        for role in ["technical_lead", "business_lead", "domain_expert",
                     "ip_commercialization", "financial_ops"]:
            if role in missing or role in d.get("missing_roles", []):
                hiring_priority.append({
                    "role": role,
                    "urgency": "즉시" if role in ("technical_lead", "business_lead") else "3개월 내",
                    "hiring_channel": "기술이전 네트워크·창업 생태계·헤드헌터",
                })

        return {
            "team_assessment": {
                "team_type": _TEAM_TYPES.get(d.get("team_type",""), d.get("team_type","")),
                "total_size": d.get("total_team_size", len(members)),
                "full_time":  d.get("full_time_committed", 0),
                "prior_exits": d.get("prior_exits", 0),
                "advisors":   len(d.get("advisors", [])),
                "team_score": score,
            },
            "five_dimension_profile": dim_scores,
            "role_coverage": {
                "covered": sorted(covered & set(_ROLE_WEIGHTS)),
                "missing": missing,
            },
            "strengths":          llm_out.get("strengths", []),
            "weaknesses":         llm_out.get("weaknesses", []),
            "recommended_actions": llm_out.get("actions", []),
            "hiring_priority":    hiring_priority,
            "execution_risk": (
                "높음" if score < 40 else
                "중간" if score < 65 else
                "낮음"
            ),
        }

    def _next_actions(self, gate: str, d: dict) -> list[str]:
        missing = d.get("missing_roles", [])
        actions = []
        if gate == "Go":
            actions.append("팀 역량 강화 계획 수립 후 G5 사업모델 설계 진행")
            actions.append("부족 자문단 영역 3개월 내 보강")
        elif gate == "Hold":
            if "business_lead" in missing:
                actions.append("시장 실행 경험 보유자 즉시 영입 또는 자문 계약")
            if "technical_lead" in missing:
                actions.append("핵심 기술 구현 담당자 확보 (공동창업자 또는 CTO 계약직)")
            actions.append("전임 인원 최소 2명 확보 후 재평가")
        else:
            actions.append("팀 전면 재구성: 기술+사업 핵심 2인 이상 확보 필수")
            actions.append("TLO·창업지원단·AC 프로그램을 통한 팀빌딩 지원 요청")
        return actions
