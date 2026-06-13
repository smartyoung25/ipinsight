"""G1-Whitespace 특허 화이트스페이스 분석 — WIPO 특허 지형 분석 표준

WIPO 특허 지형 분석의 두 축:
  1. FTO (Freedom to Operate): 기존 특허에 침해하지 않는가  → G2-Patent에서 담당
  2. White Space: 아직 아무도 특허를 내지 않은 기술 공백은 어디인가  → 본 모듈

화이트스페이스 식별 방법 (Stanford OTL 벤치마크):
  - IPC 코드 × 기술 기능 매트릭스에서 미점유 셀 탐색
  - 출원 트렌드 감소 영역 (경쟁사가 포기한 영역)
  - 지리적 공백 (특정 국가에서 미출원된 핵심 기술)
  - 기술 융합 공백 (두 IPC 코드가 결합된 영역의 미출원)
"""
from __future__ import annotations
from .base_agent import BaseAgent, StageResult

# IPC 섹션별 기술 도메인 (WIPO IPC 구분)
_IPC_SECTIONS = {
    "A": "생활필수품 (농업·식품·의료·오락)",
    "B": "처리조작·운수",
    "C": "화학·야금",
    "D": "섬유·제지",
    "E": "고정구조물 (건축·굴착)",
    "F": "기계공학·조명·무기",
    "G": "물리학 (계측·광학·정보처리)",
    "H": "전기",
}

# 화이트스페이스 유형 정의
_WHITESPACE_TYPES = {
    "functional_gap": {
        "name": "기능 공백",
        "desc": "특정 기능을 수행하는 기술이 특허화되지 않은 영역",
        "opportunity": "높음",
    },
    "geographic_gap": {
        "name": "지리적 공백",
        "desc": "핵심 기술이 특정 국가에서 미출원된 영역",
        "opportunity": "중간 (선출원 경쟁 주의)",
    },
    "combination_gap": {
        "name": "기술 융합 공백",
        "desc": "두 기술 도메인의 결합이 미출원된 융합 영역",
        "opportunity": "매우 높음",
    },
    "abandoned_area": {
        "name": "포기 영역",
        "desc": "경쟁사가 출원 후 유지를 포기한 기술 영역",
        "opportunity": "중간 (재진입 가능)",
    },
    "emerging_gap": {
        "name": "신기술 공백",
        "desc": "새로운 기술 트렌드에서 아직 특허가 희소한 영역",
        "opportunity": "매우 높음 (선점 기회)",
    },
}


class WhitespaceAnalyzer(BaseAgent):
    stage_id = "G1-Whitespace"
    stage_name = "특허 화이트스페이스 분석"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          tech_name (str): 기술명
          ipc_codes (list of str): 자사 기술의 IPC 코드 (예: ["G06N", "A01G"])
          competitor_filings (list of {
            assignee, ipc_codes[], filed_year, status: active/expired/abandoned
          }): 경쟁사 출원 목록
          target_countries (list of str): 목표 출원 국가 (예: ["KOR","USA","EU"])
          technology_trends (list of str): 기술 트렌드 (예: ["엣지AI", "디지털트윈"])
          own_filed_ipc (list of str, optional): 이미 출원한 IPC 코드
        """
        score = self._score(input_data)
        gate = self._gate_from_score(score)
        output_doc = self._build_output(input_data, score)
        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output_doc,
            next_actions=self._next_actions(gate, output_doc),
            warnings=self._warnings(input_data),
        )

    def _score(self, d: dict) -> float:
        """화이트스페이스 분석 완성도 채점"""
        score = 0.0
        # IPC 코드 커버리지 (25점)
        score += min(25, len(d.get("ipc_codes", [])) * 8)
        # 경쟁사 출원 분석 완성도 (30점)
        filings = d.get("competitor_filings", [])
        score += min(30, len(filings) * 3)
        # 지리적 다양성 (20점)
        score += min(20, len(d.get("target_countries", [])) * 5)
        # 기술 트렌드 반영 (15점)
        score += min(15, len(d.get("technology_trends", [])) * 5)
        # 자사 출원 현황 파악 (10점)
        score += 10 if d.get("own_filed_ipc") else 0
        return round(min(score, 100), 1)

    def _find_geographic_gaps(self, d: dict) -> list[dict]:
        """자사 IPC × 목표 국가에서 경쟁사 미출원 영역 탐색"""
        own_ipc = set(d.get("ipc_codes", []))
        target_countries = d.get("target_countries", [])
        filings = d.get("competitor_filings", [])

        # 국가별 출원된 IPC 집계
        country_ipc_coverage: dict = {}
        for f in filings:
            # 출원 국가를 IPC 코드 prefix로 추정 (실제 구현 시 patent_no prefix 사용)
            for ipc in f.get("ipc_codes", []):
                section = ipc[:1]
                country_ipc_coverage.setdefault("ALL", set()).add(ipc[:4])

        gaps = []
        for country in target_countries:
            covered = country_ipc_coverage.get("ALL", set())
            country_gaps = [ipc for ipc in own_ipc if ipc[:4] not in covered]
            if country_gaps:
                gaps.append({
                    "country": country,
                    "uncovered_ipc": country_gaps,
                    "opportunity": "선출원 가능 — 경쟁사 미진입 확인 필요",
                })
        return gaps

    def _find_combination_gaps(self, d: dict) -> list[dict]:
        """자사 IPC 코드들의 융합 조합 중 미출원 영역"""
        own_ipc = d.get("ipc_codes", [])
        trends = d.get("technology_trends", [])
        filings = d.get("competitor_filings", [])

        filed_combinations: set = set()
        for f in filings:
            codes = f.get("ipc_codes", [])
            for i in range(len(codes)):
                for j in range(i + 1, len(codes)):
                    filed_combinations.add((codes[i][:4], codes[j][:4]))

        gaps = []
        for i in range(len(own_ipc)):
            for j in range(i + 1, len(own_ipc)):
                combo = (own_ipc[i][:4], own_ipc[j][:4])
                if combo not in filed_combinations:
                    gaps.append({
                        "ipc_combination": list(combo),
                        "ipc_domains": [
                            _IPC_SECTIONS.get(combo[0][0], "기타"),
                            _IPC_SECTIONS.get(combo[1][0], "기타"),
                        ],
                        "whitespace_type": "combination_gap",
                        "opportunity": _WHITESPACE_TYPES["combination_gap"]["opportunity"],
                    })

        # 트렌드 기반 신기술 공백
        for trend in trends:
            gaps.append({
                "ipc_combination": own_ipc[:2] if len(own_ipc) >= 2 else own_ipc,
                "emerging_trend": trend,
                "whitespace_type": "emerging_gap",
                "opportunity": _WHITESPACE_TYPES["emerging_gap"]["opportunity"],
            })

        return gaps[:10]  # 상위 10개만

    def _find_abandoned_areas(self, d: dict) -> list[dict]:
        """경쟁사가 포기(abandoned/expired)한 기술 영역"""
        filings = d.get("competitor_filings", [])
        abandoned = [f for f in filings if f.get("status") in ("abandoned", "expired")]
        result = []
        for f in abandoned:
            result.append({
                "assignee": f.get("assignee", ""),
                "ipc_codes": f.get("ipc_codes", []),
                "filed_year": f.get("filed_year", ""),
                "whitespace_type": "abandoned_area",
                "opportunity": _WHITESPACE_TYPES["abandoned_area"]["opportunity"],
                "note": "원 출원인이 유지 포기 — 기술 공개는 됐으나 독점권 없음. 재출원 시 선행기술 주의",
            })
        return result

    def _build_output(self, d: dict, score: float) -> dict:
        geo_gaps = self._find_geographic_gaps(d)
        combo_gaps = self._find_combination_gaps(d)
        abandoned = self._find_abandoned_areas(d)

        all_opportunities = geo_gaps + combo_gaps + abandoned
        high_opp = [o for o in all_opportunities if "높음" in o.get("opportunity", "")]

        llm_result = self._llm(
            f"기술명: {d.get('tech_name', '')}\n"
            f"IPC 코드: {d.get('ipc_codes', [])}\n"
            f"기술 트렌드: {d.get('technology_trends', [])}\n"
            f"지리적 공백: {len(geo_gaps)}건, 융합 공백: {len(combo_gaps)}건\n\n"
            "이 기술의 화이트스페이스 전략을 JSON으로:\n"
            '{"top_whitespace_opportunity":"","filing_priority":[],"strategic_direction":""}',
            system="WIPO 특허 지형 분석 전문가. JSON만 반환."
        )
        try:
            import json
            strategy = json.loads(llm_result)
        except Exception:
            strategy = {
                "top_whitespace_opportunity": f"{combo_gaps[0]['ipc_combination'] if combo_gaps else '미정'} 융합 영역 선점",
                "filing_priority": [g.get("country", "") for g in geo_gaps[:3]],
                "strategic_direction": "융합 IPC 조합 출원으로 경쟁사 미진입 영역 선점",
            }

        return {
            "whitespace_summary": {
                "tech_name": d.get("tech_name", ""),
                "total_opportunities": len(all_opportunities),
                "high_priority_count": len(high_opp),
                "geographic_gaps": len(geo_gaps),
                "combination_gaps": len(combo_gaps),
                "abandoned_areas": len(abandoned),
                "whitespace_score": score,
            },
            "geographic_whitespace": geo_gaps,
            "combination_whitespace": combo_gaps[:5],
            "abandoned_whitespace": abandoned[:5],
            "filing_recommendations": {
                "immediate": [
                    o for o in high_opp[:3]
                ],
                "watch_list": combo_gaps[3:6] if len(combo_gaps) > 3 else [],
            },
            "whitespace_types_reference": _WHITESPACE_TYPES,
            "strategic_analysis": strategy,
        }

    def _next_actions(self, gate: str, output_doc: dict) -> list[str]:
        summary = output_doc.get("whitespace_summary", {})
        if gate == "Go":
            return [
                f"고우선 화이트스페이스 {summary.get('high_priority_count', 0)}건 즉시 출원 착수",
                "융합 IPC 조합 출원으로 경쟁사 진입 차단 청구항 설계",
                "G10-Global 글로벌 IP 전략과 연동하여 국가별 선점 계획 수립",
            ]
        if gate == "Hold":
            return [
                "경쟁사 출원 데이터 추가 수집 (KIPRIS·USPTO·Espacenet 검색)",
                "IPC 코드 범위 확대 — 인접 기술 도메인까지 탐색",
                "IP 전문가와 화이트스페이스 청구항 설계 협의",
            ]
        return [
            "화이트스페이스 분석 데이터 부족 — 경쟁사 출원 목록 확보 후 재분석",
        ]

    def _warnings(self, d: dict) -> list[str]:
        w = []
        if not d.get("competitor_filings"):
            w.append("경쟁사 출원 데이터 없음 — 공백 분석 신뢰도 낮음. KIPRIS·USPTO 검색 필요")
        if len(d.get("ipc_codes", [])) < 2:
            w.append("IPC 코드 1개 — 융합 공백 분석 불가. 관련 IPC 코드 추가 입력 권장")
        if not d.get("technology_trends"):
            w.append("기술 트렌드 미입력 — 신기술 공백(Emerging Gap) 탐색 불가")
        return w
