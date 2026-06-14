"""PCML (Patent Claim Modeling Language) v2.0 청구항 구조 분석 에이전트
New PCML v2.0 전용 구조화·검증 엔진 기반 Python 구현.
ip-insight-handoff harness-pcml.ts 로직 통합.

출력: Part A(사람용 요약 15절) + Part B(JSON 6계층)
계층: L1 Patent | L2 Claim Graph | L3 Support | L4 Metadata | L5 Legal&Family | L6 Evidence
"""
from __future__ import annotations
import json
import re
from .base_agent import BaseAgent, StageResult

# ── 허용값 상수 ───────────────────────────────────────────────
_NODE_TYPES = {"Physical", "Logical", "Data", "Actor", "Step"}
_ELEMENT_CLASSES = {"Core", "Supporting", "Peripheral"}
_RELATION_TYPES = {
    "includes", "has", "performs", "inputs", "receives", "outputs",
    "transmits", "controls", "based_on", "stores", "retrieves",
    "connected_to", "depends_on",
}
_ATTR_TYPES = {
    "algorithm", "decision_rule", "sequence_specificity", "binding_specificity",
    "genomic_position_specificity", "material", "range", "condition",
    "function", "ordinal", "reference", "formatting",
}
_FUNCTION_TAGS = {
    "accuracy_improvement", "speed_improvement", "automation", "cost_reduction",
    "energy_saving", "safety_improvement", "compliance_support", "fault_reduction",
    "reliability_improvement", "prediction", "resource_optimization", "user_convenience",
}
_LEGAL_STATUS = {"active", "lapsed", "invalidated", "pending", "opposed", "transferred", "disputed"}
_EVIDENCE_TYPES = {
    "product_log", "reverse_engineering", "test_data", "public_document",
    "purchase_record", "source_code", "official_disclosure",
}
_OBSERVABILITY_LEVELS = {
    "direct_measurement", "external_observation", "log_analysis",
    "reverse_engineering", "inferential_only",
}
_RELEASE_STATUS = {"releasable", "internal_only", "blocked"}

_PCML_SYSTEM = (
    "너는 New PCML v2.0 전용 구조화·검증 엔진이다. "
    "반드시 Part A(사람용 요약)와 Part B(JSON) 두 부분을 모두 출력한다. "
    "JSON 파트는 ```json 코드펜스로 감싸서 출력한다."
)


def _build_v2_prompt(patent_text: str, patent_id: str | None, input_mode: str) -> str:
    return f"""
너는 New PCML v2.0 전용 구조화·검증 엔진이다.

특허 입력자료를 받아 New PCML의 설계원칙에 맞게 구조화하고,
계층 의존성·정규화·품질관리·운영통제까지 반영한 결과를 생성하라.

────────────────
[0. 최상위 운영 목표]
────────────────
1. L2 Claim Graph Layer를 모든 분석의 코어로 유지한다.
2. L1·L2는 필수 생성, L3~L6은 입력자료가 있을 때 생성한다.
3. 각 계층은 의존성 규칙을 반드시 따른다.
4. 정규화되지 않은 값, 임의 라벨, 임의 관계어 사용을 금지한다.
5. 모든 결과는 "사람용 요약(Part A) + 기계용 JSON(Part B)"으로 동시에 출력한다.
6. QC를 반드시 수행하고 QC_confidence를 산출한다.
7. QC_grade D 또는 confidence < 50이면 blocked 표시한다.
8. 이 결과는 구조적 분석 결과이며 최종 법적 해석을 대체하지 않는다.

────────────────
[입력 정보]
────────────────
입력모드: {input_mode}
특허번호: {patent_id or "unknown_patent_id"}

특허 원문:
{patent_text}

────────────────
[설계 원칙 요약]
────────────────
1. Claim Graph 중심성 — Patent-level 정보는 Claim Graph를 대체하지 않는다.
2. Support Traceability — linked_element_id 없는 support 허용 안 함.
3. Metadata Normalization — raw_value와 normalized_value 구분, WIPO ST.9 INID 우선.
4. Legal Operability — 권리상태·존속성·분쟁상태 포함.
5. Family Expandability — 패밀리 국가별 범위 차이 수용.
6. Enforcement Readiness — 실제 입증 가능성까지 표현.
7. Sentence-to-Requirement Structuring — 분석 기준은 필수요건 세트.
8. Element Class Traceability — 모든 Node/Link는 element_class 보유 (미부여=QC FAIL).
9. KPI Interoperability — shared variable과 confidence 전달 규칙 준수.

────────────────
[Node 허용 필드]
────────────────
- node_type: Physical | Logical | Data | Actor | Step
- element_class: Core | Supporting | Peripheral
- observability: 0(관측불가) | 25(블랙박스) | 50(역설계) | 75(외부관찰) | 100(직접측정)
- function_tags (최대 2개): accuracy_improvement | speed_improvement | automation |
  cost_reduction | energy_saving | safety_improvement | compliance_support |
  fault_reduction | reliability_improvement | prediction | resource_optimization | user_convenience
- mandatory_flag: true/false

────────────────
[Link 허용 relation_type]
────────────────
includes | has | performs | inputs | receives | outputs | transmits |
controls | based_on | stores | retrieves | connected_to | depends_on

임의 relation_type 절대 금지. 비표준 관계는 relation_mapping_ambiguous를 QC WARN에 기록 후 가장 가까운 표준값 사용.

────────────────
[Attribute 허용 attr_type]
────────────────
algorithm | decision_rule | sequence_specificity | binding_specificity |
genomic_position_specificity | material | range | condition | function |
ordinal | reference | formatting

────────────────
[Legal current_status 허용값]
────────────────
active | lapsed | invalidated | pending | opposed | transferred | disputed

────────────────
[kpi9_status_score 변환]
────────────────
active=100 | pending_annuity=85 | opposed=65 | pending_ipo=55 | lapsed=10 | invalidated=0

────────────────
[Evidence evidence_type 허용값]
────────────────
product_log | reverse_engineering | test_data | public_document |
purchase_record | source_code | official_disclosure

────────────────
[QC FAIL 조건]
────────────────
1. Core Node 1개 이상 미추출
2. 종속항 단절 링크 1개 이상
3. element_class 미부여 Node/Link 1개 이상
4. linked_element_id 없는 Support 존재 (L3 생성 시)
5. linked_element_id 없는 Evidence 존재 (L6 생성 시)

────────────────
[QC WARN 조건]
────────────────
1. unsupported Core 요소 존재
2. 비표준 relation_type 사용 시도
3. observability 미태깅 Core Node 존재
4. 중복 Node 존재
5. support mapping failure 존재
6. low_enforceability 존재
7. orphan 계층 객체 존재
8. taxonomy normalization ambiguous 존재
9. relation_mapping_ambiguous 존재
10. separate_but_similar 존재

────────────────
[Release Gate]
────────────────
- releasable: QC_grade A 또는 B, QC_confidence ≥ 70
- internal_only: QC_grade C 또는 confidence 50~69
- blocked: QC_grade D 또는 confidence < 50 ("외부 배포 금지" 명시)

────────────────
[출력 형식]
────────────────
반드시 아래 2부 형식으로 출력하라.

[Part A. 사람용 구조화 요약]
1. 분석모드 (Claim Graph Core | Claim Graph + Support | Claim Graph + Support + Metadata/Legal/Evidence)
2. 입력자료 범위
3. 생성된 계층 / 미생성 계층
4. 특허 개요
5. Claim 구조 요약
6. Core Node / Core Link / 필수 Attribute 요약
7. Support 상태 요약
8. Metadata 정규화 상태
9. Legal / Family 상태 요약
10. Evidence / Enforceability 상태 요약
11. Shared variables 요약
12. QC 결과
13. Release Gate 결과
14. 해석상 주의사항
15. 다음 단계 제안

[Part B. JSON]
반드시 최상위 키를 아래 구조로 출력. 추가 키 생성 금지.
```json
{{
  "patent_layer": {{
    "patent_id": "string",
    "source_provenance": "string",
    "jurisdiction": "string",
    "document_type": "string",
    "language": "string",
    "input_mode": "{input_mode}",
    "title": "string",
    "applicant": "string",
    "abstract": "string",
    "tech_field": "string",
    "core_idea": "string",
    "filing_date": "string | null",
    "registration_date": "string | null"
  }},
  "claim_graph_layer": {{
    "claims": [
      {{
        "claim_id": "C-001",
        "claim_no": 1,
        "claim_type": "independent | dependent",
        "claim_category": "장치 | 방법 | 시스템 | 매체 | 조성물 | 사용 | 기타",
        "depends_on": null,
        "claim_text": "string",
        "normalized_claim_text": "string",
        "syntax_type": "요소열거형 | Jepson형 | 특징형 | 관계설명형",
        "characterizing_clause": "string | null",
        "clarity_flags": [],
        "confidence_score": 0.9
      }}
    ],
    "nodes": [
      {{
        "node_id": "N-001",
        "label": "string",
        "normalized_label": "string",
        "node_type": "Physical | Logical | Data | Actor | Step",
        "role": "string",
        "element_class": "Core | Supporting | Peripheral",
        "observability": 75,
        "mandatory_flag": true,
        "function_tags": ["string"],
        "source_span": "string",
        "confidence_score": 0.9
      }}
    ],
    "links": [
      {{
        "link_id": "L-001",
        "src_node": "N-001",
        "dst_node": "N-002",
        "relation_type": "controls",
        "constraints": "string | null",
        "element_class": "Core | Supporting | Peripheral",
        "mandatory_flag": true,
        "source_span": "string",
        "confidence_score": 0.9
      }}
    ],
    "attributes": [
      {{
        "attr_id": "A-001",
        "target_type": "node | link",
        "target_id": "N-001",
        "attr_type": "decision_rule | range | material | function | ...",
        "value": "string",
        "normalized_value": "string | null",
        "scope": "필수 | 선택 | 예시",
        "mandatory_flag": true,
        "source_span": "string",
        "confidence_score": 0.9
      }}
    ],
    "dependency_tree": [
      {{"parent": null, "claim_id": "C-001", "children": ["C-002", "C-003"]}}
    ],
    "essential_requirement_set": {{
      "C-001": {{
        "core_nodes": ["N-001", "N-002"],
        "core_links": ["L-001"],
        "mandatory_attributes": ["A-001"]
      }}
    }}
  }},
  "support_layer": [
    {{
      "support_id": "S-001",
      "claim_id": "C-001",
      "linked_element_type": "node",
      "linked_element_id": "N-001",
      "support_type": "description | embodiment | drawing | effect | parameter",
      "source_section": "string",
      "paragraph_no": "string | null",
      "support_text": "string",
      "support_strength": 0.7,
      "explicitness_level": "explicit | partial | implicit | none",
      "enablement_flag": true,
      "written_description_flag": true,
      "reference_support": false,
      "confidence_score": 0.85
    }}
  ],
  "metadata_layer": [
    {{
      "metadata_id": "M-001",
      "inid_code": "11",
      "field_name": "application_number",
      "raw_value": "string",
      "normalized_value": "string | null",
      "source_location": "string",
      "confidence_score": 0.9
    }}
  ],
  "legal_family_layer": {{
    "legal_events": [
      {{
        "legal_event_id": "LE-001",
        "patent_id": "string",
        "jurisdiction": "string",
        "current_status": "active | lapsed | invalidated | pending | opposed | transferred | disputed",
        "kpi9_status_score": 100,
        "event_type": "registration | rejection | lapse | invalidation | opposition | transfer | annuity_warning | restoration",
        "event_date": "string | null",
        "term_end_date": "string | null",
        "annuity_status": "paid | overdue | grace_period | lapsed",
        "source_provenance": "string",
        "confidence_score": 0.8
      }}
    ],
    "family": []
  }},
  "evidence_layer": [
    {{
      "evidence_id": "E-001",
      "claim_id": "C-001",
      "linked_element_type": "node",
      "linked_element_id": "N-001",
      "evidence_type": "product_log | reverse_engineering | test_data | ...",
      "observability_level": "direct_measurement | external_observation | log_analysis | reverse_engineering | inferential_only",
      "acquisition_method": "string",
      "evidentiary_strength": 0.7,
      "admissibility_risk": "low | medium | high",
      "proof_cost": "low | medium | high",
      "jurisdiction_relevance": "string",
      "source_provenance": "string",
      "confidence_score": 0.8
    }}
  ],
  "shared_variables": {{
    "self_core_nodes": 0,
    "self_core_links": 0,
    "support_coverage": 0.0,
    "explicit_support_ratio": 0.0,
    "evidence_linkage_ratio": null,
    "black_box_core_ratio": 0.0,
    "claim_clarity_penalty": 0,
    "legal_status_score": null,
    "family_coverage_rate": null
  }},
  "governance": {{
    "structure_version": "1.0",
    "status_version": "1.0",
    "evidence_version": "1.0",
    "change_log_summary": [],
    "reviewer_note": "",
    "release_status": "internal_only"
  }},
  "qc": {{
    "fail_count": 0,
    "warn_count": 0,
    "qc_pass": true,
    "qc_grade": "A | B | C | D",
    "qc_confidence": 100,
    "issues_list": [
      {{"code": "string", "severity": "FAIL | WARN | INFO", "message": "string"}}
    ],
    "error_type_report": {{}},
    "qc_integrity_for_kpi": 100
  }},
  "analysis_limits": ["string - 해석 한계 및 주의사항"],
  "next_actions": ["string - 후속 조치 3~5개"]
}}
```

금지사항:
- 입력에 없는 메타데이터 상상 생성 금지
- 허용되지 않은 element_class / relation_type / attr_type 사용 금지
- "상기", "제1", "적어도 하나"를 Node로 만들지 말 것
- 같은 support 문장을 여러 요소 주 support로 중복 연결 금지
- JSON 키 이름 변경 금지
"""


# ── 규칙기반 폴백 ────────────────────────────────────────────

def _parse_claims_regex(patent_text: str) -> tuple[list[dict], list[dict]]:
    """청구항 번호 기반 정규식 파싱 — LLM 없을 때 사용"""
    claim_re = re.compile(
        r"(?:청구항|claim)\s*(\d+)[.）\s]+([\s\S]+?)(?=(?:청구항|claim)\s*\d+[.）\s]|$)",
        re.IGNORECASE,
    )
    dep_re = re.compile(r"(?:청구항|claim)\s*(\d+)에\s*(?:있어서|따른|기재된|의해)", re.IGNORECASE)

    independent, dependent = [], []
    for m in claim_re.finditer(patent_text):
        no = int(m.group(1))
        text = m.group(2).strip()
        dep = dep_re.search(text)
        if dep:
            dependent.append({
                "claim_id": f"C-{no:03d}", "claim_no": no,
                "claim_type": "dependent",
                "claim_category": "장치",
                "depends_on": int(dep.group(1)),
                "claim_text": text, "normalized_claim_text": text,
                "syntax_type": "요소열거형", "characterizing_clause": None,
                "clarity_flags": [], "confidence_score": 0.6,
            })
        else:
            independent.append({
                "claim_id": f"C-{no:03d}", "claim_no": no,
                "claim_type": "independent",
                "claim_category": "장치",
                "depends_on": None,
                "claim_text": text, "normalized_claim_text": text,
                "syntax_type": "요소열거형", "characterizing_clause": None,
                "clarity_flags": [], "confidence_score": 0.6,
            })
    return independent, dependent


def _extract_nodes_regex(independent_claims: list[dict]) -> list[dict]:
    """독립항에서 핵심 구성요소 추출 — 조사 기반"""
    nodes = []
    seen: set[str] = set()
    elem_re = re.compile(r"([가-힣a-zA-Z][가-힣a-zA-Z\s]{1,20}(?:부|기|기기|장치|수단|유닛|모듈|회로|서버|센서|부재|장|시스템|네트워크|인터페이스|엔진))")
    for cl in independent_claims:
        for i, m in enumerate(elem_re.finditer(cl["claim_text"])):
            label = m.group(1).strip()
            nl = re.sub(r"^(?:상기|제\d+|해당|전술한)\s*", "", label).strip()
            if nl and nl not in seen and len(nl) <= 20:
                seen.add(nl)
                nodes.append({
                    "node_id": f"N-{len(nodes)+1:03d}",
                    "label": label, "normalized_label": nl,
                    "node_type": "Physical",
                    "role": "구성요소",
                    "element_class": "Core" if i < 3 else "Supporting",
                    "observability": 75,
                    "mandatory_flag": i < 3,
                    "function_tags": [],
                    "source_span": f"{cl['claim_id']}",
                    "confidence_score": 0.5,
                })
    return nodes[:10]


def _rule_fallback_v2(patent_text: str, patent_id: str | None, input_mode: str) -> dict:
    """LLM 없을 때 v2.0 구조 규칙기반 생성"""
    pid = patent_id or "unknown_patent_id"
    independent, dependent = _parse_claims_regex(patent_text)
    all_claims = independent + dependent

    nodes = _extract_nodes_regex(independent)
    core_nodes = [n for n in nodes if n["element_class"] == "Core"]

    # 링크: 첫 Core 노드 → 다음 Core 노드 체인
    links = []
    for i in range(len(core_nodes) - 1):
        links.append({
            "link_id": f"L-{i+1:03d}",
            "src_node": core_nodes[i]["node_id"],
            "dst_node": core_nodes[i+1]["node_id"],
            "relation_type": "controls",
            "constraints": None,
            "element_class": "Core",
            "mandatory_flag": True,
            "source_span": "규칙기반 추론",
            "confidence_score": 0.4,
        })

    # QC — 규칙 폴백은 신뢰도 상한 60으로 제한 (LLM 없이 법적 해석 불가)
    fail_count = 0 if core_nodes else 1
    warn_count = 1  # LLM 미사용 항상 WARN
    qc_conf = min(60, max(0, 100 - fail_count * 20 - warn_count * 5))
    qc_grade = "B" if qc_conf >= 55 else "C" if qc_conf >= 40 else "D"
    release_status = ("releasable" if qc_grade in ("A","B") and qc_conf >= 70
                      else "internal_only" if qc_conf >= 50 else "blocked")

    # Essential requirement set
    ers: dict = {}
    for cl in independent:
        cid = cl["claim_id"]
        ers[cid] = {
            "core_nodes": [n["node_id"] for n in core_nodes],
            "core_links": [l["link_id"] for l in links],
            "mandatory_attributes": [],
        }

    # Shared variables
    sv = {
        "self_core_nodes": len(core_nodes),
        "self_core_links": len(links),
        "support_coverage": 0.0,
        "explicit_support_ratio": 0.0,
        "evidence_linkage_ratio": None,
        "black_box_core_ratio": 0.0,
        "claim_clarity_penalty": 0,
        "legal_status_score": None,
        "family_coverage_rate": None,
    }

    return {
        "patent_layer": {
            "patent_id": pid,
            "source_provenance": "직접입력",
            "jurisdiction": "KR" if str(pid).upper().startswith("KR") else "unknown",
            "document_type": "unknown",
            "language": "ko",
            "input_mode": input_mode,
            "title": pid,
            "applicant": "",
            "abstract": "",
            "tech_field": "LLM 키 미설정 — 규칙기반 분석 (ANTHROPIC_API_KEY 설정 후 재분석 권장)",
            "core_idea": "",
            "filing_date": None,
            "registration_date": None,
        },
        "claim_graph_layer": {
            "claims": all_claims,
            "nodes": nodes,
            "links": links,
            "attributes": [],
            "dependency_tree": [
                {"parent": None, "claim_id": c["claim_id"], "children": [
                    d["claim_id"] for d in dependent if d["depends_on"] == c["claim_no"]
                ]} for c in independent
            ],
            "essential_requirement_set": ers,
        },
        "support_layer": [],
        "metadata_layer": [],
        "legal_family_layer": {"legal_events": [], "family": []},
        "evidence_layer": [],
        "shared_variables": sv,
        "governance": {
            "structure_version": "1.0",
            "status_version": "1.0",
            "evidence_version": "1.0",
            "change_log_summary": ["v1.0 초기 생성 (규칙기반 폴백)"],
            "reviewer_note": "LLM 미사용 — 정밀도 제한. ANTHROPIC_API_KEY 설정 후 재분석 필요.",
            "release_status": release_status,
        },
        "qc": {
            "fail_count": fail_count,
            "warn_count": warn_count,
            "qc_pass": fail_count == 0,
            "qc_grade": qc_grade,
            "qc_confidence": qc_conf,
            "issues_list": [
                {"code": "WARN-LLM", "severity": "WARN",
                 "message": "LLM 키 미설정으로 규칙기반 분석 적용. 정밀도 제한."},
                *([{"code": "FAIL-CORE", "severity": "FAIL",
                    "message": "Core Node 추출 실패 — 청구항 원문 품질 확인 필요"}]
                  if not core_nodes else []),
            ],
            "error_type_report": {"WARN-LLM": 1, **({"FAIL-CORE": 1} if not core_nodes else {})},
            "qc_integrity_for_kpi": qc_conf,
        },
        "analysis_limits": [
            "LLM 미사용 — 청구항 해석 정확도 제한적",
            "L3 Support / L4 Metadata / L5 Legal / L6 Evidence 계층 미생성",
            "Node 추출은 정규식 기반이며 법적 청구범위 해석과 다를 수 있음",
        ],
        "next_actions": [
            "ANTHROPIC_API_KEY 설정 후 /ip/pcml 재호출로 LLM 분석 활성화",
            "KIPRIS 법적상태 조회 후 L5 Legal Layer 보강",
            "명세서(spec_text) 추가 입력으로 L3 Support 생성 가능",
            "patent_id 정규화 후 패밀리 조회 (L5 Family)",
        ],
        "_summary": f"규칙기반 분석: 독립항 {len(independent)}개, 종속항 {len(dependent)}개, Core Node {len(core_nodes)}개",
    }


def _extract_json_from_llm(text: str) -> dict:
    """LLM 응답에서 JSON 추출 — 코드펜스 또는 raw JSON"""
    # ```json ... ``` 블록 추출
    fence = re.search(r"```json\s*([\s\S]+?)\s*```", text, re.IGNORECASE)
    if fence:
        return json.loads(fence.group(1))
    # 첫 번째 { 부터 마지막 } 까지
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return json.loads(text[start:end + 1])
    raise ValueError("JSON 블록 미발견")


def _validate_and_repair(data: dict) -> dict:
    """v2.0 규칙 검증 및 비허용값 자동 수정"""
    issues: list[dict] = data.get("qc", {}).get("issues_list", [])
    cgl = data.get("claim_graph_layer", {})

    # Node element_class 검증
    for node in cgl.get("nodes", []):
        if node.get("element_class") not in _ELEMENT_CLASSES:
            node["element_class"] = "Supporting"
            issues.append({"code": "REPAIR-NODE-CLASS", "severity": "WARN",
                           "message": f"node {node.get('node_id')} element_class 비허용값 → Supporting 수정"})
        if node.get("node_type") not in _NODE_TYPES:
            node["node_type"] = "Physical"
        ft = node.get("function_tags", [])
        node["function_tags"] = [t for t in ft if t in _FUNCTION_TAGS][:2]

    # Link relation_type 검증
    for link in cgl.get("links", []):
        if link.get("relation_type") not in _RELATION_TYPES:
            issues.append({"code": "WARN-RELATION", "severity": "WARN",
                           "message": f"link {link.get('link_id')} 비표준 relation_type '{link.get('relation_type')}' → controls 수정"})
            link["relation_type"] = "controls"
        if link.get("element_class") not in _ELEMENT_CLASSES:
            link["element_class"] = "Core"

    # Attribute attr_type 검증
    for attr in cgl.get("attributes", []):
        if attr.get("attr_type") not in _ATTR_TYPES:
            attr["attr_type"] = "function"

    # governance release_status 검증
    gov = data.get("governance", {})
    if gov.get("release_status") not in _RELEASE_STATUS:
        gov["release_status"] = "internal_only"

    # Support linked_element_id 검증
    for sup in data.get("support_layer", []):
        if not sup.get("linked_element_id"):
            issues.append({"code": "FAIL-SUPPORT-LINK", "severity": "FAIL",
                           "message": f"support {sup.get('support_id')} linked_element_id 없음"})

    # 수정된 issues 반영
    if "qc" in data:
        data["qc"]["issues_list"] = issues
    return data


class PCMLAgent(BaseAgent):
    """PCML v2.0 — 6계층 특허 청구항 구조 분석 에이전트
    New PCML v2.0 전용 구조화·검증 엔진 기반.
    input_mode: claim_only | full_spec | enriched
    """
    stage_id = "G1.5-PCML"
    stage_name = "PCML v2.0 청구항 구조 분석"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          patent_text: str    — 특허 원문 (claim_only / full_spec)
          patent_id:   str    — 특허번호 (KR10-..., US..., EP...)
          input_mode:  str    — claim_only | full_spec | enriched (기본: full_spec)
        """
        patent_text = input_data.get("patent_text", "")
        patent_id = input_data.get("patent_id") or input_data.get("tech_id")
        input_mode = input_data.get("input_mode", "full_spec" if patent_text else "claim_only")

        if not patent_text:
            patent_text = f"특허번호 {patent_id} — 원문 미제공 (input_mode: {input_mode})"

        result = self._run_pcml_v2(patent_text, patent_id, input_mode)

        # 점수 산출: QC confidence 기반
        qc = result.get("qc", {})
        score = float(qc.get("qc_confidence", 50))
        gate = self._gate_from_score(score)

        warnings = [i["message"] for i in qc.get("issues_list", []) if i.get("severity") == "WARN"]

        return StageResult(
            stage=self.stage_id,
            score=score,
            gate=gate,
            output_doc=result,
            next_actions=result.get("next_actions", []),
            warnings=warnings,
        )

    def _run_pcml_v2(self, patent_text: str, patent_id: str | None, input_mode: str) -> dict:
        if self._llm_client is None:
            return _rule_fallback_v2(patent_text, patent_id, input_mode)

        prompt = _build_v2_prompt(patent_text, patent_id, input_mode)
        try:
            backend = getattr(self, "_llm_backend", "anthropic")
            if backend == "anthropic":
                msg = self._llm_client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=16000,
                    system=_PCML_SYSTEM,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = msg.content[0].text.strip()
            elif backend == "groq":
                # llama-3.1-70b-versatile: 컨텍스트 8192 토큰 제한
                # input ~2.5k + output → output을 5000으로 제한
                resp = self._llm_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    max_tokens=5000,
                    messages=[
                        {"role": "system", "content": _PCML_SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                )
                raw = resp.choices[0].message.content.strip()
            else:
                raise ValueError("LLM 클라이언트 없음")


            # Part A 보존, Part B JSON 추출
            part_a = ""
            part_b_match = re.search(r"\[Part\s*A\..*?\](.+?)(?=\[Part\s*B\.|```json)", raw, re.DOTALL | re.IGNORECASE)
            if part_b_match:
                part_a = part_b_match.group(1).strip()

            data = _extract_json_from_llm(raw)
            data["_part_a_summary"] = part_a  # 사람용 요약 보존
            data = _validate_and_repair(data)
            return data

        except json.JSONDecodeError as e:
            fb = _rule_fallback_v2(patent_text, patent_id, input_mode)
            fb["qc"]["issues_list"].append({
                "code": "FAIL-PARSE", "severity": "FAIL",
                "message": f"LLM 응답 JSON 파싱 실패: {e}",
            })
            fb["qc"]["fail_count"] += 1
            fb["qc"]["qc_confidence"] = max(0, fb["qc"]["qc_confidence"] - 20)
            fb["governance"]["release_status"] = "blocked"
            return fb
        except Exception as e:
            fb = _rule_fallback_v2(patent_text, patent_id, input_mode)
            fb["qc"]["issues_list"].append({
                "code": "FAIL-LLM", "severity": "FAIL",
                "message": f"LLM 호출 실패: {e}",
            })
            return fb

    # ── 기술사업화 초기평가 연계 헬퍼 ─────────────────────────

    def extract_kpi_inputs(self, pcml_result: dict) -> dict:
        """PCML shared_variables를 기술사업화 KPI 입력값으로 변환
        G1~G6 에이전트에서 재사용 가능한 표준 인터페이스.
        """
        sv = pcml_result.get("shared_variables", {})
        qc = pcml_result.get("qc", {})
        pl = pcml_result.get("patent_layer", {})
        gov = pcml_result.get("governance", {})

        core_nodes = sv.get("self_core_nodes", 0)
        support_cov = sv.get("support_coverage", 0.0)
        black_box = sv.get("black_box_core_ratio", 0.0)
        qc_conf = qc.get("qc_confidence", 50)

        # IP 강도 점수 (S score 대용)
        ip_strength = round(
            (min(core_nodes, 8) / 8) * 40          # Core Node 수 (최대 40점)
            + support_cov * 30                       # Support 커버리지 (최대 30점)
            + (1 - black_box) * 20                   # 입증 가능성 (최대 20점)
            + (qc_conf / 100) * 10,                  # QC 신뢰도 (최대 10점)
            1,
        )

        return {
            "ip_strength_score": ip_strength,
            "core_node_count": core_nodes,
            "core_link_count": sv.get("self_core_links", 0),
            "support_coverage": support_cov,
            "explicit_support_ratio": sv.get("explicit_support_ratio", 0.0),
            "black_box_core_ratio": black_box,
            "legal_status_score": sv.get("legal_status_score"),
            "family_coverage_rate": sv.get("family_coverage_rate"),
            "qc_confidence": qc_conf,
            "qc_grade": qc.get("qc_grade", "D"),
            "release_status": gov.get("release_status", "blocked"),
            "patent_id": pl.get("patent_id"),
            "jurisdiction": pl.get("jurisdiction"),
            "tech_field": pl.get("tech_field", ""),
            "keywords": [
                n.get("normalized_label", "")
                for n in pcml_result.get("claim_graph_layer", {}).get("nodes", [])
                if n.get("element_class") == "Core"
            ][:5],
        }
