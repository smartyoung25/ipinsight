"""3단계 신규성 스크리닝 에이전트 (G1.6-SCR) — PQE-SCR v4.0

포팅 출처: ip-insight-handoff/app/prompts/harness-screening.ts

파이프라인 위치: G1.5 (PCML) → G1.6 (Screening) → G2 (TRL)

처리 단계:
  1. 선행기술 조사 (prior art search)
  2. 신규성 분석 (novelty)
  3. 진보성 평가 (inventive step)

출력: SCR 7개 섹션 + Gate 라우팅 (G1~G4)
"""
from __future__ import annotations

import json
import re
from typing import Any

from .base_agent import BaseAgent, StageResult


def _build_screening_prompt(pcml_data: dict, scope: str) -> str:
    is_extended = scope == "full"
    mode_label = "Extended" if is_extended else "Basic"

    return f"""[ROLE]
당신은 IIAMHUB IPinsight PQE-SCR v4.0 운영지침을 준수하는 특허 스크리닝 보고서 분석가입니다.
PCML 분석 결과를 기반으로 (1) 선행기술 조사, (2) 신규성/진보성 평가, (3) SCR 7개 섹션 보고서를 생성합니다.

[MODE]
{mode_label} 스크리닝 — {"KPI 5개(KPI1·4·5·7·9) + PCML 6지표 정량 + §103 시나리오 A + Gate 라우팅 상세" if is_extended else "KPI 3개(KPI1·4·9) 정성 등급 + PCML 범주형 + 기본 Gate 판정"}

[INPUT DATA - PCML 분석 결과]
{json.dumps(pcml_data, ensure_ascii=False, indent=2)}

[ABSOLUTE RULES — SCR 절대 금지 사항]
1. 추정값은 반드시 "(추정)" 표기 — 산출 근거 없이 수치 기재 금지
2. 청구항 원문 근거 없는 Core Node 관계 생성 금지
3. Hard Stop 있는데 G1 결론 금지 — 반드시 G2 이하
4. KPI 수치 확정 금지 — 정성 등급(上/中/下) + 예비값만, 확정은 R1 Full에서
5. 모든 등급에는 1줄 근거 필수

[OUTPUT SCHEMA]
반드시 아래 JSON 구조로 출력하세요.

{{
  "searchMethodology": {{
    "databases": ["string - 검색 DB 목록"],
    "queryStrings": ["string - 실제 사용한 검색 쿼리"],
    "totalHits": 0,
    "analyzedCount": 0
  }},
  "priorArt": {{
    "patents": [
      {{
        "number": "string", "title": "string", "applicant": "string",
        "filingDate": "string", "relevance": 0,
        "keyPassages": ["string"], "overlapElements": ["string"]
      }}
    ],
    "nonPatent": [{{"source": "string", "title": "string", "url": null, "relevance": 0}}]
  }},
  "noveltyAnalysis": {{
    "status": "NOVEL | PARTIAL | NOT_NOVEL",
    "details": "string",
    "threateningClaims": []
  }},
  "inventiveStep": {{
    "status": "INVENTIVE | OBVIOUS | UNCLEAR",
    "details": "string",
    "combinationRisk": "string"
  }},
  "similarityScores": {{
    "maxSimilarity": 0,
    "avgSimilarity": 0,
    "distribution": [{{"range": "string", "count": 0}}]
  }},
  "whiteSpace": ["string - 기술 공백 영역"],
  "section112Issues": ["string - 기재불비 이슈"],

  "scrReport": {{
    "mode": "{mode_label.lower()}",
    "patentBasicInfo": {{
      "patentNumber": "string",
      "applicant": "string",
      "ipcCodes": ["string"],
      "registered": false,
      "remainingYears": null,
      "hasFamily": false
    }},
    "technicalSummary": {{
      "inventionTitle": "string",
      "industryMapping": "string",
      "technicalProblem": "string",
      "technicalSolution": "string",
      "coreNodes": [{{"label": "string", "weight": 0.5}}]
    }},
    "pcmlStructure": {{
      "spofCategory": "없음 | 1건 | 2건+",
      "minCutCategory": "낮음 | 중간 | 높음",
      "ciChecklist": [{{"item": "string", "ok": true}}]
    }},
    "kpiRatings": {{
      "kpi1_claimStrength": {{"grade": "上|中|下", "reason": "string"}},
      "kpi4_evasionResistance": {{"grade": "上|中|下", "reason": "string"}},
      "kpi9_legalStability": {{"grade": "上|中|下", "reason": "string"}}
    }},
    "hardStops": [
      {{"id": "101_eligibility", "label": "§101/§29 특허 적격성", "detected": false, "detail": "string"}},
      {{"id": "spof", "label": "SPOF 발견", "detected": false, "detail": "string"}},
      {{"id": "remaining_life", "label": "잔여수명 3년 미만", "detected": false, "detail": "string"}},
      {{"id": "ipr_pending", "label": "무효심판·IPR 계류", "detected": false, "detail": "string"}},
      {{"id": "no_pct", "label": "PCT/해외 출원 전무", "detected": false, "detail": "string"}}
    ],
    "marketPreview": {{
      "painPoints": ["string"],
      "cagr": null,
      "revenueModelDirection": "string"
    }},
    "gateRouting": {{
      "gate": "G1 | G2 | G3 | G4",
      "score": 0,
      "rationale": "string",
      "recommendedReports": ["R1_investment"],
      "rescreenConditions": ["string"]
    }}
  }}
}}

[Gate 판정]
G1: 80+ (즉시 진행)
G2: 70-79 (조건부 진행)
G3: 60-69 (보류)
G4: <60 (중단)
"""


def _rule_fallback_screening(pcml_data: dict) -> dict:
    """LLM 없이 PCML 데이터에서 SCR 결과를 규칙으로 추론한다."""
    shared = pcml_data.get("shared_variables", {})
    patent_layer = pcml_data.get("patent_layer", {})

    core_nodes = int(shared.get("self_core_nodes") or
                     shared.get("tech_core_nodes", 0) + shared.get("market_core_nodes", 0)
                     + shared.get("business_core_nodes", 0) + shared.get("regulatory_core_nodes", 0))
    # 모든 비율 값은 0.0~1.0 범위로 클램핑 (LLM이 0~100 스케일로 반환할 수 있음)
    def _clamp01(v, default):
        if v is None:
            return default
        v = float(v)
        return v / 100.0 if v > 1.0 else v  # 100점 스케일 자동 변환

    support_cov = _clamp01(shared.get("support_coverage"), 0.0)
    black_box = _clamp01(shared.get("black_box_core_ratio"), 0.5)
    legal_status = _clamp01(shared.get("legal_status_score"), 0.5)
    family_cov = _clamp01(shared.get("family_coverage_rate"), 0.0)

    # 간이 점수 (0~100)
    score = int(
        core_nodes / max(core_nodes, 8) * 30
        + support_cov * 25
        + (1 - black_box) * 20
        + legal_status * 15
        + min(family_cov, 1.0) * 10
    )
    score = min(score, 100)

    gate = "G1" if score >= 80 else "G2" if score >= 70 else "G3" if score >= 60 else "G4"
    novelty_status = "NOVEL" if score >= 70 else "PARTIAL" if score >= 50 else "NOT_NOVEL"
    inventive_status = "INVENTIVE" if score >= 70 else "UNCLEAR"

    patent_number = (
        patent_layer.get("patent_info", {}).get("application_number", "")
        or patent_layer.get("patent_info", {}).get("publication_number", "")
    )
    applicant = patent_layer.get("patent_info", {}).get("applicant", "")
    ipc_codes = patent_layer.get("patent_info", {}).get("ipc_codes", [])

    return {
        "searchMethodology": {
            "databases": ["KIPRIS", "Google Patents", "Espacenet"],
            "queryStrings": ["규칙 기반 추론 (LLM 미사용)"],
            "totalHits": 0,
            "analyzedCount": 0,
        },
        "priorArt": {"patents": [], "nonPatent": []},
        "noveltyAnalysis": {
            "status": novelty_status,
            "details": "규칙 기반 추론 결과 (LLM 키 미설정)",
            "threateningClaims": [],
        },
        "inventiveStep": {
            "status": inventive_status,
            "details": "규칙 기반 추론 결과",
            "combinationRisk": "미평가",
        },
        "similarityScores": {"maxSimilarity": 0, "avgSimilarity": 0, "distribution": []},
        "whiteSpace": [],
        "section112Issues": [],
        "scrReport": {
            "mode": "basic",
            "patentBasicInfo": {
                "patentNumber": patent_number,
                "applicant": applicant,
                "ipcCodes": ipc_codes,
                "registered": legal_status >= 0.8,
                "remainingYears": None,
                "hasFamily": family_cov > 0,
            },
            "technicalSummary": {
                "inventionTitle": patent_layer.get("patent_info", {}).get("title", ""),
                "industryMapping": ", ".join(ipc_codes[:2]) if ipc_codes else "미분류",
                "technicalProblem": "LLM 없이 분석 불가",
                "technicalSolution": "LLM 없이 분석 불가",
                "coreNodes": [],
            },
            "pcmlStructure": {
                "spofCategory": "없음",
                "minCutCategory": "중간",
                "ciChecklist": [],
            },
            "kpiRatings": {
                "kpi1_claimStrength": {
                    "grade": "上" if core_nodes >= 5 else "中" if core_nodes >= 3 else "下",
                    "reason": f"Core Node {core_nodes}개 기반 추정",
                },
                "kpi4_evasionResistance": {
                    "grade": "中" if black_box < 0.4 else "下",
                    "reason": f"Black-box 비율 {black_box:.0%} 기반 추정",
                },
                "kpi9_legalStability": {
                    "grade": "上" if legal_status >= 0.8 else "中" if legal_status >= 0.5 else "下",
                    "reason": f"법적상태 점수 {legal_status:.2f} 기반 추정",
                },
            },
            "hardStops": [
                {"id": "101_eligibility", "label": "§101/§29 특허 적격성", "detected": False, "detail": "미평가"},
                {"id": "spof", "label": "SPOF 발견", "detected": False, "detail": "미평가"},
                {"id": "remaining_life", "label": "잔여수명 3년 미만", "detected": False, "detail": "미평가"},
                {"id": "ipr_pending", "label": "무효심판·IPR 계류", "detected": False, "detail": "미평가"},
                {"id": "no_pct", "label": "PCT/해외 출원 전무", "detected": family_cov == 0, "detail": "패밀리 미탐지"},
            ],
            "marketPreview": {
                "painPoints": [],
                "cagr": None,
                "revenueModelDirection": "LLM 없이 추론 불가",
            },
            "gateRouting": {
                "gate": gate,
                "score": score,
                "rationale": f"규칙 기반 추론 (core_nodes={core_nodes}, support_cov={support_cov:.2f}, score={score})",
                "recommendedReports": ["R1_investment", "R9_sps"],
                "rescreenConditions": ["LLM 키 설정 후 재스크리닝 권장"],
            },
        },
        "_fallback": True,
    }


class ScreeningAgent(BaseAgent):
    """G1.6 — 3단계 신규성 스크리닝 에이전트 (PQE-SCR v4.0)."""

    stage_id = "G1.6-SCR"
    stage_name = "신규성·진보성 스크리닝"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          - pcml_result (dict): PCMLAgent.assess() 의 output_doc
          - scope (str): "basic" | "full" (기본값: "basic")
          - tech_id (str)
        """
        pcml_result = input_data.get("pcml_result", {})
        scope = input_data.get("scope", "basic")
        tech_id = input_data.get("tech_id", "")

        scr_data = self._run_screening(pcml_result, scope)

        scr_report = scr_data.get("scrReport", {})
        gate_routing = scr_report.get("gateRouting", {})
        score = float(gate_routing.get("score", 50))
        gate = gate_routing.get("gate", "G3")

        return StageResult(
            stage=self.stage_id,
            score=score,
            gate=gate,
            output_doc={
                "tech_id": tech_id,
                "scope": scope,
                "screening_version": 1,
                **scr_data,
            },
            next_actions=gate_routing.get("recommendedReports", []),
            warnings=(
                ["LLM 미사용 — 규칙 기반 폴백 결과"] if scr_data.get("_fallback") else []
            ),
        )

    def _run_screening(self, pcml_data: dict, scope: str) -> dict:
        """LLM 우선, 실패 시 규칙 폴백."""
        if not self._llm_client:
            return _rule_fallback_screening(pcml_data)

        prompt = _build_screening_prompt(pcml_data, scope)
        try:
            backend = getattr(self, "_llm_backend", "anthropic")
            if backend == "anthropic":
                message = self._llm_client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=8000,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = message.content[0].text.strip()
            elif backend == "groq":
                # llama-3.3-70b-versatile: 128k 컨텍스트, 12k output 지원
                # (llama-3.1-8b-instant는 6k TPM 한도로 SCR 프롬프트 초과)
                resp = self._llm_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    max_tokens=6000,
                    messages=[
                        {"role": "system", "content": "특허 스크리닝 분석가. JSON만 반환."},
                        {"role": "user", "content": prompt},
                    ],
                )
                raw = resp.choices[0].message.content.strip()
            else:
                raw = ""
            # JSON 추출 — 마크다운 코드블록 제거 후 파싱 시도
            raw = re.sub(r"```(?:json)?\s*", "", raw).strip()
            json_match = re.search(r"\{[\s\S]+\}", raw)
            if json_match:
                candidate = json_match.group()
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    # 불완전 JSON 자동 복구 시도: 열린 괄호 닫기
                    try:
                        open_b = candidate.count("{") - candidate.count("}")
                        open_sq = candidate.count("[") - candidate.count("]")
                        candidate += "]" * max(open_sq, 0) + "}" * max(open_b, 0)
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        pass
        except Exception as _e:
            import logging as _log
            _log.getLogger("screening").warning("LLM 스크리닝 실패 → 규칙 폴백: %s", _e)

        return _rule_fallback_screening(pcml_data)
