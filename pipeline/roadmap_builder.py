"""Layer 3 — 서비스: 기술사업화 로드맵 자동 생성
PhaseGatePipeline 전체 결과 → TRL·자금·파트너·엑시트 통합 타임라인 자동 합성.
산출물: 분기별 마일스톤, 자금조달 단계, 파트너십 시점, KPI 목표, 리스크 레지스터
"""
from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict


# ─────────────────────────────────────────────
# 마일스톤 정의
# ─────────────────────────────────────────────
@dataclass
class Milestone:
    quarter: str          # "Q1 2026"
    stage:   str          # "TRL5 달성" / "첫 매출" 등
    action:  str          # 구체 액션
    owner:   str          # "기술팀" / "영업팀" 등
    kpi:     str          # 측정 지표
    funding_event: str = ""  # 연계 자금 이벤트


@dataclass
class RoadmapOutput:
    tech_id:       str
    tech_name:     str
    current_trl:   int
    target_trl:    int
    total_quarters: int
    milestones:    list[Milestone] = field(default_factory=list)
    funding_plan:  list[dict]      = field(default_factory=list)
    kpi_targets:   dict            = field(default_factory=dict)
    risk_register: list[dict]      = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# ─────────────────────────────────────────────
# TRL 단계별 표준 마일스톤 템플릿
# ─────────────────────────────────────────────
_TRL_MILESTONES = {
    1: Milestone("Q0",   "TRL1",  "기초 연구 원리 확인",               "연구팀",  "논문 1편 이상"),
    2: Milestone("Q0",   "TRL2",  "기술 개념 정립·특허 출원",           "연구팀",  "발명공개서(IDF) 제출"),
    3: Milestone("Q1",   "TRL3",  "PoC 설계·프로토타입 계획",           "연구팀",  "PoC 계획서 승인"),
    4: Milestone("Q1",   "TRL4",  "실험실 수준 프로토타입 검증",         "개발팀",  "MAPE/성능 목표 달성"),
    5: Milestone("Q2",   "TRL5",  "관련 환경 실증·사용자 인터뷰 5건",   "개발팀",  "고객 인터뷰 5건 완료"),
    6: Milestone("Q2",   "TRL6",  "파일럿 환경 검증·LoI 1건",           "영업팀",  "LoI 서명 1건"),
    7: Milestone("Q3",   "TRL7",  "운영 환경 시범 구축·파일럿 3개사",   "영업팀",  "파일럿 계약 3건"),
    8: Milestone("Q3",   "TRL8",  "시스템 완성·초기 매출 발생",         "경영진",  "ARR $100K+"),
    9: Milestone("Q4",   "TRL9",  "양산·상업화·레퍼런스 확보",          "경영진",  "ARR $500K+ / 고객 10개사"),
}

_FUNDING_SEQUENCE = [
    {"trl_trigger": 3, "stage": "부트스트랩·정부 R&D",   "amount_usd": 100_000,   "dilution_pct": 0,  "type": "non_dilutive"},
    {"trl_trigger": 5, "stage": "Pre-Seed·TIPS",         "amount_usd": 500_000,   "dilution_pct": 8,  "type": "equity"},
    {"trl_trigger": 6, "stage": "Seed",                  "amount_usd": 2_000_000, "dilution_pct": 15, "type": "equity"},
    {"trl_trigger": 7, "stage": "Series A",              "amount_usd": 8_000_000, "dilution_pct": 20, "type": "equity"},
    {"trl_trigger": 9, "stage": "Series B+",             "amount_usd": 30_000_000,"dilution_pct": 15, "type": "equity"},
]

_RISK_REGISTER_TEMPLATE = [
    {"id": "R1", "category": "기술", "risk": "TRL 달성 지연",         "probability": "중", "impact": "고", "mitigation": "주 단위 기술 리뷰·대체 방법론 준비"},
    {"id": "R2", "category": "시장", "risk": "고객 도입 속도 저조",   "probability": "중", "impact": "고", "mitigation": "얼리어답터 집중·무료 파일럿 제공"},
    {"id": "R3", "category": "자금", "risk": "투자 유치 실패",        "probability": "중", "impact": "고", "mitigation": "정부 비희석 자금 병행·런웨이 18개월 유지"},
    {"id": "R4", "category": "IP",   "risk": "경쟁사 유사 특허 등록", "probability": "저", "impact": "고", "mitigation": "선행 특허 조기 출원·방어 특허 포트폴리오"},
    {"id": "R5", "category": "팀",   "risk": "핵심 인력 이탈",        "probability": "중", "impact": "중", "mitigation": "스톡옵션 설계·리텐션 보너스"},
    {"id": "R6", "category": "규제", "risk": "인증 획득 지연",        "probability": "중", "impact": "중", "mitigation": "규제 전문가 선임·규제 샌드박스 활용"},
]


# ─────────────────────────────────────────────
# 로드맵 빌더
# ─────────────────────────────────────────────
class RoadmapBuilder:

    def build(
        self,
        tech_id:      str,
        tech_name:    str,
        current_trl:  int,
        target_trl:   int,
        pipeline_results: dict = None,
        start_year:   int = 2026,
        start_quarter: int = 2,
    ) -> RoadmapOutput:
        """
        pipeline_results: PhaseGatePipeline.get_all_results() 반환값 (선택)
        """
        trl_steps    = range(current_trl + 1, min(target_trl + 1, 10))
        total_qtrs   = len(trl_steps) * 1  # TRL당 평균 1분기
        roadmap      = RoadmapOutput(
            tech_id=tech_id,
            tech_name=tech_name,
            current_trl=current_trl,
            target_trl=target_trl,
            total_quarters=total_qtrs,
        )

        # 마일스톤 생성
        q_idx = 0
        for trl in trl_steps:
            template = _TRL_MILESTONES.get(trl)
            if not template:
                continue
            yr  = start_year + (start_quarter + q_idx - 1) // 4
            qtr = (start_quarter + q_idx - 1) % 4 + 1

            # 자금 이벤트 연계
            funding_event = next(
                (f["stage"] for f in _FUNDING_SEQUENCE if f["trl_trigger"] == trl), ""
            )
            roadmap.milestones.append(Milestone(
                quarter=f"Q{qtr} {yr}",
                stage=template.stage,
                action=template.action,
                owner=template.owner,
                kpi=template.kpi,
                funding_event=funding_event,
            ))
            q_idx += 1

        # 자금조달 계획
        roadmap.funding_plan = [
            f for f in _FUNDING_SEQUENCE
            if f["trl_trigger"] >= current_trl and f["trl_trigger"] <= target_trl
        ]

        # KPI 목표 (파이프라인 결과에서 추출)
        roadmap.kpi_targets = self._extract_kpis(pipeline_results or {}, target_trl)

        # 리스크 레지스터
        roadmap.risk_register = _RISK_REGISTER_TEMPLATE.copy()

        return roadmap

    def _extract_kpis(self, results: dict, target_trl: int) -> dict:
        kpis = {
            "trl_target":         target_trl,
            "customer_target_6m": 3,
            "customer_target_12m": 10,
            "arr_target_12m_usd": 100_000,
            "arr_target_24m_usd": 500_000,
            "patent_target":      3,
            "team_size_target":   10,
        }
        # G3 시장 분석 결과에서 SOM 추출
        g3 = results.get("3", {})
        if isinstance(g3, dict):
            doc = g3.get("output_doc", {})
            som = doc.get("market_analysis", {}).get("som_usd", 0)
            if som:
                kpis["arr_target_24m_usd"] = int(som * 0.05)
        return kpis

    def to_json(self, roadmap: RoadmapOutput) -> str:
        return json.dumps(roadmap.to_dict(), ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────
# 헬퍼 함수 — API에서 직접 호출
# ─────────────────────────────────────────────
def build_roadmap(
    tech_id: str,
    tech_name: str,
    current_trl: int,
    target_trl: int = 9,
    pipeline_results: dict = None,
) -> dict:
    builder = RoadmapBuilder()
    roadmap = builder.build(tech_id, tech_name, current_trl, target_trl, pipeline_results)
    return roadmap.to_dict()
