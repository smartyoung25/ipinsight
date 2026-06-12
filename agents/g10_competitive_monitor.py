"""G10-Competitive 경쟁대응 전략 — 특허 모니터링·무효화·회피설계 로드맵"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# 경쟁대응 액션 유형
_RESPONSE_ACTIONS = {
    "design_around": {
        "name": "회피설계 (Design-Around)",
        "desc": "경쟁사 특허 청구항을 분석하여 침해하지 않는 대안 기술 개발",
        "cost": "중간 (R&D 비용)",
        "timeline": "3~12개월",
        "when": "경쟁사 특허 핵심이 자사 제품과 충돌 시",
    },
    "invalidity": {
        "name": "무효심판 (Inter Partes Review / 無效審判)",
        "desc": "경쟁사 특허의 선행기술 발굴로 등록 무효 청구",
        "cost": "높음 ($50k~$500k)",
        "timeline": "12~36개월",
        "when": "경쟁사 핵심 특허가 자사 사업에 심각한 장애 시",
    },
    "license_in": {
        "name": "라이선스 도입 (License-In)",
        "desc": "경쟁사 특허를 로열티 지불로 사용권 확보",
        "cost": "로열티 (매출의 1~10%)",
        "timeline": "3~6개월 협상",
        "when": "회피설계 비용 > 로열티 비용 시",
    },
    "cross_license": {
        "name": "크로스 라이선스 (Cross-License)",
        "desc": "자사 IP와 경쟁사 IP를 상호 무상(또는 저가) 교환",
        "cost": "협상 비용",
        "timeline": "6~12개월",
        "when": "양사 보유 IP 상호 필요 시",
    },
    "patent_pool": {
        "name": "특허 풀 참여 (Patent Pool)",
        "desc": "업계 공동 특허 풀 가입으로 포괄적 실시권 확보",
        "cost": "참여비 (연간 고정)",
        "timeline": "즉시",
        "when": "표준 기술(FRAND) 또는 산업 표준화 분야",
    },
    "monitor_only": {
        "name": "모니터링 지속",
        "desc": "즉각 대응 불필요, 기술 변화 추적 지속",
        "cost": "낮음 (모니터링 비용)",
        "timeline": "상시",
        "when": "직접 충돌 없으나 기술 방향 유사 시",
    },
}

# 위협 심각도 분류
_THREAT_LEVELS = {
    "critical": {"label": "긴급", "action_months": 1, "color": "red"},
    "high": {"label": "시급", "action_months": 3, "color": "orange"},
    "medium": {"label": "주의", "action_months": 6, "color": "yellow"},
    "low": {"label": "관찰", "action_months": 12, "color": "green"},
}


class CompetitiveMonitor(BaseAgent):
    stage_id = "G10-Competitive"
    stage_name = "경쟁대응 전략"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          tech_name (str): 기술명
          competitor_patents (list of {
            patent_no, title, assignee, ipc, claim_summary,
            overlap_risk: critical/high/medium/low,
            filed_date
          }): 경쟁사 특허 목록
          market_intelligence (list of str): 시장 정보 (신제품 출시, 인수합병 등)
          technology_trends (list of str): 기술 트렌드 (표준화 동향, 오픈소스 등)
          own_patent_count (int): 자사 보유 특허 수
          own_ip_strength_score (float): 자사 IP 강도 점수 (G1 결과)
          target_market (str, optional): 주요 시장
        """
        score = self._score(input_data)
        gate = self._gate_from_score(score)
        output_doc = self._build_output(input_data, score)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output_doc,
            next_actions=self._next_actions(gate, input_data),
            warnings=self._warnings(input_data),
        )

    def _score(self, d: dict) -> float:
        """높을수록 경쟁대응 준비도 양호"""
        score = 0.0
        comp_patents = d.get("competitor_patents", [])
        critical_count = sum(1 for p in comp_patents if p.get("overlap_risk") == "critical")
        high_count = sum(1 for p in comp_patents if p.get("overlap_risk") == "high")

        # 자사 IP 강도 (30점)
        own_strength = d.get("own_ip_strength_score", 50)
        score += own_strength * 0.3

        # 경쟁 위협 분석 완성도 (25점)
        score += min(25, len(comp_patents) * 5)

        # 위협 심각도 역산 (클수록 대응 필요 = 준비도 낮음)
        threat_penalty = critical_count * 15 + high_count * 8
        score -= min(40, threat_penalty)

        # 시장 정보 보유 (15점)
        score += min(15, len(d.get("market_intelligence", [])) * 5)

        # 기술 트렌드 파악 (10점)
        score += min(10, len(d.get("technology_trends", [])) * 3)

        return round(max(0, min(score + 20, 100)), 1)

    def _recommend_response(self, patent: dict, own_strength: float) -> str:
        risk = patent.get("overlap_risk", "low")
        if risk == "critical":
            return "invalidity" if own_strength >= 70 else "license_in"
        if risk == "high":
            return "design_around"
        if risk == "medium":
            return "monitor_only"
        return "monitor_only"

    def _build_output(self, d: dict, score: float) -> dict:
        comp_patents = d.get("competitor_patents", [])
        own_strength = d.get("own_ip_strength_score", 50)

        # 위협별 대응 계획
        threat_response_plan = []
        for p in comp_patents:
            risk = p.get("overlap_risk", "low")
            action_key = self._recommend_response(p, own_strength)
            threat_response_plan.append({
                "patent_no": p.get("patent_no", ""),
                "title": p.get("title", ""),
                "assignee": p.get("assignee", ""),
                "overlap_risk": risk,
                "threat_level": _THREAT_LEVELS.get(risk, {}),
                "recommended_action": action_key,
                "action_detail": _RESPONSE_ACTIONS.get(action_key, {}),
            })
        threat_response_plan.sort(
            key=lambda x: ["critical", "high", "medium", "low"].index(x.get("overlap_risk", "low"))
        )

        # 회피설계 로드맵 (critical/high 대상)
        design_around_targets = [
            p for p in threat_response_plan
            if p["recommended_action"] == "design_around"
        ]

        llm_result = self._llm(
            f"기술명: {d.get('tech_name', '')}\n"
            f"경쟁사 특허 위협: critical={sum(1 for p in comp_patents if p.get('overlap_risk')=='critical')}건, "
            f"high={sum(1 for p in comp_patents if p.get('overlap_risk')=='high')}건\n"
            f"시장 정보: {d.get('market_intelligence', [])}\n"
            f"기술 트렌드: {d.get('technology_trends', [])}\n\n"
            "경쟁대응 종합 전략을 JSON으로:\n"
            '{"competitive_position":"leading/following/challenged","key_threats":[],'
            '"strategic_recommendations":[],"monitoring_checklist":[]}',
            system="IP 경쟁전략 전문가. JSON만 반환."
        )
        try:
            import json
            strategic_analysis = json.loads(llm_result)
        except Exception:
            strategic_analysis = {
                "competitive_position": "challenged" if score < 50 else "following",
                "key_threats": [p["title"] for p in threat_response_plan[:3]],
                "strategic_recommendations": ["경쟁사 핵심 특허 무효심판 검토", "회피설계 R&D 스프린트 착수"],
            }

        return {
            "competitive_landscape_tracking": {
                "tech_name": d.get("tech_name", ""),
                "competitor_patent_count": len(comp_patents),
                "threat_summary": {
                    "critical": sum(1 for p in comp_patents if p.get("overlap_risk") == "critical"),
                    "high": sum(1 for p in comp_patents if p.get("overlap_risk") == "high"),
                    "medium": sum(1 for p in comp_patents if p.get("overlap_risk") == "medium"),
                    "low": sum(1 for p in comp_patents if p.get("overlap_risk") == "low"),
                },
                "own_patent_count": d.get("own_patent_count", 0),
                "own_ip_strength": own_strength,
            },
            "threat_response_plan": threat_response_plan,
            "design_around_roadmap": {
                "target_count": len(design_around_targets),
                "targets": design_around_targets,
                "estimated_months": len(design_around_targets) * 4,
                "note": "회피설계 각 건당 평균 4개월 R&D 스프린트 소요",
            },
            "response_actions_menu": _RESPONSE_ACTIONS,
            "strategic_analysis": strategic_analysis,
            "competitive_score": score,
        }

    def _next_actions(self, gate: str, d: dict) -> list[str]:
        comp_patents = d.get("competitor_patents", [])
        critical = [p for p in comp_patents if p.get("overlap_risk") == "critical"]
        if gate == "Go":
            return [
                "경쟁 모니터링 자동화 시스템 구축 (Derwent, PatSnap 등)",
                "분기별 경쟁사 특허 공개 정기 검색",
                "G10-Portfolio 최적화와 연계하여 IP 포트폴리오 강화 계획 수립",
            ]
        if gate == "Hold":
            if critical:
                return [
                    f"긴급 대응: {critical[0].get('patent_no', '')} 특허 무효심판 또는 라이선스 협상 즉시 착수",
                    "IP 전문 대리인 긴급 자문 요청",
                ]
            return ["경쟁사 특허 조사 범위 확대", "시장 인텔리전스 추가 수집"]
        return ["경쟁 위협 과다 — G9 거래구조 재검토 또는 기술 피벗"]

    def _warnings(self, d: dict) -> list[str]:
        warns = []
        comp_patents = d.get("competitor_patents", [])
        critical_count = sum(1 for p in comp_patents if p.get("overlap_risk") == "critical")
        high_count = sum(1 for p in comp_patents if p.get("overlap_risk") == "high")
        if critical_count > 0:
            warns.append(f"긴급 위협 {critical_count}건: 즉각 법률 자문 및 대응 계획 수립 필요")
        if high_count > 0:
            warns.append(f"시급 위협 {high_count}건: 회피설계 또는 라이선스 협상 3개월 내 착수 권장")
        if not d.get("market_intelligence"):
            warns.append("시장 인텔리전스 부재: 경쟁사 전략 변화 추적 체계 부재")
        return warns
