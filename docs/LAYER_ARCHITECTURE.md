# IPInsight PCML 2.0 — 4레이어 아키텍처 정의서
> 산출물 통합 문서: AI 모델 구조 정의서 · 데이터·테이블 정의서 · 서비스·프롬프트 정의서 · PoC 검증 결과서

---

## Layer 1 — AI 모델 구조 정의서

### 기능 분류 × 구현 위치

| 기능 | 방식 | 구현 파일 | 모델 |
|------|------|----------|------|
| 질의응답 (QA) | RAG + LLM | `pipeline/rag_retriever.py` + `BaseAgent._rag()` | claude-haiku-4-5 |
| 요약 (Summary) | LLM | `BaseAgent._llm()` | claude-haiku-4-5 |
| 생성 (Generation) | LLM + 템플릿 | 각 Agent `_build_output()` | claude-haiku-4-5 |
| 매칭 (Matching) | 벡터 유사도 | `RAGIndex.search()` (TF-IDF 코사인) | 로컬 (외부 의존 0) |

### RAG 파이프라인 흐름

```
knowledge/*.json (9개)
      ↓ KnowledgeBaseLoader.load_all()
  청크 분할 (400 tokens, 80 overlap)
      ↓ _NumpyEmbedder.fit()
  TF-IDF 벡터 인덱스 (RAGIndex)
      ↓ RAGIndex.search(query, top_k=5)
  유사 청크 반환 → build_rag_context()
      ↓
  [지식베이스 참조 컨텍스트] 블록
      ↓ BaseAgent._llm(prompt + context)
  LLM 응답 (키 없으면 규칙기반 폴백)
```

### 폴백 계층 (외부 의존 없이 동작 보장)

```
1순위: Anthropic claude-haiku-4-5 (ANTHROPIC_API_KEY 설정 시)
2순위: 로컬 Ollama llama3 (OLLAMA_URL 설정 시, 향후 지원)
3순위: 규칙기반 폴백 (_rule_fallback) — 항상 동작
```

---

## Layer 2 — 데이터·테이블 정의서

### 6개 데이터 도메인

| 도메인 | 소스 | 갱신 주기 | 스키마 파일 |
|--------|------|----------|------------|
| 특허 (patent) | KIPRIS / USPTO / EPO | 일간 | `knowledge/schema.json` → domains.patent |
| 논문 (paper) | NTIS / NDSL / PubMed | 주간 | domains.paper |
| R&D 과제 (rd_project) | NTIS / NRF / IITP | 월간 | domains.rd_project |
| 기술거래 (tech_transfer) | KSTB / KIPO | 주간 | domains.tech_transfer |
| 시장 정보 (market_info) | KOTRA / IBISWorld | 분기 | domains.market_info |
| 지원 프로그램 (support_program) | 중기부 / KIAT | 월간 | domains.support_program |

### 분류 체계

- **기술 분야**: 국가과학기술표준분류(KSTIC) 10대 분야
- **IPC → 산업 도메인**: G06N(AI) / A01G(농업) / H01M(배터리) 등 자동 매핑
- **데이터 품질 규칙**: 필수 필드 4개 / 날짜 형식 YYYY-MM-DD / 통화 USD 기준

### 커넥터 로드맵

```
구현 예정: connectors/
  kipris_connector.py   — KIPRIS OpenAPI (특허)
  ntis_connector.py     — NTIS API (R&D·논문)
  kstb_connector.py     — 기술거래소 (기술거래)
  kotra_connector.py    — KOTRA (시장·수출)
```

---

## Layer 3 — 서비스·프롬프트 정의서

### 3대 자동 생성 서비스

#### ① 수요조사서 (`/service/demand-survey`)
**에이전트**: `DemandSurveyGenerator` (agents/g0_demand_survey.py)  
**프롬프트 구조**:
```
[기술 정보] tech_name + description + TRL
[RAG 컨텍스트] market_info 도메인 검색 결과 (top 4)
[수요 세그먼트] 산업별 표준 5개 유형
→ JSON: executive_summary / demand_segments / adoption_barriers / pilot_roadmap
```

#### ② SMK — 사업화시장키트 (`/service/smk`)
**에이전트**: `SMKGenerator` (agents/smk_generator.py)  
**프롬프트 구조**:
```
[시장 정보] TAM·SAM·SOM + 성장률
[경쟁 정보] 경쟁사 비교표 + 차별화 포인트
[RAG 컨텍스트] 경쟁·GTM 관련 지식베이스 (top 3)
→ JSON: positioning / gtm_plan / channel_strategy / pricing_rationale / sales_playbook
```

#### ③ 기술사업화 로드맵 (`/service/roadmap`)
**빌더**: `RoadmapBuilder` (pipeline/roadmap_builder.py)  
**알고리즘** (LLM 불필요, 결정론적):
```
TRL current → target: 각 단계별 표준 마일스톤 템플릿 적용
자금조달: TRL 트리거 기반 Bootstrap→Seed→SeriesA 시퀀스 자동 삽입
KPI: G3 시장분석(SOM) 결과에서 ARR 목표 자동 추출
리스크: 6개 표준 리스크 레지스터 (기술·시장·자금·IP·팀·규제)
```

### 전체 서비스 → 산출물 매핑

```
수요조사서 (G0-DS)
    ↓
SMK — 사업화시장키트 (SMK)
    ↓
PhaseGatePipeline G0~G10 + Gap 모듈
    ↓
기술사업화 로드맵 (Roadmap)
    ↓
IR Deck (G6-IR) + ESG 리포트 (G10-ESG)
    ↓
투자자 종합 보고서 (/ip/report)
```

---

## Layer 4 — PoC 검증 결과서

### 검증 체크리스트 (14개 항목)

| # | 카테고리 | 항목 | 기준 |
|---|---------|------|------|
| 1 | AI 모델 | LLM 폴백 | API 키 없어도 규칙기반 응답 반환 |
| 2 | AI 모델 | RAG 인덱스 빌드 | knowledge/*.json 청크 > 0개 인덱싱 |
| 3 | AI 모델 | RAG 검색 | 쿼리 → 유사 청크 반환, 컨텍스트 길이 > 50자 |
| 4 | 데이터 | knowledge/*.json 무결성 | 9개 파일 모두 JSON 파싱 성공 |
| 5 | 데이터 | 스키마 정의서 | schema.json 존재, 6개 도메인 확인 |
| 6 | 서비스 | 에이전트 임포트 | 16개 Agent 클래스 모두 임포트 성공 |
| 7 | 서비스 | 로드맵 빌더 | TRL3→9 마일스톤 5개 이상 생성 |
| 8 | 서비스 | 수요조사서 생성 | G0-DS stage + document_type 확인 |
| 9 | 서비스 | SMK 생성 | SMK stage + market_sizing 확인 |
| 10 | 서비스 | API /health | 서버 응답 status=ok |
| 11 | 서비스 | Gap 엔드포인트 등록 | 7개 /gap/* 엔드포인트 main.py에 존재 |
| 12 | 검증 | 테스트 파일 | tests/test_*.py 3개 이상 |
| 13 | 검증 | 온프레미스 요구사항 | requirements.txt + .env 존재 |
| 14 | 검증 | Python 버전 | Python 3.10+ |

### 실행 방법

```bash
# 단독 실행 (서버 불필요)
cd C:\IPinsight
python deploy/poc_checklist.py

# API 경유 실행 (서버 구동 후)
GET http://localhost:8100/verify/poc

# 결과 저장 위치
deploy/poc_report.json
```

### 온프레미스 전환 가이드

```bash
# 1. 설치 (외부 인터넷 연결 필요)
pip install -r requirements.txt

# 2. 환경 변수 (선택 — 없어도 폴백 동작)
cp .env.example .env
# ANTHROPIC_API_KEY=sk-ant-...  (LLM 고도화)
# KIPRIS_API_KEY=...             (실시간 특허 검색)

# 3. 서버 기동 (포트 8100)
PYTHONPATH=C:\IPinsight python -m uvicorn api.main:app --port 8100

# 4. 검증
python deploy/poc_checklist.py
```

---

## 전체 아키텍처 요약

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: AI 모델                                        │
│  LLM (claude-haiku) ←→ RAG (TF-IDF 벡터 인덱스)         │
│  폴백 계층: LLM → 규칙기반 (외부 의존 0 보장)            │
├─────────────────────────────────────────────────────────┤
│  Layer 2: 데이터                                         │
│  knowledge/*.json (9개) + schema.json (6개 도메인)       │
│  커넥터 예정: KIPRIS / NTIS / KSTB / KOTRA              │
├─────────────────────────────────────────────────────────┤
│  Layer 3: 서비스                                         │
│  수요조사서 → SMK → G0~G10 + Gap(10모듈) → 로드맵 → IR  │
│  엔드포인트: /service/* + /gap/* + /execution/* + /ip/*  │
├─────────────────────────────────────────────────────────┤
│  Layer 4: 검증                                           │
│  PoC 체크리스트 14항목 자동화 + 온프레미스 전환 가이드    │
│  GET /verify/poc → JSON 결과 + deploy/poc_report.json   │
└─────────────────────────────────────────────────────────┘
```
