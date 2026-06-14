"""보고서 의존성 그래프 — R1~R9 가용성 체커

포팅 출처: ip-insight-handoff/app/lib/reportDeps.ts

R5 → R6
R5 + R2 → R7
(R1 OR R2) → R8
R1~R4·R9 = Tier 1 (선행 보고서 불필요)
R5~R7 = Tier 2
R8 = Tier 3
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

# ─── 보고서 ID 상수 ──────────────────────────────────
R1 = "R1_investment"
R2 = "R2_enforcement"
R3 = "R3_commercialize"
R4 = "R4_portfolio"
R5 = "R5_valuation"
R6 = "R6_ir"
R7 = "R7_license"
R8 = "R8_gov_ir"
R9 = "R9_sps"

ALL_REPORTS: list[str] = [R1, R2, R3, R4, R5, R6, R7, R8, R9]


@dataclass
class ReportDef:
    label: str
    label_en: str
    tier: int
    description: str
    deps: list[str] = field(default_factory=list)           # AND 조건
    or_deps: list[list[str]] = field(default_factory=list)  # OR 그룹 조건


REPORT_DEFS: dict[str, ReportDef] = {
    R1: ReportDef(
        label="투자·인수 심사 보고서(R1)",
        label_en="Investment & Acquisition Report",
        tier=1,
        description="특허 투자 가치·시장 규모·권리 안정성·리스크 종합 평가",
    ),
    R2: ReportDef(
        label="권리행사·분쟁 전략 보고서(R2)",
        label_en="Rights Enforcement Report",
        tier=1,
        description="PCML 6지표·경쟁특허·Key Passages 기반 분쟁전략·NPV·라이선스 조건",
    ),
    R3: ReportDef(
        label="사업화·연구개발 실행 보고서(R3)",
        label_en="Commercialization & R&D Execution Report",
        tier=1,
        description="TRL 로드맵·BM 4가지·파트너십 Tier A/B/C·White Space·R&D 과제",
    ),
    R4: ReportDef(
        label="포트폴리오·대외 제출 보고서(R4)",
        label_en="Portfolio & External Submission Report",
        tier=1,
        description="Asset Tier·PQE·HHI·Landscape·경쟁기술 비교·IR/과제/기술이전 메시지",
    ),
    R9: ReportDef(
        label="선행기술조사 보고서(SPS)",
        label_en="State of the Art Search Report",
        tier=1,
        description="선행기술 기반 신규성/진보성 상세 분석 보고서",
    ),
    R5: ReportDef(
        label="기술가치평가 보고서(R5)",
        label_en="Technology Valuation Report",
        tier=2,
        description="3접근법(수익·시장·원가)·TCF·WACC·수명주기·NPV 3시나리오 — WIPO/KIIP/ISO 국제기준 (참고용)",
    ),
    R6: ReportDef(
        label="투자자 IR 브리프(R6)",
        label_en="Investor IR Brief",
        tier=2,
        description="PCML 7지표 투자자 언어 번역·기술/시장 경쟁력 근거·IR Deck 4문장 (R5 연계 권장)",
        deps=[R5],
    ),
    R7: ReportDef(
        label="라이선스·기술이전 준비도 보고서(R7)",
        label_en="License & Technology Transfer Readiness Report",
        tier=2,
        description="거래 준비도·후보군 세그멘테이션·BM×거래방식·Term Sheet 10항목·실시료·리스크 할인율",
        deps=[R5, R2],
    ),
    R8: ReportDef(
        label="정부지원/IR 제출 보고서(R8)",
        label_en="Gov & IR Submission Report",
        tier=3,
        description="기술보증·과제 신청·투자 유치용 요약 보고서",
        or_deps=[[R1, R2]],
    ),
}


@dataclass
class ReportAvailability:
    report_id: str
    label: str
    tier: int
    available: bool
    completed: bool
    stale: bool
    missing_deps: list[str]
    missing_or_deps: list[list[str]]
    missing_stores: list[str]


def check_availability(
    report_id: str,
    completed: dict[str, dict],      # report_id → {"status": "completed", "pcml_v": int, "scr_v": int}
    has_store_a: bool = True,
    has_store_b: bool = True,
    pcml_version: int = 0,
    screening_version: int = 0,
) -> ReportAvailability:
    """단일 보고서 가용성을 계산한다."""
    defn = REPORT_DEFS[report_id]
    existing = completed.get(report_id)

    # 필수 스토어 체크 (모든 보고서는 A+B 필요)
    missing_stores: list[str] = []
    if not has_store_a:
        missing_stores.append("A")
    if not has_store_b:
        missing_stores.append("B")

    # AND deps
    missing_deps = [
        d for d in defn.deps
        if completed.get(d, {}).get("status") != "completed"
    ]

    # OR dep groups
    missing_or_deps: list[list[str]] = []
    for group in defn.or_deps:
        has_any = any(completed.get(d, {}).get("status") == "completed" for d in group)
        if not has_any:
            missing_or_deps.append(group)

    # stale 체크
    stale = False
    if existing:
        based_pcml = existing.get("pcml_v", 0)
        based_scr = existing.get("scr_v", 0)
        stale = based_pcml < pcml_version or based_scr < screening_version

    available = (
        not missing_stores and not missing_deps and not missing_or_deps
    )
    is_completed = existing is not None and existing.get("status") == "completed"

    return ReportAvailability(
        report_id=report_id,
        label=defn.label,
        tier=defn.tier,
        available=available,
        completed=is_completed,
        stale=stale,
        missing_deps=missing_deps,
        missing_or_deps=missing_or_deps,
        missing_stores=missing_stores,
    )


def get_all_availability(
    completed: dict[str, dict],
    has_store_a: bool = True,
    has_store_b: bool = True,
    pcml_version: int = 0,
    screening_version: int = 0,
) -> list[ReportAvailability]:
    """R1~R9 전체 가용성을 Tier 순으로 반환."""
    results = [
        check_availability(rid, completed, has_store_a, has_store_b, pcml_version, screening_version)
        for rid in ALL_REPORTS
    ]
    return sorted(results, key=lambda r: r.tier)


def mark_stale_cascade(
    completed: dict[str, dict],
    changed_report_id: str,
) -> list[str]:
    """보고서가 갱신됐을 때 의존 보고서를 stale 처리하고 목록 반환."""
    staled: list[str] = []
    for rid, defn in REPORT_DEFS.items():
        if changed_report_id in defn.deps:
            if completed.get(rid, {}).get("status") == "completed":
                completed[rid]["status"] = "stale"
                staled.append(rid)
        for group in defn.or_deps:
            if changed_report_id in group and rid not in staled:
                if completed.get(rid, {}).get("status") == "completed":
                    completed[rid]["status"] = "stale"
                    staled.append(rid)
    return staled
