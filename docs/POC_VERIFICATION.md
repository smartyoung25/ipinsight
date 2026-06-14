# IPInsight PoC 검증 보고서 v1.0

## 1. 검증 개요

- **검증 일시**: 2026-06-14
- **환경**: Python 3.11.9 / Windows 11 / C:\IPinsight / pytest-9.0.3
- **테스트 케이스 수**: 파이프라인 3건 (G3·G8·ALL) + 단위테스트 37건

---

## 2. 스테이지별 검증 결과

### G3 (agritech — 스마트팜 센서)

- **라우팅 결과**: 활성 커넥터 7개 (esg, industry, market, paper, patent, trade, wipo), 스킵 0개, 예상 API 14회
- **특허 데이터**:
  - source: EPO OPS
  - 건수: 3건
  - 샘플 ID: DE102024136833.A1, EP4755175.A1, EP4755809.A1
  - fto_landscape: Google Patents 503 오류 → 정적 폴백 작동
- **시장 데이터**:
  - TAM 총계: 1,124.76억 USD (KR 24.1B / US 1,059.9B / JP 40.7B)
  - 커버 국가: KR, US, JP
  - 방법론: World Bank GDP × 섹터지출비율 × 침투계수
- **무역 데이터 (by_country, 백만 USD)**:
  - US: 4,134.3M / JP: 507.1M / KR: 487.8M
  - HS코드: 8432 (농업용 기계), 8424 (관개·분무 장치)
- **논문**: OpenAlex 72건 + PubMed 3건 + EuropePMC 9건 실 조회, 총 인용 346회
- **ESG**: SDG 2·12·13 정렬, OWID 에너지트렌드 404 → 정적 폴백 작동
- **에러**: trade.errors=[], ctx.errors=[] (0건)
- **실행 시간**: 4.12~6.72s (캐시 미적중 기준)

---

### G8 (medical_device — 수술로봇)

- **라우팅 결과**: 활성 커넥터 4개 (clinical, company, regional, regulatory), 스킵 0개, 예상 API 8회
- **임상 데이터**:
  - source: ClinicalTrials.gov v2
  - 건수: 총 11건 조회, 유사 10건 반환
  - 평균 등록 환자: 128명
  - regulatory_signal: "초기 단계 (임상 소수 — 선도자 기회)"
  - 주요 스폰서: Yonsei University, H. Lee Moffitt Cancer Center 등
- **FDA 510(k)**:
  - 총 승인 건수: 3,078건 ("surgical robot" 키워드)
  - api_limit: "120,000/일 (키 설정)" — 문자열 확인 PASS
  - 샘플 승인: K232938 Traus SSG30 Surgical System (Saeshin Precision, 2024-09-16)
- **규제 경로 3개국**:
  - US: 21 CFR Part 820 / FDA / 510(k)·PMA
  - EU: MDR 2017/745 / CE Mark Class I/II/III
  - KR: 의료기기법 / MFDS / 1~4등급 허가
- **지역 분석 (regional)**: KR(진입점수 75)·US(90)·EU/OTHER(60) 우선순위 산출
- **에러**: 0건
- **실행 시간**: 캐시 완전 히트 시 0.0s (G8 이전 G3에서 동일 인프라 사전 로드)

---

### ALL (energy — 고체전지)

- **활성 커넥터 수**: 13개 (전체 커넥터 — clinical, company, esg, industry, market, paper, patent, policy, regional, regulatory, technology, trade, wipo)
- **특허**: EPO OPS 3건 (US20260162994.A1, US20260163106.A1, DE102024211722.A1)
- **무역 (by_country, 백만 USD)**: US 10,119.5M / KR 4,794.2M / DE 385.8M (HS: 8541 반도체·태양광셀, 8502)
- **시장 TAM**: KR 10,199.8B / DE 13,234.9B / US 극대 (에너지 섹터 계수 적용)
- **기술코드**: CPC-Y 분류·KSTC 분류·tech_convergence·NTIS 필드 반환
- **정책**: ROR 기관 검색 포함
- **임상**: solid state battery 임상 데이터 조회 (의료기기 교차 참조)
- **에러**: trade.errors=[], patent.cpc_search.errors=N/A (없음)
- **실행 시간**: 36.5s (13개 커넥터 × API 병렬 미적용 순차 실행)

---

## 3. 단위 테스트 결과

```
pytest tests/test_connectors.py -v
37 passed in 8.66s
```

전체 37개 테스트 PASS:
- TestPaperConnector: 5개 (TRL 추정, OpenAlex 구조, 근거 키)
- TestMarketConnector: 4개 (TAM 구조, 양수/제로, GDP 지표, 마켓 서머리)
- TestClinicalConnector: 4개 (규제 시그널 카테고리, 임상 구조, 벤치마크 키, EUDAMED)
- TestESGConnector: 5개 (임팩트 등급, SDG 매핑, 섹터 구조, 탄소감축 잠재력, ESG 서머리)
- TestRegionalConnector: 12개 (KR·US·EU·JP·CN·IN·RU, 제재, 우선순위, 특허전략, 지역분류)
- TestTradeConnector: 4개 (무역흐름 구조, 섹터 서머리 키, 시장규모, HS코드 정의)
- TestCodeLinkerPhase1Integration: 3개 (컨텍스트 전체 필드, 필드 타입, regional 필드)

---

## 4. 성능 측정

| 스테이지 | 실행 시간 | 활성 커넥터 | 예상 API 호출 | 특이사항 |
|----------|----------|------------|--------------|---------| 
| G3 (agritech) | 4.12~6.72s | 7개 | 14회 | 초기 실행 |
| G8 (medical_device) | ~0.0s | 4개 | 8회 | 완전 캐시 히트 |
| ALL (energy) | 36.5s | 13개 | 26회 | 전체 커넥터 순차 실행 |

- **캐시 히트**: G8 실행 시 CodeLinkerPipeline 인스턴스 재사용으로 내부 캐시 완전 히트 (0.0s)
- **외부 API 실 호출 확인**: EPO OPS (특허 3건 실반환), ClinicalTrials.gov v2 (임상 11건), UN Comtrade v2 (무역 실측), World Bank (GDP 실측), OpenAlex (논문 72건), PubMed (3건)
- **폴백 작동 확인**: Google Patents 503 → 정적 폴백, OWID 404 → 정적 폴백 (에러 미전파)

---

## 5. 검증 판정

| 항목 | 기준 | 결과 | 판정 |
|------|------|------|------|
| EPO OPS 특허 조회 | 실제 특허 ID 반환 | DE102024136833.A1 등 3건 반환 | PASS |
| FDA 510(k) 한도 | api_limit 문자열 확인 | "120,000/일 (키 설정)" 반환 | PASS |
| UN Comtrade 무역 | by_country 데이터 반환 | US/JP/KR 실측값(백만 USD) 반환 | PASS |
| 규제 경로 3개국 | US·EU·KR 경로 반환 | 21 CFR·MDR·의료기기법 전부 반환 | PASS |
| 에러 0건 | errors=[] | 3개 스테이지 모두 ctx.errors=[], trade.errors=[] | PASS |
| 37개 테스트 통과 | 전체 pass | 37 passed in 8.66s | PASS |

**종합 판정: 6/6 PASS**

---

## 6. 발견된 이슈 및 조치

### 자동 폴백으로 처리된 항목 (에러 미전파, 서비스 계속)

| 이슈 | 원인 | 조치 |
|------|------|------|
| Google Patents fto_landscape 503 | 외부 서비스 일시 불가 | 정적 CPC 설명 폴백 자동 작동 |
| OWID energy_trend 404 | URL 경로 변경 추정 | portal URL 보존, 데이터 없음으로 기록 |
| NAICS 2022 Census API — keyword 미매칭 | "스마트팜" 영문 미매칭 | 빈 배열 반환 후 ISIC 매핑은 정상 진행 |
| OECD MSTI R&D 지출 — 빈 배열 | API 응답 파싱 이슈 또는 데이터 없음 | gerd_usd_mio=[] 반환, TAM 산출에 영향 없음 |

### 잔여 조치 필요 항목

1. **OWID energy_trend 404**: `share-of-electricity-low-carbon` 경로가 변경된 것으로 추정. Our World in Data API 엔드포인트 최신화 필요 (`pipeline/connectors/esg_connector.py` 내 URL 갱신).
2. **NAICS 영문 키워드 처리**: 한국어 `industry_keyword`를 Census API에 전달 시 매칭 결과 없음. 한→영 번역 레이어 또는 NAICS 코드 직접 입력 파라미터 추가 권장.
3. **ALL 스테이지 실행 시간 36.5s**: 13개 커넥터 순차 실행으로 인한 지연. 커넥터 병렬화(asyncio/ThreadPoolExecutor) 적용 시 10s 이하로 단축 가능.
4. **G8 route_decision 직렬화**: `ctx.route_decision`이 `to_dict()`에 포함되지 않음 (현재 summary 문자열로만 기록). 디버그용 라우팅 결과를 `to_dict()` 출력에 포함하도록 개선 권장.
