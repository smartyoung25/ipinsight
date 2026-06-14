# IPInsight — 통합 기술사업화 AI 구조설계서 v1.0

## 1. 시스템 개요

### 목적·비전·핵심가치

IPInsight는 연구소·대학·중소기업의 기술을 글로벌 시장으로 연결하는 AI 기반 기술사업화 운영체제(Agent OS)다. WIPO Lab-to-Market 방법론을 기반으로, 아이디어 발굴(G0)부터 Exit 전략(G10)까지 전주기를 단일 파이프라인으로 처리한다.

핵심가치: (1) 오픈 데이터 우선 — 무료 공공 API 13개를 실가동하여 초기 유료 DB 의존 없이 글로벌 분석 제공. (2) 측정 기반 결정 — 모든 Go/Hold/Kill 게이트는 0~100점 수치 스코어로 판정. (3) 비용 최적화 — QueryRouter가 매 요청마다 필요한 커넥터만 선택해 API 호출 70% 절감.

### G0~G10 Stage Gate 체계

| Stage | 이름 | 핵심 Agent |
|---|---|---|
| G0 | 수요조사·IDF | tech_scout, demand_survey, idf_generator |
| G1 | IP 구조화·포트폴리오 | ip_structurer, whitespace_analyzer, portfolio_strategist, trade_secret, patent_maintenance |
| G2 | TRL·특허성 검증 | trl_assessor, patentability_assessor, funding_planner |
| G3 | 시장 스캔 | market_scanner, ecosystem_matcher |
| G4 | 고객·팀 검증 | customer_validator, team_assessor |
| G5 | 비즈니스 모델 | bm_designer, unit_economics |
| G6 | 가치평가·IR | valuation_engine, ir_deck |
| G7 | PoC 관리 | poc_manager |
| G8 | MRL·ARL·규제 | mrl_arl_assessor, regulatory_roadmap |
| G9 | 딜 구조화 | deal_structurer |
| G10 | 경쟁·ESG·Exit·글로벌 | competitive_monitor, esg_impact, exit_strategy, global_ip_strategist, portfolio_optimizer, performance_tracker |

### 4계층 아키텍처

```
┌─────────────────────────────────────────────────┐
│  API / Output Layer  FastAPI port 8100           │
│  /api/v1/* · report_builder · SMK Generator     │
├─────────────────────────────────────────────────┤
│  Agent Layer  32개 G0~G10 Agent (base_agent.py) │
│  claude-haiku-4-5 기본 / sonnet-4-6 심화        │
├─────────────────────────────────────────────────┤
│  Pipeline Layer  code_linker · query_router      │
│  phase_gate_pipeline · rag_retriever             │
├─────────────────────────────────────────────────┤
│  Data Layer  13개 외부 API + 10개 Knowledge DB  │
│  .rag_cache/ TTL 캐싱                            │
└─────────────────────────────────────────────────┘
```

---

## 2. 계층별 상세 구조

### 2.1 Data Layer

**외부 API 커넥터 13개 (모두 실가동)**

| 커넥터 | 데이터 | TTL | API |
|---|---|---|---|
| patent | IPC/CPC 특허 패밀리 | 24h | EPO OPS → Google Patents 폴백 |
| paper | 논문·인용 | 24h | OpenAlex + EuropePMC |
| market | GDP·무역통계 | 168h | WorldBank + OECD |
| clinical | 임상시험·EU 규제 | 24h | ClinicalTrials + EUDAMED |
| esg | 탄소배출·기후 | 168h | ClimateTRACE + OWID |
| trade | HS코드 수출입 | 168h | UN Comtrade |
| company | 기업 식별자 | 168h | GLEIF (LEI) |
| wipo | PCT 출원 동향 | 720h | WIPO |
| technology | CPC-Y 기술분류 | 720h | 정적 매핑 |
| regulatory | CFR/CE/KFD 경로 | 720h | FDA openFDA + 정적 DB |
| industry | NAICS/ISIC | 720h | 정적 매핑 |
| policy | NTIS R&D 과제 | 720h | NTIS (승인대기) → ROR 폴백 |
| regional | 8개 지역 지식 | 2160h | Knowledge DB 정적 |

캐시 경로: `.rag_cache/{connector}/{key}.json`. TTL 초과 시 자동 재호출. 갱신 스케줄: patent/paper/clinical은 매일 새벽 2~4시, market/esg는 매주 일요일, regulatory/policy는 매월 1일, regional은 분기.

**Knowledge DB (10개 JSON 정적 파일)**

`/knowledge/` 디렉토리: `global_markets.json`, `country_programs.json`, `trl_framework.json`, `royalty_benchmarks.json`, `regulatory_paths.json`, `arl_framework.json`, `mrl_framework.json`, `portfolio_scoring.json`, `schema.json`, `competitive_database.json`. RAGRetriever가 인덱싱하여 Agent 쿼리 시 로컬 검색 제공.

---

### 2.2 Pipeline Layer

**CodeContext — 14필드 데이터 컨테이너**

`pipeline/code_linker.py`의 `@dataclass CodeContext`가 파이프라인 전체의 단일 데이터 버스 역할을 한다. 필드: `tech_id`(식별자), `patent`, `technology`, `wipo`, `industry`, `regulatory`, `company`, `policy`(G0~G1 특허·산업), `paper`, `market`, `clinical`, `esg`, `trade`(G2~G9 분석 데이터), `regional`(8개 지역), `route_decision`(디버그 로그). 모든 필드는 `dict` 기본값으로 부분 채움을 허용하며, `to_dict()`로 Agent에 직렬화 전달.

**QueryRouter — 동적 커넥터 선택**

`pipeline/query_router.py`. 입력: `stage(G0~G10)`, `tech_type`, `regions[]`. 출력: `RouteDecision(selected_connectors, ttl_policy, estimated_api_calls, rationale)`.

- `_STAGE_CONNECTOR_MAP`: Stage별 최소 커넥터 정의 (G0=3개, G2=4개, G10=3개 등)
- `_TECH_ADDON`: 의료기기→clinical+regulatory, 에너지→esg+market 등 기술유형 추가
- `_REGION_SKIP`: RU→clinical 스킵, DEV→company 스킵 등 지역별 제외
- 3-Tier 병렬 실행 계획: Tier1(로컬/캐시) → Tier2(외부 API) → Tier3(느린 API) 순서로 병렬 묶음

**PhaseGatePipeline — Stage Gate 실행 엔진**

`pipeline/phase_gate_pipeline.py`. `StageResult(score, gate, output_doc, next_actions, warnings)`를 각 Stage에서 반환. `gate ∈ {Go, Hold, Kill}`. score < 40 → Kill, 40~70 → Hold, 70+ → Go 기본 정책. 단일 Stage 실행(`/stage/{n}`)과 전체 파이프라인 실행(`/pipeline/full`) 모두 지원.

**RAGRetriever**

`pipeline/rag_retriever.py`. Knowledge DB 10개 JSON을 메모리 인덱스로 적재. Agent가 `royalty_benchmark(tech_type, region)`, `trl_criteria(stage)` 등으로 쿼리하면 로컬 검색 결과 반환. 외부 API 미호출.

---

### 2.3 Agent Layer

**공통 인터페이스 — base_agent.py**

모든 Agent는 `BaseAgent`를 상속하며 `stage_id`, `stage_name` 클래스 변수를 선언한다. LLM 호출 패턴: 점수 산정·데이터 파싱은 `claude-haiku-4-5`(속도 우선), IP 전략 서술·IR Deck 생성·SMK 종합 등 서술형 심화 분석은 `claude-sonnet-4-6` 사용. API 키는 `ANTHROPIC_API_KEY` 환경변수. Knowledge DB는 RAGRetriever를 통해 `KNOWLEDGE_DIR`에서 직접 로딩.

**32개 Agent 역할·의존관계**

| Agent | 주요 입력 | 주요 출력 | 핵심 커넥터 |
|---|---|---|---|
| g0_tech_scout | tech_id, keyword | 기술 후보 목록, TRL 초기 추정 | paper, market |
| g0_demand_survey | tech_id, region | 수요 인터뷰 프레임워크, 시장규모 추정 | market, trade, regional |
| g0_idf_generator | tech_scout 결과 | IDF(Invention Disclosure Form) 초안 | paper, wipo |
| g1_ip_structurer | IDF, patent | IPC/CPC 매핑, 독립항 구조 | patent, wipo |
| g1_whitespace_analyzer | patent | 공백 기술영역 지도 | patent, wipo |
| g1_portfolio_strategist | patent 포트폴리오 | 포트폴리오 점수, 우선 유지/포기 추천 | patent, market |
| g1_trade_secret | IDF | 영업비밀 vs 특허 판단 기준 | regulatory |
| g1_patent_maintenance | patent | 유지/포기/매각 스케줄 | royalty_benchmarks(KB) |
| g2_trl_assessor | tech, paper | TRL 1~9 점수, 근거 | paper, trl_framework(KB) |
| g2_patentability_assessor | IDF, patent | 특허성 점수, 선행기술 충돌 | patent, paper |
| g2_funding_planner | TRL, region | 정부 지원사업 매칭, 투자 단계 로드맵 | policy, country_programs(KB) |
| g3_market_scanner | tech_type, region | TAM/SAM/SOM, 경쟁사 지도 | market, trade, patent |
| g3_ecosystem_matcher | tech, industry | 파트너·채널 매칭 추천 | company, industry |
| g4_customer_validator | BM, region | I-Corps 고객 검증 프레임워크 | market, regional |
| g4_team_assessor | team | 팀 역량 점수, 부족 영역 | policy |
| g5_bm_designer | market, IP | 비즈니스 모델 캔버스, 수익모델 옵션 | market, royalty_benchmarks(KB) |
| g5_unit_economics | BM | LTV/CAC, 손익분기 시뮬레이션 | market |
| g6_valuation_engine | BM, patent, market | DCF·비교법·로열티법 3종 가치평가 | market, trade, company |
| g6_ir_deck | valuation 결과 | IR Deck JSON→PDF 구조 | esg, market |
| g7_poc_manager | TRL, BM | PoC 마일스톤, KPI 추적 템플릿 | company, policy |
| g8_mrl_arl_assessor | BM, region | MRL 1~9·ARL 1~7 점수 | regulatory, mrl/arl_framework(KB) |
| g8_regulatory_roadmap | tech_type, region | FDA/CE/MFDS 승인 경로 및 일정 | regulatory, clinical |
| g9_deal_structurer | valuation, IP | LOI·라이선스·JV 구조 옵션 | company, market, policy |
| g10_competitive_monitor | tech, region | 경쟁사 동향 실시간 알림 | patent, market |
| g10_esg_impact | BM, region | ESG 점수, 탄소발자국 추정 | esg, market |
| g10_exit_strategy | valuation, BM | M&A·IPO·라이선싱 Exit 시나리오 | company, market |
| g10_global_ip_strategist | patent, region | PCT 진입국 우선순위, 현지 전략 | patent, wipo, regional |
| g10_portfolio_optimizer | 전체 포트폴리오 | 포트폴리오 점수 최적화 | portfolio_scoring(KB) |
| g10_performance_tracker | 활동 이력 | KPI 실적 대비 목표 추적 | market |
| smk_generator | 전 Stage 결과 | SMK(Synthesis Multi-Knowledge) 종합보고서 | 전체 |

---

### 2.4 API/Output Layer

**FastAPI 엔드포인트 (port 8100)**

`api/main.py`. 주요 라우트:

- `GET /health` — 서비스 상태
- `GET /stages` — G0~G10 단계 목록
- `POST /stage/{stage_num}` — 단일 Stage 실행 (StageRequest)
- `POST /pipeline/full` — 전체 파이프라인 실행 (PipelineRequest)
- `POST /funding/match` — 정부·민간 자금 매칭 (FundingMatchRequest)
- `POST /roadmap` — 기술사업화 로드맵 생성
- Agent별 직접 호출 엔드포인트 (IDF, IP, 시장스캔, 가치평가, IR Deck 등)

**출력 형식**: `StageResult.to_dict()` → JSON 기본. `report_builder.py`가 JSON을 구조화 보고서로 변환. `g6_ir_deck`은 IR Deck 슬라이드 구조(JSON) 생성 후 PDF 렌더링 가능. `smk_generator`는 G0~G10 전 결과를 claude-sonnet-4-6으로 종합하여 SMK 보고서 출력.

---

## 3. 데이터 흐름도

```
사용자 입력
 tech_id="KAIST-2026-001"
 params={stage:"G3", tech_type:"medical_device", regions:["KR","US"]}
         │
         ▼
┌─────────────────────┐
│   QueryRouter       │  stage=G3 → patent+wipo+market+industry+trade
│   route()           │  tech_type=medical → +clinical+regulatory
│                     │  regions=KR+US  → 스킵 없음
│  → 7개 커넥터 선택  │  전체 13개 → 7개 선택 (46% 절감)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐     .rag_cache/ HIT?
│  CodeLinker         │ ──→ YES: 캐시 반환 (0 API 호출)
│  run(connectors)    │     NO : 외부 API 호출 → 캐시 저장
│                     │
│  CodeContext 채움   │  patent={...}, market={...},
│  (14필드 부분채움)  │  clinical={...}, trade={...} ...
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  PhaseGatePipeline  │
│  run_stage(G3)      │
│                     │
│  g3_market_scanner  │ → TAM/SAM/SOM, 경쟁 지도
│  g3_ecosystem_      │ → 파트너·채널 매칭
│    matcher          │
│                     │
│  StageResult(       │
│   score=78,         │
│   gate="Go",        │
│   output_doc={...}  │
│  )                  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  report_builder     │ → JSON 구조화 보고서
│  smk_generator      │ → SMK 종합 (sonnet-4-6)
│  api/main.py        │ → HTTP 200 응답
└─────────────────────┘
```

---

## 4. 기술 스택

| 분류 | 기술 | 용도 |
|---|---|---|
| Runtime | Python 3.11 | 전체 백엔드 |
| API 서버 | FastAPI + uvicorn | port 8100, 37개 엔드포인트 |
| LLM SDK | Anthropic SDK (anthropic) | claude-haiku-4-5 / sonnet-4-6 |
| HTTP | urllib (표준 라이브러리) | 외부 API 호출 (무의존성) |
| 환경변수 | python-dotenv | .env 파일 → 런타임 주입 |
| 캐시 | json 파일 (.rag_cache/) | TTL 기반 API 응답 캐싱 |
| 테스트 | pytest | 37개 단위·통합 테스트 |
| 문서화 | FastAPI 자동 Swagger | /docs |

---

## 5. 보안·품질 기준

**키 관리**: 모든 API 키(EPO_CLIENT_ID, EPO_CLIENT_SECRET, ANTHROPIC_API_KEY 등)는 `.env` 파일에 저장하고 `.gitignore`로 버전관리 제외. 런타임에 `os.environ.get()`으로만 참조. `base_agent.py`에서 `load_dotenv()` 자동 로드.

**데이터 격리**: PitchBook·IBISWorld 등 유료 상업 DB는 코드베이스에 영구 제외. 공공 API 및 자체 Knowledge DB만 사용. UN Comtrade 요청 시 개인 식별 정보 미포함.

**테스트 커버리지**: pytest 37개 테스트 통과 (단위: Agent별 스코어 산출, 통합: API 엔드포인트 응답, 파이프라인: Stage Gate 순서). CI 기준: 37개 전부 통과 시에만 배포.

**캐시 무결성**: TTL 초과 캐시는 재호출 전 삭제(덮어쓰기). API 오류 시 캐시 미갱신(stale 보존). `errors[]` 필드로 부분 실패 투명 기록.

---

## 6. 확장 로드맵

**Phase 3 유료 DB 연동 (수익 발생 후)**
- Crunchbase API ($49/월): `company` 커넥터에 GLEIF 병렬 소스로 추가. 스타트업 투자 이력, CrunchBase Rank 활용.
- Royalty Range ($300~/월): `royalty_benchmarks.json` 정적 DB를 실시간 라이선스 비교 데이터로 교체. `g5_bm_designer`, `g9_deal_structurer` 정확도 향상.
- Lens.org 상업 라이선스: 현재 무료 tier(IP 월 50회) → 무제한 특허 패밀리 검색.

**NTIS 국내 R&D 연동 (승인 대기 중)**
- 현재 `policy` 커넥터는 ROR(기관) 폴백 사용 중. NTIS API 키 승인 시 `regional_connector.py`에 자동 전환 로직 기구현. 국내 R&D 과제 번호 → 기술 연계 자동화.

**연합학습 (Flower FedAvg)**
- 현재 Agent 스코어 모델은 규칙 기반(Knowledge DB 가중치). Flower 도입 시 다수 기술사업화 케이스 축적 데이터로 FedAvg 보정. Smart Farm 프로젝트의 `pipeline/federated/` 구조 재사용 가능.

**멀티 테넌트 SaaS 전환**
- 현재 단일 인스턴스(포트 8100). FastAPI `Depends(get_tenant)` 패턴으로 기관별 Knowledge DB 파티셔닝 및 캐시 격리 확장 가능. JWT 인증 레이어 추가 시 B2B API 상품화.
