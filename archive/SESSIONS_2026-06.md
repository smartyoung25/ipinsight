# IPInsight 세션 아카이브 — 2026년 6월
> 이 파일은 자동으로 읽히지 않음. 참조 필요 시 명시적으로 요청할 것.

---

## 2026-06-14 (이번 세션): 사업화 납품물 3종 + 작업체계 재편

### 완료 작업

**analyze-chain NoneType 버그 수정 (screening_agent.py)**
- 원인: `dict.get("key", default)` — key가 None 값으로 존재하면 default 무시
- 수정: `or` 패턴 / `if ... is not None else` 패턴으로 전환
- 결과: POST /ip/analyze-chain 200 OK, 216 테스트 통과

**G5-CR 사업화 로드맵 (agents/g5_commercialization_roadmap.py, 신규)**
- KIAT/KEIT 협약 표준 + DOE Commercialization Plan 구조
- TRL 기반 Phase 자동 결정 (TRL<6→Phase1, <8→Phase2, <9→Phase3)
- 정부 프로그램 매칭: TIPS·KEIT R&D·SBIR·EIC·규제샌드박스
- KIAT 필수 KPI 5종 자동 생성

**G4 LoI 자동생성 (agents/g4_customer_validator.py 수정)**
- loi_count≥1 or poc_requests≥1 시 도입의향서 자동생성
- parties·technology_overview·poc_plan·commercial_intent·signature_block 포함
- TIPS/KEIT 제출용 안내 4개 포함

**G5 BM → SMK 자동 트리거 (agents/g5_bm_designer.py 수정)**
- Go 게이트: CommercializationRoadmap + SMKGenerator 자동 실행
- Hold 게이트: CommercializationRoadmap만 실행
- output_doc에 `commercialization_roadmap`·`smk` 키 추가

**신규 API 엔드포인트 (api/main.py)**
- POST /g5/assess (BM + 로드맵 + SMK 통합)
- POST /g5/roadmap (로드맵 단독)
- POST /g4/loi-template (LoI, loi_count<1·poc<1 시 422)
- POST /service/smk-from-pipeline (G3+G4+G5 통합 SMK)

**테스트 추가 (tests/test_connectors.py)**
- TestDeliverables 5개 추가: G5-CR 로드맵·G4 LoI·SMK 파이프라인
- 누계: 199 → 216개

**작업체계 재편 (4-Layer Architecture)**
- smart_farm CLAUDE.md: 463줄 → 120줄 (343줄 → archive/)
- smart_farm NEXT.md: 표준 템플릿 30줄
- IPinsight CLAUDE.md: 189줄 → 120줄
- IPinsight NEXT.md: 89줄 → 30줄 표준 템플릿
- archive/ 디렉토리 양 프로젝트 신설

---

## 2026-06-14 (이전): A급 달성 6개 차원 + 216 테스트

### 완료 작업
- G5 Unit Economics + LTV:CAC + NDR
- G5 Competitive Mapping (TAM/SAM/SOM)
- G7 PoC Platform Catalog
- G8 Supply Chain Auto-enrichment (MRL L4)
- G10 SQLite KPI Store (`pipeline/kpi_store.py`)
- G4 Interview Persistence (인터뷰 결과 저장·집계)
- POST /ip/analyze-chain (PCML → SCR 체인 엔드포인트)
- TestAGradeEndpoints 12개 테스트 전부 통과

---

## 2026-06-14 초기: PCML v2.0 + 인증 + ip-insight-handoff 이식

### Phase 1~4 완료 (53 → 163 테스트)
- JWT Bearer + API Key 인증 + rate limiting (api/auth.py + api/middleware.py)
- Pydantic 스키마 9종 (schemas.py) + 6개 새 엔드포인트
- structlog 미들웨어 + /metrics + BackgroundTasks 비동기 Job 큐
- Streamlit MVP 프론트엔드 (frontend/app.py)

### ip-insight-handoff 자산 이식 완료 (8/8)
| 자산 | Python 파일 |
|------|-------------|
| harness-pcml.ts | agents/pcml_agent.py (PCML v2.0 6계층) |
| kipris.ts | pipeline/connectors/kipris_connector.py |
| google-patents.ts | pipeline/connectors/google_patents_connector.py |
| reportDeps.ts | api/report_deps.py |
| r1~r9-*.ts | api/routers/reports.py |
| harness-screening.ts | agents/screening_agent.py (G1.6-SCR) |

### PCML v2.0 완성
- 6계층 L1~L6 구현
- LLM 없을 때 정규식 규칙 폴백 (v2.0 구조 준수)
- extract_kpi_inputs() → G1~G6 에이전트 재사용

### 인증 결정사항
- bcrypt==4.0.1 핀 (passlib 1.7.4)
- SHA-256 고정솔트 폴백
- 개발 모드 자동 통과 (JWT_SECRET_KEY + ADMIN_API_KEY 모두 미설정 시)
- 미들웨어 역순 실행 규칙 확인

### G0~G10 에이전트 전체 완성
- G6 가치평가: TRL<7→로열티구제법, TRL≥7→DCF, Monte Carlo
- G8 ARL: 5차원 + 병목원칙 (단일차원≤2→전체최대4)
- G10 BCG Matrix: IP강도35%+특허수명25%+TRL20%+ARL20%
- G9 Venture Client Model
- smk_generator.py: G3+G4+G5 통합 SMK

---

## 미결 사항 (다음 스프린트 후보)
- FTO 보고서 (Freedom-to-Operate) — G1 단계
- 클레임 차트 자동 생성
- 로열티 산정서 고도화
- 보고서 영속화: 인메모리 _report_store → SQLite
- KIPRIS 실키 테스트 (KIPRIS_API_KEY 필요)
- Streamlit MVP → 전체 흐름 UI (KIPRIS + PCML + SCR)
- Next.js 프론트엔드 (Firebase → 자체 DB 교체 선행 필요)
