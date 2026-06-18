"""PCML (Platform Commercialization Markup Language) v3.0 통합 구조 분석 에이전트
기술·시장·사업·규제 4개 도메인을 통합하는 범용 구조화 언어.

출력: Part A(사람용 요약) + Part B(JSON 10계층)
계층:
  L1 Tech Graph   — 특허·기술 구성요소·TRL
  L2 Market Graph — 시장·고객·경쟁·채널
  L3 Business Graph — BM캔버스·수익·비용·파트너
  L4 Regulatory Graph — 규제·인증·관할·리스크
  L5 Support Layer — 근거 추적성
  L6 Metadata Layer — 정규화 메타데이터
  L7 Legal & Family Layer — 법적 상태·패밀리
  L8 Evidence Layer — 입증 가능성
  QC / Governance / KPI Inputs
"""
from __future__ import annotations
import json
import re
from .base_agent import BaseAgent, StageResult

# ══════════════════════════════════════════════════════════════
# 허용값 상수 — v3.0
# ══════════════════════════════════════════════════════════════

# 노드 유형: 도메인별 분류
_NODE_TYPES_TECH = {
    "Physical",    # 물리적 구성요소 (센서, 장치, 부품)
    "Logical",     # 논리적 개념 (알고리즘, 프로토콜)
    "Data",        # 데이터/신호 (입력값, 출력값, 파라미터)
    "Actor",       # 행위주체 (제어부, 사용자, 시스템)
    "Step",        # 프로세스 단계 (측정, 처리, 출력)
    "TechSpec",    # 기술 사양 (성능수치, 스펙, TRL 증거)
    "Material",    # 재료·물질 (원소, 화합물, 기판)
    # ── 특허 전용 ──
    "PatentRight", # 특허권 자체 (청구범위 단위가 아닌 IP 자산으로서의 특허)
                   # Physical/Logical과 구분: 기술구성요소가 아닌 IP 보호 객체
}
_NODE_TYPES_MARKET = {
    "MarketSegment",   # 시장 세그먼트 (B2B/B2C, 지역, 산업)
    "Customer",        # 고객 유형·페르소나 (대상 정의)
    "Competitor",      # 경쟁사/대체재
    "Product",         # 제품·솔루션·서비스
    "Channel",         # 유통·판매 채널
    "Pricing",         # 가격 모델·정책
    "Trend",           # 시장 트렌드·동인
    # ── 고객검증 전용 ──
    "Validation",      # 고객검증 결과 (인터뷰·PoC·파일럿·설문)
                       # Customer(대상)와 구분: Validation은 검증 활동·결과 자체
                       # evidence_layer와 구분: 노드로 구조화해야 다른 노드와 연결 가능
}
_NODE_TYPES_BUSINESS = {
    "ValueProp",       # 가치 제안
    "Revenue",         # 수익원·수익 모델
    "Cost",            # 비용 항목·원가 구조
    "Partner",         # 핵심 파트너·공급사
    "Activity",        # 핵심 활동
    "Resource",        # 핵심 자원
    "CustomerSegment", # 고객 세그먼트 (BM 맥락, market의 Customer와 중복 방지:
                       #   market=외부 시장관점, business=BM 내부 역할관점)
    "UnitEcon",        # 단위 경제성 (LTV, CAC, 마진)
    # ── 투자 전용 ──
    "Investor",        # 투자자 (VC, CVC, 정부, 엔젤)
                       # Partner와 구분: Partner=운영 파트너십, Investor=자본 제공자
    "FundingRound",    # 투자 라운드 (Seed, Series A, 정부과제, 기술보증)
                       # Revenue/Cost와 구분: 투자금은 영업활동 매출·비용이 아닌 자본 유입
}
_NODE_TYPES_REGULATORY = {
    "Regulation",      # 법률·시행령·고시 (강제성 있는 법규)
    "Certification",   # 인증·표준 (CE, FDA, KC, ISO)
    "Authority",       # 규제 기관 (FDA, 식약처, 특허청, 중기부)
    "Jurisdiction",    # 관할 지역·국가
    "Penalty",         # 벌칙·제재
    "Compliance",      # 준수 요건·절차
    "RegulatoryPath",  # 인허가 경로 (510k, PMA, EMA)
    # ── 정책 전용 ──
    "Policy",          # 정부 정책·지원사업·방향성 (강제성 없는 행정 지침)
                       # Regulation과 구분: Regulation=법적 강제(위반 시 제재),
                       #   Policy=정책 지원(이행 시 혜택, 미이행 시 제재 없음)
                       # 예: 스마트팜 확산 정책, K-바이오 육성전략, 농업직불제
}
_NODE_TYPES = (
    _NODE_TYPES_TECH | _NODE_TYPES_MARKET |
    _NODE_TYPES_BUSINESS | _NODE_TYPES_REGULATORY
)

# 노드 도메인 분류 맵
_DOMAIN_OF_NODE = {
    **{t: "technology"  for t in _NODE_TYPES_TECH},
    **{t: "market"      for t in _NODE_TYPES_MARKET},
    **{t: "business"    for t in _NODE_TYPES_BUSINESS},
    **{t: "regulatory"  for t in _NODE_TYPES_REGULATORY},
}

_ELEMENT_CLASSES = {"Core", "Supporting", "Peripheral"}

# 관계 유형: 도메인별 + 도메인 간
_RELATION_TYPES = {
    # ── 기술 내부 ──
    "includes", "has", "performs", "inputs", "receives", "outputs",
    "transmits", "controls", "based_on", "stores", "retrieves",
    "connected_to", "depends_on",
    # ── 시장 ──
    "targets",          # 제품 → 시장/고객
    "competes_with",    # 경쟁사 ↔ 제품
    "distributed_via",  # 제품 → 채널
    "serves",           # 제품 → 고객 세그먼트
    "substitutes",      # 경쟁사 → 제품 (대체)
    "priced_as",        # 제품 → 가격 모델
    # ── 사업 ──
    "enables",          # 기술/자원 → 가치제안
    "generates",        # 활동 → 수익
    "requires_resource","partnered_with",
    "drives",           # 비용동인 → 비용
    # ── 규제 ──
    "regulated_by",     # 제품 → 규제
    "requires_cert",    # 제품 → 인증
    "blocks",           # 규제 → 사업 (장벽)
    "operates_in",      # 제품 → 관할
    "penalizes",        # 규제 → 위반
    "certifies",        # 기관 → 인증
    # ── 도메인 간 ──
    "commercializes",   # 기술 → 제품/사업
    "protected_by",     # 제품 → 특허/IP (PatentRight)
    "valued_at",        # 기술/제품 → 가치
    "risks",            # 규제 → 기술/사업 리스크
    # ── 특허 연결 ──
    "covers",           # PatentRight → 기술 구성요소 (특허가 기술을 보호)
    "filed_for",        # PatentRight → 제품/사업 (사업화를 위한 출원)
    # ── 고객검증 연결 ──
    "validated_by",     # 제품/ValueProp → Validation (검증 완료)
    "invalidated_by",   # 제품/가설 → Validation (검증 실패)
    "supports_need",    # Validation → Customer (니즈 확인)
    # ── 투자 연결 ──
    "funded_by",        # 사업/Activity → FundingRound (투자 받음)
    "invested_in",      # Investor → FundingRound (투자자 참여)
    "requires_funding", # Activity/Resource → FundingRound (자금 필요)
    # ── 정책 연결 ──
    "governed_by",      # 시장/사업 → Policy (정책 적용 대상)
    "incentivized_by",  # 활동/제품 → Policy (정책 혜택 수혜)
    "aligned_with",     # 사업방향 → Policy (정책과 방향 일치)
}

# 속성 유형: 도메인별
_ATTR_TYPES = {
    # ── 기술 ──
    "algorithm", "decision_rule", "sequence_specificity", "binding_specificity",
    "genomic_position_specificity", "material", "range", "condition",
    "function", "ordinal", "reference", "formatting",
    "trl_level",        # TRL 1~9
    "performance_kpi",  # 성능 수치 (정확도, 속도 등)
    "tech_readiness",   # 기술 성숙도 근거
    # ── 시장 ──
    "market_size",      # TAM/SAM/SOM (USD, KRW)
    "growth_rate",      # CAGR (%)
    "market_share",     # 점유율 (%)
    "price_point",      # 가격대 (USD/월, 건당)
    "geography",        # 지역 (KR, US, SEA 등)
    "customer_pain",    # 고객 페인포인트
    # ── 사업 ──
    "revenue_model",    # SaaS/라이선스/중개/하드웨어
    "unit_economics",   # LTV, CAC, 마진율, 손익분기
    "ltv_cac_ratio",    # LTV/CAC 비율
    "gross_margin",     # 매출 총이익률 (%)
    "payback_period",   # 투자 회수 기간
    "scalability",      # 확장성 설명
    # ── 규제 ──
    "risk_level",       # Low | Medium | High | Critical
    "cert_status",      # Required | In Progress | Obtained | Waived
    "regulatory_pathway",  # 510k | CE MDR | KC | 식약처 등
    "compliance_deadline", # 준수 기한
    "penalty_amount",   # 위반 시 벌금/제재
    # ── 특허 ──
    "patent_no",        # 특허번호 (KR10-..., US..., EP...)
    "claim_scope",      # 청구범위 강도 (광범위/좁음/제한적)
    "ip_status",        # IP 상태 (등록/출원/거절/소멸)
    "filing_country",   # 출원 국가 목록
    # ── 고객검증 ──
    "validation_method",  # 검증 방법 (인터뷰/설문/PoC/파일럿/A-B테스트)
    "sample_size",        # 검증 대상 수 (인터뷰 N명, 파일럿 N농가)
    "nps_score",          # NPS (Net Promoter Score, -100~100)
    "validation_result",  # 검증 결론 (긍정/부정/혼합/미결)
    "willingness_to_pay", # 지불의사 확인 여부 및 금액
    # ── 투자 ──
    "investment_amount",  # 투자금액 (억원, USD)
    "valuation",          # 기업가치 (Pre/Post money, 억원)
    "equity_ratio",       # 지분율 (%)
    "investment_stage",   # 투자 단계 (Seed/A/B/C/IPO/정부과제)
    "funding_type",       # 자금 유형 (VC/정부/전략적투자/대출/크라우드)
    # ── 정책 ──
    "policy_ref",         # 정책명·고시번호 (예: 제4차 스마트팜 확산 기본계획)
    "support_amount",     # 지원 규모 (연간 예산, 과제당 최대 지원금)
    "policy_period",      # 정책 시행 기간
    "eligibility",        # 수혜 자격 조건
    "policy_alignment",   # 사업과의 정책 부합도 (High/Medium/Low)
    # ── 공통 ──
    "timeline",         # 기간 (분기, 연도)
    "kpi_value",        # 핵심 수치
    "source_citation",  # 출처 인용
    "confidence_basis", # 신뢰도 근거
}

_FUNCTION_TAGS = {
    "accuracy_improvement", "speed_improvement", "automation", "cost_reduction",
    "energy_saving", "safety_improvement", "compliance_support", "fault_reduction",
    "reliability_improvement", "prediction", "resource_optimization", "user_convenience",
    # v3.0 추가
    "market_expansion", "regulatory_compliance", "competitive_differentiation",
    "revenue_growth", "risk_mitigation", "customer_retention",
}
_LEGAL_STATUS = {"active", "lapsed", "invalidated", "pending", "opposed", "transferred", "disputed"}
_EVIDENCE_TYPES = {
    "product_log", "reverse_engineering", "test_data", "public_document",
    "purchase_record", "source_code", "official_disclosure",
    "market_survey", "expert_opinion", "pilot_result", "regulatory_filing",
}
_OBSERVABILITY_LEVELS = {
    "direct_measurement", "external_observation", "log_analysis",
    "reverse_engineering", "inferential_only",
}
_RELEASE_STATUS = {"releasable", "internal_only", "blocked"}

# 위험 수준
_RISK_LEVELS = {"Low", "Medium", "High", "Critical"}
# 인증 상태
_CERT_STATUSES = {"Required", "In Progress", "Obtained", "Waived", "Not Applicable"}

_PCML_SYSTEM = (
    "너는 PCML v3.0 (Platform Commercialization Markup Language) 통합 구조화 엔진이다. "
    "기술·시장·사업·규제 4개 도메인을 통합 구조화한다. "
    "반드시 Part A(사람용 요약)와 Part B(JSON) 두 부분을 모두 출력한다. "
    "JSON 파트는 ```json 코드펜스로 감싸서 출력한다."
)


def _build_v2_prompt(text: str, doc_id: str | None, input_mode: str) -> str:
    """PCML v3.0 통합 구조화 프롬프트 — 기술·시장·사업·규제 4도메인"""
    return f"""
너는 PCML v3.0 (Platform Commercialization Markup Language) 통합 구조화·검증 엔진이다.

입력 문서(특허·논문·사업계획서·시장보고서 등)를 받아
기술(Technology), 시장(Market), 사업(Business), 규제(Regulatory) 4개 도메인으로
구조화하고 품질관리·운영통제 결과를 생성하라.

────────────────
[0. 최상위 운영 목표]
────────────────
1. 4개 도메인 계층을 통합하여 사업화 판단을 지원하는 것이 최우선 목적이다.
2. 기술 도메인(L1 Tech Graph)은 특허·기술문서에서만 생성한다.
3. 시장·사업·규제 도메인은 입력 문서에 관련 내용이 있을 때 생성한다.
4. 도메인 간 연결(commercializes, protected_by, regulated_by 등)을 반드시 추출한다.
5. 허용되지 않은 node_type / relation_type / attr_type 사용 절대 금지.
6. QC를 반드시 수행하고 QC_confidence를 산출한다.
7. 모든 결과는 Part A(사람용 요약) + Part B(JSON)로 동시에 출력한다.

────────────────
[입력 정보]
────────────────
입력모드: {input_mode}
문서 ID: {doc_id or "unknown_doc_id"}

입력 문서:
{text}

────────────────
[도메인별 Node 허용 유형]
────────────────
기술(technology):
  Physical | Logical | Data | Actor | Step | TechSpec | Material
  + PatentRight  ← 특허권 자체 (청구항 구성요소가 아닌 IP 자산 단위)
                   예) "IoT 수확량 예측 특허(KR10-2345678)" 자체를 노드로 표현

시장(market):
  MarketSegment | Customer | Competitor | Product | Channel | Pricing | Trend
  + Validation   ← 고객검증 결과 (인터뷰·PoC·파일럿·설문 활동 및 결론)
                   ※ Customer(대상)와 구분: Validation은 검증 활동·결과 자체
                   예) "농가 30곳 PoC 검증(2026.03, NPS+42)" → Validation 노드

사업(business):
  ValueProp | Revenue | Cost | Partner | Activity | Resource | CustomerSegment | UnitEcon
  + Investor      ← 투자자 (VC·CVC·엔젤·정부펀드)
                    ※ Partner(운영협력)와 구분: Investor는 자본 제공자
  + FundingRound  ← 투자 라운드 (Seed·Series A·정부과제·기술보증)
                    ※ Revenue(매출)·Cost(비용)와 구분: 투자금은 자본 유입

규제(regulatory):
  Regulation | Certification | Authority | Jurisdiction | Penalty | Compliance | RegulatoryPath
  + Policy        ← 정부 정책·지원사업 (강제성 없는 행정 지침·인센티브)
                    ※ Regulation(법적 강제, 위반 시 제재)과 구분:
                      Policy는 이행 시 혜택, 미이행 시 제재 없음
                    예) "스마트팜 확산 기본계획", "농업기술실용화 R&D 지원"

모든 Node에 반드시 "domain" 필드 부여: technology | market | business | regulatory

────────────────
[중복 방지 규칙]
────────────────
· Customer(시장) vs CustomerSegment(사업): Customer=외부 시장 관점, CustomerSegment=BM 내 역할
· PatentRight(기술) vs Physical/Logical: 기술 구성요소는 Physical/Logical, 특허권 자산은 PatentRight
· Validation(시장) vs evidence_layer: evidence는 링크 추적용, Validation은 구조화 노드
· Investor(사업) vs Partner(사업): 자본 제공자=Investor, 운영 파트너십=Partner
· Policy(규제) vs Regulation(규제): 법적 강제=Regulation, 정책 지원=Policy

────────────────
[Link 허용 relation_type]
────────────────
기술 내부: includes | has | performs | inputs | receives | outputs | transmits |
          controls | based_on | stores | retrieves | connected_to | depends_on

특허 연결: covers (PatentRight→기술) | filed_for (PatentRight→제품/사업)

시장: targets | competes_with | distributed_via | serves | substitutes | priced_as

고객검증: validated_by (제품→Validation) | invalidated_by | supports_need (Validation→Customer)

사업: enables | generates | requires_resource | partnered_with | drives

투자: funded_by (사업→FundingRound) | invested_in (Investor→FundingRound) | requires_funding

규제: regulated_by | requires_cert | blocks | operates_in | penalizes | certifies

정책: governed_by (시장/사업→Policy) | incentivized_by (활동→Policy) | aligned_with

도메인 간: commercializes | protected_by | valued_at | risks

비표준 relation_type 절대 금지. 유사한 표준값으로 대체 후 QC WARN 기록.

────────────────
[Attribute 허용 attr_type]
────────────────
기술: algorithm | decision_rule | material | range | condition | function |
     ordinal | reference | trl_level | performance_kpi | tech_readiness

특허: patent_no | claim_scope | ip_status | filing_country

시장: market_size | growth_rate | market_share | price_point | geography | customer_pain

고객검증: validation_method | sample_size | nps_score | validation_result | willingness_to_pay

사업: revenue_model | unit_economics | ltv_cac_ratio | gross_margin |
     payback_period | scalability

투자: investment_amount | valuation | equity_ratio | investment_stage | funding_type

규제: risk_level | cert_status | regulatory_pathway | compliance_deadline | penalty_amount

정책: policy_ref | support_amount | policy_period | eligibility | policy_alignment

공통: timeline | kpi_value | source_citation | confidence_basis

────────────────
[QC 기준]
────────────────
FAIL:
1. Core Node 0개 (어떤 도메인이든)
2. element_class 미부여 Node/Link 1개 이상
3. linked_element_id 없는 Support 존재
4. domain 필드 누락 Node 1개 이상

WARN:
1. 도메인 간 cross-domain link 0개 (4도메인 모두 생성 시)
2. 비표준 relation_type 사용 시도
3. 시장 도메인 생성 시 market_kpi 미설정
4. 사업 도메인 생성 시 unit_economics 미설정
5. 규제 도메인 생성 시 risk_summary 미설정

Release Gate:
- releasable: QC_grade A 또는 B, confidence ≥ 70
- internal_only: QC_grade C 또는 confidence 50~69
- blocked: QC_grade D 또는 confidence < 50

────────────────
[출력 형식]
────────────────
[Part A. 사람용 요약]
1. 입력 문서 유형 및 분석 범위
2. 생성된 도메인 계층 (기술/시장/사업/규제)
3. 기술 도메인 핵심 요약 (Core Node/Link, TRL, 특허 핵심 청구범위)
4. 시장 도메인 핵심 요약 (TAM/SAM, 주요 고객, 경쟁 구도)
5. 사업 도메인 핵심 요약 (수익 모델, 단위 경제성, 핵심 파트너)
6. 규제 도메인 핵심 요약 (필요 인증, 주요 규제, 리스크 수준)
7. 도메인 간 연결 요약 (cross-domain links)
8. QC 결과 및 Release Gate
9. 해석 한계 및 다음 단계

[Part B. JSON]
최상위 키를 아래 구조로 출력. 추가 최상위 키 생성 금지.
```json
{{
  "tech_graph_layer": {{
    "doc_id": "{doc_id or 'unknown'}",
    "input_mode": "{input_mode}",
    "title": "string",
    "applicant": "string",
    "tech_field": "string",
    "core_idea": "string",
    "trl": 1,
    "filing_date": "string | null",
    "claims": [
      {{
        "claim_id": "C-001",
        "claim_no": 1,
        "claim_type": "independent | dependent",
        "claim_category": "장치 | 방법 | 시스템 | 기타",
        "depends_on": null,
        "claim_text": "string",
        "confidence_score": 0.9
      }}
    ],
    "nodes": [
      {{
        "node_id": "TN-001",
        "label": "string",
        "node_type": "Physical | Logical | Data | Actor | Step | TechSpec | Material",
        "domain": "technology",
        "element_class": "Core | Supporting | Peripheral",
        "observability": 75,
        "mandatory_flag": true,
        "function_tags": [],
        "confidence_score": 0.9
      }}
    ],
    "links": [
      {{
        "link_id": "TL-001",
        "src_node": "TN-001",
        "dst_node": "TN-002",
        "relation_type": "controls",
        "domain": "technology",
        "element_class": "Core",
        "confidence_score": 0.9
      }}
    ],
    "attributes": [
      {{
        "attr_id": "TA-001",
        "target_id": "TN-001",
        "attr_type": "trl_level | algorithm | range | performance_kpi | ...",
        "value": "string",
        "source_citation": "string | null",
        "confidence_score": 0.9
      }}
    ]
  }},
  "market_graph_layer": {{
    "market_kpi": {{
      "tam": "string (TAM 추정값 + 출처)",
      "sam": "string",
      "som": "string",
      "cagr": "string (연평균 성장률 %)",
      "target_geography": "string"
    }},
    "nodes": [
      {{
        "node_id": "MN-001",
        "label": "string",
        "node_type": "MarketSegment | Customer | Competitor | Product | Channel | Pricing | Trend",
        "domain": "market",
        "element_class": "Core | Supporting | Peripheral",
        "confidence_score": 0.8
      }}
    ],
    "links": [
      {{
        "link_id": "ML-001",
        "src_node": "MN-001",
        "dst_node": "MN-002",
        "relation_type": "targets | competes_with | distributed_via | serves | substitutes | priced_as",
        "domain": "market",
        "confidence_score": 0.8
      }}
    ],
    "attributes": [
      {{
        "attr_id": "MA-001",
        "target_id": "MN-001",
        "attr_type": "market_size | growth_rate | market_share | price_point | geography | customer_pain",
        "value": "string",
        "source_citation": "string | null",
        "confidence_score": 0.8
      }}
    ]
  }},
  "business_graph_layer": {{
    "unit_economics": {{
      "revenue_model": "string (SaaS/라이선스/중개 등)",
      "ltv": "string",
      "cac": "string",
      "gross_margin": "string (%)",
      "payback_period": "string"
    }},
    "nodes": [
      {{
        "node_id": "BN-001",
        "label": "string",
        "node_type": "ValueProp | Revenue | Cost | Partner | Activity | Resource | CustomerSegment | UnitEcon",
        "domain": "business",
        "element_class": "Core | Supporting | Peripheral",
        "confidence_score": 0.8
      }}
    ],
    "links": [
      {{
        "link_id": "BL-001",
        "src_node": "BN-001",
        "dst_node": "BN-002",
        "relation_type": "enables | generates | requires_resource | partnered_with | drives",
        "domain": "business",
        "confidence_score": 0.8
      }}
    ],
    "attributes": [
      {{
        "attr_id": "BA-001",
        "target_id": "BN-001",
        "attr_type": "revenue_model | unit_economics | ltv_cac_ratio | gross_margin | payback_period | scalability",
        "value": "string",
        "source_citation": "string | null",
        "confidence_score": 0.8
      }}
    ]
  }},
  "regulatory_graph_layer": {{
    "risk_summary": {{
      "overall_risk": "Low | Medium | High | Critical",
      "blocking_issues": ["string"],
      "key_certifications": ["string"],
      "estimated_timeline": "string"
    }},
    "nodes": [
      {{
        "node_id": "RN-001",
        "label": "string",
        "node_type": "Regulation | Certification | Authority | Jurisdiction | Penalty | Compliance | RegulatoryPath",
        "domain": "regulatory",
        "element_class": "Core | Supporting | Peripheral",
        "confidence_score": 0.8
      }}
    ],
    "links": [
      {{
        "link_id": "RL-001",
        "src_node": "RN-001",
        "dst_node": "RN-002",
        "relation_type": "regulated_by | requires_cert | blocks | operates_in | penalizes | certifies",
        "domain": "regulatory",
        "confidence_score": 0.8
      }}
    ],
    "attributes": [
      {{
        "attr_id": "RA-001",
        "target_id": "RN-001",
        "attr_type": "risk_level | cert_status | regulatory_pathway | compliance_deadline | penalty_amount",
        "value": "string",
        "source_citation": "string | null",
        "confidence_score": 0.8
      }}
    ]
  }},
  "cross_domain_links": [
    {{
      "link_id": "XL-001",
      "src_node": "TN-001",
      "dst_node": "MN-001",
      "relation_type": "commercializes | protected_by | valued_at | risks | regulated_by | requires_cert",
      "src_domain": "technology",
      "dst_domain": "market",
      "rationale": "string",
      "confidence_score": 0.8
    }}
  ],
  "support_layer": [
    {{
      "support_id": "S-001",
      "claim_id": "C-001",
      "linked_element_id": "TN-001",
      "support_type": "description | embodiment | drawing | effect | parameter",
      "support_text": "string",
      "support_strength": 0.7,
      "confidence_score": 0.85
    }}
  ],
  "metadata_layer": {{
    "jurisdiction": "KR | US | EP | CN | ...",
    "language": "ko | en",
    "document_type": "patent | paper | business_plan | market_report | mixed",
    "source_provenance": "string",
    "abstract": "string"
  }},
  "legal_family_layer": {{
    "legal_events": [],
    "family": []
  }},
  "evidence_layer": [],
  "shared_variables": {{
    "tech_core_nodes": 0,
    "market_core_nodes": 0,
    "business_core_nodes": 0,
    "regulatory_core_nodes": 0,
    "cross_domain_links_count": 0,
    "overall_trl": null,
    "market_attractiveness": null,
    "regulatory_risk": null
  }},
  "governance": {{
    "pcml_version": "3.0",
    "change_log_summary": [],
    "reviewer_note": "",
    "release_status": "internal_only"
  }},
  "qc": {{
    "fail_count": 0,
    "warn_count": 0,
    "qc_pass": true,
    "qc_grade": "A | B | C | D",
    "qc_confidence": 85,
    "issues_list": [],
    "qc_integrity_for_kpi": 85
  }},
  "analysis_limits": ["string"],
  "next_actions": ["string"]
}}
```

금지사항:
- 입력에 없는 수치·이름 상상 생성 금지 (수치가 없으면 null 또는 "정보 없음")
- 허용되지 않은 node_type / relation_type / attr_type 사용 금지
- domain 필드 누락 금지
- JSON 키 이름 변경 금지
- 시장조사 DB(PitchBook, IBISWorld 등) 직접 연동·인용 금지
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


def _rule_fallback_v3(text: str, doc_id: str | None, input_mode: str) -> dict:
    """LLM 없을 때 PCML v3.0 규칙기반 4도메인 최소 구조 생성"""
    did = doc_id or "unknown_doc_id"
    independent, dependent = _parse_claims_regex(text)
    all_claims = independent + dependent
    tech_nodes_raw = _extract_nodes_regex(independent)

    # 기술 노드에 domain 필드 추가
    tech_nodes = []
    for n in tech_nodes_raw:
        n["domain"] = "technology"
        n["node_id"] = n["node_id"].replace("N-", "TN-")
        tech_nodes.append(n)

    core_tech = [n for n in tech_nodes if n["element_class"] == "Core"]

    # 기술 내부 링크
    tech_links = []
    for i in range(len(core_tech) - 1):
        tech_links.append({
            "link_id": f"TL-{i+1:03d}",
            "src_node": core_tech[i]["node_id"],
            "dst_node": core_tech[i+1]["node_id"],
            "relation_type": "controls",
            "domain": "technology",
            "element_class": "Core",
            "confidence_score": 0.4,
        })

    # QC
    fail_count = 0 if core_tech else 1
    warn_count = 1
    qc_conf = min(55, max(0, 100 - fail_count * 20 - warn_count * 5))
    qc_grade = "C" if qc_conf >= 40 else "D"
    release_status = "internal_only" if qc_conf >= 50 else "blocked"

    return {
        "tech_graph_layer": {
            "doc_id": did,
            "input_mode": input_mode,
            "title": did,
            "applicant": "",
            "tech_field": "LLM 키 미설정 — 규칙기반 분석",
            "core_idea": "",
            "trl": None,
            "filing_date": None,
            "claims": all_claims,
            "nodes": tech_nodes,
            "links": tech_links,
            "attributes": [],
        },
        "market_graph_layer": {
            "market_kpi": {"tam": "정보 없음", "sam": "정보 없음", "som": "정보 없음",
                           "cagr": "정보 없음", "target_geography": "정보 없음"},
            "nodes": [], "links": [], "attributes": [],
        },
        "business_graph_layer": {
            "unit_economics": {"revenue_model": "정보 없음", "ltv": "정보 없음",
                               "cac": "정보 없음", "gross_margin": "정보 없음",
                               "payback_period": "정보 없음"},
            "nodes": [], "links": [], "attributes": [],
        },
        "regulatory_graph_layer": {
            "risk_summary": {"overall_risk": "Medium", "blocking_issues": [],
                             "key_certifications": [], "estimated_timeline": "정보 없음"},
            "nodes": [], "links": [], "attributes": [],
        },
        "cross_domain_links": [],
        "support_layer": [],
        "metadata_layer": {
            "jurisdiction": "KR" if str(did).upper().startswith("KR") else "unknown",
            "language": "ko",
            "document_type": "patent",
            "source_provenance": "직접입력",
            "abstract": "",
        },
        "legal_family_layer": {"legal_events": [], "family": []},
        "evidence_layer": [],
        "shared_variables": {
            # v3.0 도메인별 분해 키
            "tech_core_nodes": len(core_tech),
            "market_core_nodes": 0,
            "business_core_nodes": 0,
            "regulatory_core_nodes": 0,
            "cross_domain_links_count": 0,
            "overall_trl": None,
            "market_attractiveness": None,
            "regulatory_risk": None,
            # v2.0 하위 호환 키 (CLAUDE.md 9종 스펙 유지)
            "self_core_nodes": len(core_tech),
            "self_core_links": 0,
            "support_coverage": 0.0,
            "explicit_support_ratio": 0.0,
            "evidence_linkage_ratio": 0.0,
            "black_box_core_ratio": 0.5,
            "claim_clarity_penalty": 0,
            "legal_status_score": 0.5,
            "family_coverage_rate": 0.0,
        },
        "governance": {
            "pcml_version": "3.0",
            "change_log_summary": ["v3.0 초기 생성 (규칙기반 폴백)"],
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
                 "message": "LLM 키 미설정으로 규칙기반 분석 적용. 시장·사업·규제 도메인 미생성."},
                *([{"code": "FAIL-CORE", "severity": "FAIL",
                    "message": "Core Node 추출 실패"}] if not core_tech else []),
            ],
            "qc_integrity_for_kpi": qc_conf,
        },
        "analysis_limits": [
            "LLM 미사용 — 4도메인 중 기술 도메인만 부분 생성 (정규식 기반)",
            "시장·사업·규제 도메인은 ANTHROPIC_API_KEY 설정 후 재분석 시 생성",
        ],
        "next_actions": [
            "ANTHROPIC_API_KEY 설정 후 /ip/pcml 재호출",
            "사업계획서·시장보고서 추가 입력으로 시장·사업 도메인 보강 가능",
        ],
        "_summary": (f"규칙기반 v3.0: 기술 Core Node {len(core_tech)}개, "
                     f"청구항 {len(all_claims)}개. 시장·사업·규제 미생성."),
    }


# 하위 호환: 기존 호출자가 _rule_fallback_v2를 직접 호출하는 경우 대비
def _rule_fallback_v2(patent_text: str, patent_id: str | None, input_mode: str) -> dict:
    return _rule_fallback_v3(patent_text, patent_id, input_mode)


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


def _ensure_v2_compat_sv(data: dict) -> None:
    """LLM 출력 shared_variables에 v2.0 하위호환 키 보장 (in-place).
    CLAUDE.md 9종 스펙: self_core_nodes, self_core_links, support_coverage,
    explicit_support_ratio, evidence_linkage_ratio, black_box_core_ratio,
    claim_clarity_penalty, legal_status_score, family_coverage_rate
    """
    sv = data.setdefault("shared_variables", {})
    # v3.0 도메인 분해 키 기본값 먼저 설정 (Groq 부하 시 누락 방지)
    for key in ("tech_core_nodes", "market_core_nodes", "business_core_nodes", "regulatory_core_nodes"):
        sv.setdefault(key, 0)
    if "self_core_nodes" not in sv:
        sv["self_core_nodes"] = (
            sv.get("tech_core_nodes", 0) + sv.get("market_core_nodes", 0)
            + sv.get("business_core_nodes", 0) + sv.get("regulatory_core_nodes", 0)
        )
    if "self_core_links" not in sv:
        sv["self_core_links"] = sv.get("cross_domain_links_count", 0)
    for key, default in (
        ("support_coverage", 0.0), ("explicit_support_ratio", 0.0),
        ("evidence_linkage_ratio", 0.0), ("black_box_core_ratio", 0.5),
        ("claim_clarity_penalty", 0), ("legal_status_score", 0.5),
        ("family_coverage_rate", 0.0),
    ):
        sv.setdefault(key, default)


def _validate_and_repair(data: dict) -> dict:
    """PCML v3.0 규칙 검증 및 비허용값 자동 수정"""
    issues: list[dict] = data.get("qc", {}).get("issues_list", [])

    # 도메인별 노드/링크 검증 헬퍼
    def _check_nodes(nodes: list, prefix: str, default_type: str) -> None:
        for node in nodes:
            nid = node.get("node_id", "?")
            if node.get("element_class") not in _ELEMENT_CLASSES:
                node["element_class"] = "Supporting"
                issues.append({"code": "REPAIR-NODE-CLASS", "severity": "WARN",
                               "message": f"{prefix} {nid} element_class 비허용값 → Supporting 수정"})
            if node.get("node_type") not in _NODE_TYPES:
                node["node_type"] = default_type
            if not node.get("domain"):
                node["domain"] = _DOMAIN_OF_NODE.get(node.get("node_type", ""), "technology")
                issues.append({"code": "FAIL-DOMAIN", "severity": "FAIL",
                               "message": f"{prefix} {nid} domain 필드 누락 → 자동 설정"})
            ft = node.get("function_tags", [])
            node["function_tags"] = [t for t in ft if t in _FUNCTION_TAGS][:2]

    def _check_links(links: list, prefix: str) -> None:
        for link in links:
            lid = link.get("link_id", "?")
            if link.get("relation_type") not in _RELATION_TYPES:
                issues.append({"code": "WARN-RELATION", "severity": "WARN",
                               "message": f"{prefix} {lid} 비표준 relation_type '{link.get('relation_type')}' → controls"})
                link["relation_type"] = "controls"
            if link.get("element_class") not in _ELEMENT_CLASSES:
                link["element_class"] = "Core"

    def _check_attrs(attrs: list, prefix: str) -> None:
        for attr in attrs:
            if attr.get("attr_type") not in _ATTR_TYPES:
                attr["attr_type"] = "function"

    # 기술 도메인 (특허: PatentRight 포함)
    tgl = data.get("tech_graph_layer", {})
    _check_nodes(tgl.get("nodes", []), "tech_node", "Physical")
    _check_links(tgl.get("links", []), "tech_link")
    _check_attrs(tgl.get("attributes", []), "tech_attr")

    # 시장 도메인 (고객검증: Validation 포함)
    mgl = data.get("market_graph_layer", {})
    _check_nodes(mgl.get("nodes", []), "market_node", "MarketSegment")
    _check_links(mgl.get("links", []), "market_link")
    _check_attrs(mgl.get("attributes", []), "market_attr")

    # 사업 도메인 (투자: Investor, FundingRound 포함)
    bgl = data.get("business_graph_layer", {})
    _check_nodes(bgl.get("nodes", []), "biz_node", "ValueProp")
    _check_links(bgl.get("links", []), "biz_link")
    _check_attrs(bgl.get("attributes", []), "biz_attr")

    # 규제 도메인 (정책: Policy 포함)
    rgl = data.get("regulatory_graph_layer", {})
    _check_nodes(rgl.get("nodes", []), "reg_node", "Regulation")
    _check_links(rgl.get("links", []), "reg_link")
    _check_attrs(rgl.get("attributes", []), "reg_attr")

    # 도메인 간 링크 검증
    for xl in data.get("cross_domain_links", []):
        if xl.get("relation_type") not in _RELATION_TYPES:
            xl["relation_type"] = "commercializes"

    # governance release_status 검증
    gov = data.get("governance", {})
    if gov.get("release_status") not in _RELEASE_STATUS:
        gov["release_status"] = "internal_only"

    # Support linked_element_id 검증
    for sup in data.get("support_layer", []):
        if not sup.get("linked_element_id"):
            issues.append({"code": "FAIL-SUPPORT-LINK", "severity": "FAIL",
                           "message": f"support {sup.get('support_id')} linked_element_id 없음"})

    if "qc" in data:
        data["qc"]["issues_list"] = issues
    return data


class PCMLAgent(BaseAgent):
    """PCML v3.0 — 기술·시장·사업·규제 4도메인 통합 구조 분석 에이전트
    Platform Commercialization Markup Language v3.0 기반.
    input_mode: claim_only | full_spec | enriched | business_plan | market_report | mixed
    """
    stage_id = "G1.5-PCML"
    stage_name = "PCML v3.0 통합 구조 분석 (기술·시장·사업·규제)"

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data:
          patent_text / text: str   — 입력 문서 원문
          patent_id / doc_id: str   — 문서 ID
          input_mode: str           — claim_only | full_spec | enriched | business_plan | mixed
        """
        text = (input_data.get("patent_text") or input_data.get("text", ""))
        doc_id = (input_data.get("patent_id") or input_data.get("doc_id")
                  or input_data.get("tech_id"))
        input_mode = input_data.get("input_mode", "full_spec" if text else "claim_only")

        if not text:
            text = f"문서 ID {doc_id} — 원문 미제공 (input_mode: {input_mode})"

        result = self._run_pcml_v3(text, doc_id, input_mode)

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

    def _run_pcml_v3(self, text: str, doc_id: str | None, input_mode: str) -> dict:
        if self._llm_client is None:
            return _rule_fallback_v3(text, doc_id, input_mode)

        prompt = _build_v2_prompt(text, doc_id, input_mode)
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
                resp = self._llm_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    max_tokens=6000,
                    messages=[
                        {"role": "system", "content": _PCML_SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                )
                raw = resp.choices[0].message.content.strip()
            else:
                raise ValueError("LLM 클라이언트 없음")

            # Part A 요약 보존
            part_a = ""
            m = re.search(r"\[Part\s*A\..*?\](.+?)(?=\[Part\s*B\.|```json)", raw, re.DOTALL | re.IGNORECASE)
            if m:
                part_a = m.group(1).strip()

            data = _extract_json_from_llm(raw)
            data["_part_a_summary"] = part_a
            data = _validate_and_repair(data)
            _ensure_v2_compat_sv(data)
            return data

        except json.JSONDecodeError as e:
            fb = _rule_fallback_v3(text, doc_id, input_mode)
            fb["qc"]["issues_list"].append({"code": "FAIL-PARSE", "severity": "FAIL",
                                            "message": f"LLM JSON 파싱 실패: {e}"})
            fb["qc"]["fail_count"] += 1
            fb["qc"]["qc_confidence"] = max(0, fb["qc"]["qc_confidence"] - 20)
            fb["governance"]["release_status"] = "blocked"
            return fb
        except Exception as e:
            fb = _rule_fallback_v3(text, doc_id, input_mode)
            fb["qc"]["issues_list"].append({"code": "FAIL-LLM", "severity": "FAIL",
                                            "message": f"LLM 호출 실패: {e}"})
            return fb

    # 하위 호환
    def _run_pcml_v2(self, patent_text: str, patent_id: str | None, input_mode: str) -> dict:
        return self._run_pcml_v3(patent_text, patent_id, input_mode)

    # ── KPI 입력값 추출 헬퍼 ─────────────────────────────────

    def extract_kpi_inputs(self, pcml_result: dict) -> dict:
        """PCML v3.0 shared_variables → 기술사업화 KPI 입력값 변환"""
        sv = pcml_result.get("shared_variables", {})
        qc = pcml_result.get("qc", {})
        gov = pcml_result.get("governance", {})
        tgl = pcml_result.get("tech_graph_layer", {})
        mgl = pcml_result.get("market_graph_layer", {})
        rgl = pcml_result.get("regulatory_graph_layer", {})

        tech_core = sv.get("tech_core_nodes", 0)
        market_core = sv.get("market_core_nodes", 0)
        biz_core = sv.get("business_core_nodes", 0)
        reg_core = sv.get("regulatory_core_nodes", 0)
        cross_links = sv.get("cross_domain_links_count", 0)
        qc_conf = qc.get("qc_confidence", 50)

        # 통합 IP 강도 점수 (100점 만점)
        ip_strength = round(
            (min(tech_core, 8) / 8) * 35           # 기술 Core Node (35점)
            + (min(market_core, 5) / 5) * 20        # 시장 도메인 (20점)
            + (min(biz_core, 5) / 5) * 20           # 사업 도메인 (20점)
            + (min(reg_core, 3) / 3) * 15           # 규제 도메인 (15점)
            + (min(cross_links, 5) / 5) * 10,       # 도메인 간 연결 (10점)
            1,
        )

        # 키워드: 기술 Core 노드 레이블
        tech_keywords = [
            n.get("label", "")
            for n in tgl.get("nodes", [])
            if n.get("element_class") == "Core"
        ][:5]

        total_core = tech_core + market_core + biz_core + reg_core
        return {
            "ip_strength_score": ip_strength,
            "core_node_count": total_core,           # 하위호환 통합 카운트
            "tech_core_nodes": tech_core,
            "market_core_nodes": market_core,
            "business_core_nodes": biz_core,
            "regulatory_core_nodes": reg_core,
            "cross_domain_links": cross_links,
            "overall_trl": sv.get("overall_trl"),
            "market_attractiveness": sv.get("market_attractiveness"),
            "regulatory_risk": sv.get("regulatory_risk"),
            "market_kpi": mgl.get("market_kpi", {}),
            "regulatory_risk_summary": rgl.get("risk_summary", {}),
            "qc_confidence": qc_conf,
            "qc_grade": qc.get("qc_grade", "D"),
            "release_status": gov.get("release_status", "blocked"),
            "doc_id": tgl.get("doc_id"),
            "tech_field": tgl.get("tech_field", ""),
            "keywords": tech_keywords,
            "trl": sv.get("overall_trl"),
        }
