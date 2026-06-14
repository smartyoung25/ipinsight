"""QueryRouter — G-Stage × tech_type × region 기반 최소 커넥터 선택
핵심 원칙: 매 요청마다 12개 커넥터를 전부 호출하지 않는다.
스테이지(G0~G10)·기술 유형·목표 지역에 필요한 커넥터만 동적으로 선택.

비용 절감 기준
  - 캐시 HIT → 0 API 호출
  - Stage별 최소 커넥터 → 평균 3~4개 (12개 전체 대비 70% 절감)
  - 지역 필터 → DEV 대상 임상 커넥터 스킵 등
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────────────────
# 1. 스테이지별 필수 커넥터 정의
# ─────────────────────────────────────────────────────────

# G-Stage → 필요한 CodeLinker 필드 목록
# (필드명은 CodeContext 필드와 1:1 대응)
_STAGE_CONNECTOR_MAP: dict[str, list[str]] = {
    "G0":  ["market", "trade", "regional"],                          # 수요조사 — 시장 + 무역 + 지역
    "G1":  ["paper", "market", "regional"],                          # 아이디어 — 논문 TRL + 시장
    "G2":  ["patent", "technology", "paper", "wipo"],                # TRL 검증 — 특허 + 논문
    "G3":  ["patent", "wipo", "market", "industry", "trade"],        # 시장스캔 — 특허 + 시장 + 무역
    "G4":  ["patent", "wipo", "industry", "regulatory"],             # IP 전략 — 특허 + 규제경로
    "G5":  ["regulatory", "clinical", "regional"],                   # 규제경로 — 규제 + 임상 + 지역
    "G6":  ["market", "trade", "company", "regional", "esg"],        # 가치평가 — 시장 + 무역 + 기업
    "G7":  ["company", "policy", "regional"],                        # 딜구조 — 기업 + 정책 + 지역
    "G8":  ["regulatory", "clinical", "company", "regional"],        # 규제승인 — 규제 + 임상 + 기업
    "G9":  ["company", "market", "trade", "policy"],                 # 딜실행 — 기업 + 시장 + 무역
    "G10": ["esg", "market", "regional"],                            # ESG임팩트 — ESG + 시장
    "ALL": ["patent", "technology", "wipo", "industry", "regulatory",
            "company", "policy", "paper", "market", "clinical", "esg", "trade", "regional"],
}

# tech_type별 선택적 추가 커넥터
_TECH_ADDON: dict[str, list[str]] = {
    "medical_device": ["clinical", "regulatory"],
    "agritech":       ["paper", "esg"],
    "energy":         ["esg", "market"],
    "software_saas":  ["company", "market"],
    "manufacturing":  ["industry", "company"],
}

# 지역별 스킵 가능 커넥터 (해당 커넥터가 지역과 무관한 경우)
_REGION_SKIP: dict[str, list[str]] = {
    "RU": ["clinical"],   # 러시아: 서방 임상DB 무관
    "CN": [],             # 중국: 전부 필요
    "DEV": ["company"],   # 개도국: LEI 기업DB 낮은 커버리지
}


# ─────────────────────────────────────────────────────────
# 2. 캐시 TTL 정책 (시간 단위)
# ─────────────────────────────────────────────────────────

CACHE_TTL: dict[str, int] = {
    # 실시간 변동 데이터 — 짧은 TTL
    "patent":     24,    # 특허: 매일 (새 출원 반영)
    "clinical":   24,    # 임상: 매일
    "paper":      24,    # 논문: 매일
    # 중간 변동 데이터
    "market":     168,   # 시장: 주간 (World Bank 월별 업데이트)
    "company":    168,   # 기업: 주간
    "industry":   168,   # 산업코드: 주간
    "trade":      168,   # 무역: 주간 (UN Comtrade 연간 집계, 연초 갱신)
    # 느린 변동 데이터 — 긴 TTL
    "wipo":       720,   # WIPO: 월간
    "technology": 720,   # 기술코드: 월간
    "regulatory": 720,   # 규제: 월간
    "policy":     720,   # 정책: 월간
    "esg":        168,   # ESG: 주간
    "regional":   2160,  # 지역 지식: 분기(90일) — 정적 데이터
}

# Bulk 사전 적재 주기
BULK_SCHEDULE: dict[str, str] = {
    "patent":     "daily:02:00",     # 매일 새벽 2시
    "paper":      "daily:03:00",     # 매일 새벽 3시
    "market":     "weekly:sun:01:00",# 매주 일요일
    "esg":        "weekly:sun:02:00",
    "clinical":   "daily:04:00",
    "regulatory": "monthly:1:01:00", # 매월 1일
    "regional":   "quarterly",       # 분기
}


# ─────────────────────────────────────────────────────────
# 3. QueryRouter
# ─────────────────────────────────────────────────────────

@dataclass
class RouteDecision:
    stage:        str
    tech_type:    str
    regions:      list[str]
    connectors:   list[str]     # 실행할 커넥터 목록
    skipped:      list[str]     # 스킵한 커넥터 목록
    ttl_policy:   dict[str, int]
    estimated_api_calls: int
    rationale:    str

    def summary(self) -> str:
        return (
            f"[{self.stage}·{self.tech_type}·{'+'.join(self.regions)}] "
            f"커넥터 {len(self.connectors)}개 실행 "
            f"(스킵 {len(self.skipped)}개 | 예상 API {self.estimated_api_calls}회)"
        )


class QueryRouter:
    """
    G-Stage × tech_type × target_regions → 최소 커넥터 집합 반환.
    CodeLinkerPipeline.run()에 connectors_filter 파라미터로 전달하여
    불필요한 커넥터를 건너뛴다.
    """

    def route(
        self,
        stage:      str,
        tech_type:  str,
        regions:    list[str],
        force_all:  bool = False,
    ) -> RouteDecision:
        """
        stage:     "G0"~"G10" 또는 "ALL"
        tech_type: "agritech" / "medical_device" / "software_saas" / "energy" / "manufacturing"
        regions:   ["KR", "US", "JP"] 등 ISO 지역 코드
        force_all: True이면 모든 커넥터 실행 (감사·전체 보고서용)
        """
        if force_all:
            selected = list(_STAGE_CONNECTOR_MAP["ALL"])
            skipped  = []
        else:
            # 스테이지 기본 커넥터
            base = set(_STAGE_CONNECTOR_MAP.get(stage, _STAGE_CONNECTOR_MAP["ALL"]))

            # tech_type 추가
            for conn in _TECH_ADDON.get(tech_type, []):
                base.add(conn)

            # 지역별 스킵 적용
            skip_set: set[str] = set()
            for region in regions:
                for conn in _REGION_SKIP.get(region, []):
                    skip_set.add(conn)

            selected = sorted(base - skip_set)
            skipped  = sorted(skip_set & base)

        # 예상 API 호출 수 (커넥터당 평균 2회)
        api_est = len(selected) * 2

        return RouteDecision(
            stage=stage,
            tech_type=tech_type,
            regions=regions,
            connectors=selected,
            skipped=skipped,
            ttl_policy={c: CACHE_TTL[c] for c in selected if c in CACHE_TTL},
            estimated_api_calls=api_est,
            rationale=self._rationale(stage, tech_type, regions, skipped),
        )

    def batch_route(self, requests: list[dict]) -> list[RouteDecision]:
        """여러 요청의 라우팅 결과를 한 번에 계산 (대시보드 선행 계획용)"""
        return [self.route(**r) for r in requests]

    def connector_priority(self, stage: str) -> list[dict]:
        """스테이지별 커넥터 실행 우선순위 (병렬 처리 순서 계획)"""
        connectors = _STAGE_CONNECTOR_MAP.get(stage, _STAGE_CONNECTOR_MAP["ALL"])
        priority_map = {
            # 빠른 응답 커넥터 (로컬 캐시·정적 DB)
            "regional":   1, "technology": 1, "industry": 1, "wipo": 1,
            # 외부 API (중간 속도)
            "patent": 2, "paper": 2, "market": 2, "regulatory": 2,
            # 느린 외부 API
            "clinical": 3, "esg": 3, "company": 3, "policy": 3,
        }
        result = []
        for tier in [1, 2, 3]:
            tier_conns = [c for c in connectors if priority_map.get(c, 2) == tier]
            if tier_conns:
                result.append({"tier": tier, "parallel": tier_conns,
                               "note": ["정적/캐시", "외부 API", "느린 API"][tier - 1]})
        return result

    def cache_freshness_plan(self) -> list[dict]:
        """전체 캐시 갱신 계획표"""
        return [
            {
                "connector": c,
                "ttl_hours": ttl,
                "schedule":  BULK_SCHEDULE.get(c, "on-demand"),
                "strategy":  "bulk-prefetch" if c in BULK_SCHEDULE else "on-demand",
            }
            for c, ttl in sorted(CACHE_TTL.items(), key=lambda x: x[1])
        ]

    def _rationale(self, stage: str, tech_type: str,
                   regions: list[str], skipped: list[str]) -> str:
        parts = [f"Stage {stage}: {', '.join(_STAGE_CONNECTOR_MAP.get(stage, [])[:3])} 위주"]
        if tech_type in _TECH_ADDON:
            parts.append(f"{tech_type} 추가: {', '.join(_TECH_ADDON[tech_type])}")
        if skipped:
            parts.append(f"지역 스킵({'+'.join(regions)}): {', '.join(skipped)}")
        return " | ".join(parts)


# ─────────────────────────────────────────────────────────
# 4. 운영 효율성 매트릭스 (참조 테이블)
# ─────────────────────────────────────────────────────────

EFFICIENCY_MATRIX: dict[str, dict] = {
    "pipeline_modes": {
        "quick":  {
            "description": "핵심 2~3개 커넥터만 — 30초 내 결과",
            "connectors":  ["market", "regional", "patent"],
            "use_case":    "초기 스크리닝·시장 적합성 빠른 판단",
        },
        "standard": {
            "description": "스테이지별 5~6개 커넥터 — 2~3분",
            "connectors":  "QueryRouter.route() 결과",
            "use_case":    "일반 G-Stage 분석",
        },
        "deep": {
            "description": "전체 12개 커넥터 — 5~10분",
            "connectors":  "ALL",
            "use_case":    "투자심사·NDA 전 완전 실사",
        },
    },
    "cost_model": {
        "free_connectors":  ["paper", "market", "clinical", "esg", "regional",
                             "wipo", "technology", "industry"],
        "free_with_key":    ["patent", "policy", "company"],
        "paid_phase3":      ["royalty_range", "crunchbase", "pitchbook"],
        "monthly_cost_usd": {
            "phase1_free":  0,
            "phase2_keys":  0,
            "phase3_paid":  450,    # Crunchbase Basic + Royalty Range
        },
    },
    "data_staleness_risk": {
        "high_risk":   ["patent", "clinical"],    # 매일 변화 → 24h TTL
        "medium_risk": ["market", "company"],     # 주간 변화 → 168h TTL
        "low_risk":    ["regulatory", "wipo", "regional"],  # 월/분기 → 720h+
    },
}
