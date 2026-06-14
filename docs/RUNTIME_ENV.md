# IPInsight — 구동환경 정의서 v1.0

## 1. 필수 소프트웨어

### Python 설치 경로 및 버전 확인

```powershell
# 버전 확인
C:\tools\python311\python.exe --version
# 예상 출력: Python 3.11.x

# pip 확인
C:\tools\python311\python.exe -m pip --version
```

### 핵심 의존성 패키지 (requirements.txt 기반)

```
# Web Framework
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9

# HTTP 클라이언트
httpx==0.27.0
aiohttp==3.9.5
requests==2.32.3

# LLM
anthropic==0.28.0

# 데이터 처리
pandas==2.2.2
pydantic==2.7.1
python-dotenv==1.0.1

# 캐시
diskcache==5.6.3

# 특허/XML 파싱
lxml==5.2.2
xmltodict==0.13.0

# 테스트
pytest==8.2.0
pytest-asyncio==0.23.6
pytest-cov==5.0.0
httpx==0.27.0  # TestClient용
```

### FastAPI·uvicorn 버전

| 패키지 | 버전 | 비고 |
|--------|------|------|
| fastapi | 0.111.0 | Pydantic v2 호환 |
| uvicorn | 0.29.0 | `[standard]` — websockets·httptools 포함 |
| python-dotenv | 1.0.1 | .env 자동 로드 |

---

## 2. 환경변수 전체 목록

```
C:\IPinsight\.env
```

| 변수명 | 현재값 | 상태 | 용도 | 미설정 시 동작 |
|--------|--------|------|------|----------------|
| `ANTHROPIC_API_KEY` | `sk-ant-****` | ✅ 활성 | Claude haiku-4-5 / sonnet-4-6 분석 엔진 | 규칙기반 요약 폴백 (LLM 비활성) |
| `ANTHROPIC_MODEL_FAST` | `claude-haiku-4-5` | ✅ | 단순 분류·태깅 (저비용) | 기본값 haiku-4-5 사용 |
| `ANTHROPIC_MODEL_DEEP` | `claude-sonnet-4-6` | ✅ | 심층 분석·보고서 생성 | 기본값 sonnet-4-6 사용 |
| `EPO_CLIENT_ID` | `IPInsight_****` | ✅ 활성 | EPO OPS OAuth2 클라이언트 ID | 특허 커넥터 비활성화 |
| `EPO_CLIENT_SECRET` | `****` | ✅ 활성 | EPO OPS OAuth2 시크릿 | 특허 커넥터 비활성화 |
| `EPO_TOKEN_URL` | `https://ops.epo.org/3.2/auth/accesstoken` | ✅ | 토큰 발급 엔드포인트 | 하드코딩 기본값 사용 |
| `FDA_API_KEY` | `****` | ✅ 활성 | FDA openFDA API 인증 | 익명(401) → 일일 1,000건 제한으로 강등 |
| `NTIS_API_KEY` | `yx6c98kg21bu649u2m8u` | ⏳ 승인대기 | 국가R&D 과제·논문 조회 | `resCd:3` 응답 → 빈 결과 반환, 경고 로그 |
| `NTIS_BASE_URL` | `https://api.ntis.go.kr/v1` | ✅ | NTIS API 베이스 URL | 하드코딩 기본값 사용 |
| `CACHE_DIR` | `C:\IPinsight\.rag_cache` | ✅ | 디스크 캐시 루트 경로 | `./.rag_cache` 폴백 |
| `CACHE_TTL_SHORT` | `3600` | ✅ | 단기 캐시 TTL (초) — 실시간성 높은 데이터 | 기본 3600s |
| `CACHE_TTL_LONG` | `86400` | ✅ | 장기 캐시 TTL (초) — 특허·논문 등 정적 데이터 | 기본 86400s |
| `APP_HOST` | `0.0.0.0` | ✅ | uvicorn 바인드 호스트 | 기본 `0.0.0.0` |
| `APP_PORT` | `8100` | ✅ | uvicorn 포트 | 기본 `8100` |
| `LOG_LEVEL` | `info` | ✅ | uvicorn 로그 레벨 | 기본 `info` |

### 무키 커넥터 (환경변수 불필요)

| 커넥터 | 엔드포인트 | 비고 |
|--------|-----------|------|
| UN Comtrade | `comtradeapi.un.org/public/v1` | 공개 엔드포인트 |
| OpenAlex | `api.openalex.org` | 이메일 헤더 권장 (`mailto=kyoyoung@gmail.com`) |
| WorldBank | `api.worldbank.org/v2` | 무인증 |
| ClinicalTrials | `clinicaltrials.gov/api/v2` | 무인증 |
| GLEIF | `api.gleif.org/api/v1` | 무인증 |
| ClimateTRACE | `api.climatetrace.org/v2` | 무인증 |
| EUDAMED | `ec.europa.eu/tools/eudamed` | 무인증 |

---

## 3. 서버 기동 절차

### 1단계 — 가상환경 진입

```powershell
# 가상환경 생성 (최초 1회)
C:\tools\python311\python.exe -m venv C:\IPinsight\.venv

# 가상환경 활성화
C:\IPinsight\.venv\Scripts\Activate.ps1

# 활성화 확인 (프롬프트 앞에 (.venv) 표시 확인)
python --version
# 출력: Python 3.11.x
```

### 2단계 — 의존성 설치

```powershell
# pip 업그레이드 후 패키지 설치
python -m pip install --upgrade pip
python -m pip install -r C:\IPinsight\requirements.txt

# 설치 확인
python -m pip show fastapi uvicorn anthropic
```

### 3단계 — 환경변수 로드 확인

```powershell
# .env 파일 존재 확인
Test-Path C:\IPinsight\.env

# 핵심 변수 로드 테스트 (Python 인라인)
python -c "
from dotenv import load_dotenv, dotenv_values
import os
load_dotenv('C:/IPinsight/.env')
keys = ['ANTHROPIC_API_KEY','EPO_CLIENT_ID','FDA_API_KEY','NTIS_API_KEY']
for k in keys:
    v = os.getenv(k, '')
    masked = v[:8] + '****' if len(v) > 8 else ('(미설정)' if not v else v)
    print(f'{k}: {masked}')
"
```

### 4단계 — 서버 기동

```powershell
# 방법 A: 직접 기동 (개발)
Set-Location C:\IPinsight
python -m uvicorn api.main:app --host 0.0.0.0 --port 8100 --reload --log-level info

# 방법 B: .env 자동 로드 포함 기동
$env:PYTHONPATH = "C:\IPinsight"
python -m uvicorn api.main:app --host 0.0.0.0 --port 8100 --env-file C:\IPinsight\.env

# 방법 C: 백그라운드 기동 (운영)
Start-Process python -ArgumentList "-m uvicorn api.main:app --host 0.0.0.0 --port 8100" `
  -WorkingDirectory C:\IPinsight -WindowStyle Hidden
```

### 5단계 — 헬스체크

```powershell
# 기본 헬스체크
Invoke-RestMethod -Uri http://localhost:8100/health

# 커넥터 상태 확인
Invoke-RestMethod -Uri http://localhost:8100/health/connectors | ConvertTo-Json -Depth 3

# API 문서 접근 확인
Start-Process "http://localhost:8100/docs"

# 예상 응답 (헬스체크)
# {
#   "status": "ok",
#   "version": "1.0.0",
#   "connectors": { "epo": "active", "fda": "active", "ntis": "pending" }
# }
```

---

## 4. API 한도 관리

| 커넥터 | 한도/일 | 한도/주 | 캐시 TTL | 초과 시 동작 |
|--------|---------|---------|----------|-------------|
| **EPO OPS** | ~357 req | 2,500 req | 86,400s (24h) | 429 → 지수 백오프(1·2·4분) → 캐시 반환 |
| **FDA openFDA** | 120,000 req | — | 3,600s (1h) | 429 → 1초 대기 후 1회 재시도 → 빈 결과 |
| **NTIS** | — | — | 86,400s (24h) | `resCd:3` → 승인 대기 경고 후 빈 배열 |
| **Anthropic API** | 토큰 기준 | — | 응답 캐시 없음 | 429 → 60초 대기 후 haiku 강등 |
| **UN Comtrade** | 100 req/h | — | 43,200s (12h) | 429 → 12시간 캐시 강제 사용 |
| **OpenAlex** | 100,000 req | — | 43,200s (12h) | 429 → 10초 대기 재시도 |
| **WorldBank** | 무제한 | — | 86,400s (24h) | 503 → 재시도 3회 |
| **ClinicalTrials** | 무제한 | — | 86,400s (24h) | 503 → 재시도 3회 |
| **GLEIF** | 60 req/분 | — | 86,400s (24h) | 429 → 60초 대기 |
| **ClimateTRACE** | 무제한 | — | 86,400s (24h) | 503 → 재시도 3회 |
| **EUDAMED** | 무제한 | — | 86,400s (24h) | 503 → 재시도 3회 |
| **Google Patents** | 비공개 | — | 86,400s (24h) | 503 → EPO OPS 자동 폴백 ⚡ |

### EPO 주간 한도 모니터링

```powershell
# 현재 주간 사용량 확인
Invoke-RestMethod -Uri http://localhost:8100/health/quota/epo

# 한도 임박(80%) 시 자동 경고 로그 확인
Get-Content C:\IPinsight\logs\quota_warn.log -Tail 20
```

---

## 5. 캐시 관리

### .rag_cache/ 디렉토리 구조

```
C:\IPinsight\.rag_cache\
├── epo\               # EPO 특허 검색 결과 (TTL: 24h)
│   ├── search_*.json
│   └── biblio_*.json
├── fda\               # FDA 의료기기·의약품 데이터 (TTL: 1h)
│   ├── device_*.json
│   └── drug_*.json
├── openalex\          # 논문·연구자 데이터 (TTL: 12h)
│   └── works_*.json
├── comtrade\          # 무역통계 (TTL: 12h)
│   └── hs_*.json
├── worldbank\         # 시장규모·GDP 지표 (TTL: 24h)
│   └── indicator_*.json
├── clinicaltrials\    # 임상시험 데이터 (TTL: 24h)
│   └── study_*.json
├── ntis\              # 국가R&D 과제 (TTL: 24h, 승인 후 활성)
│   └── project_*.json
├── gleif\             # 법인 식별 (TTL: 24h)
│   └── lei_*.json
└── _meta\             # 캐시 히트율·통계
    └── stats.json
```

### TTL별 자동 만료 정책

| TTL 유형 | 대상 커넥터 | 만료 후 동작 |
|----------|------------|-------------|
| **1h** (단기) | FDA | 다음 요청 시 API 재호출 후 갱신 |
| **12h** (중기) | OpenAlex, UN Comtrade | 만료 시 백그라운드 갱신 후 구 캐시 반환 |
| **24h** (장기) | EPO, WorldBank, NTIS, ClinicalTrials, GLEIF | 만료 시 동기 재호출, 실패 시 구 캐시 유지 |

### 캐시 관리 명령

```powershell
# 전체 캐시 크기 확인
Get-ChildItem C:\IPinsight\.rag_cache -Recurse | Measure-Object -Property Length -Sum |
  ForEach-Object { "총 캐시: {0:N2} MB" -f ($_.Sum / 1MB) }

# 만료 캐시만 삭제 (API 엔드포인트)
Invoke-RestMethod -Uri http://localhost:8100/cache/cleanup -Method Post

# 특정 커넥터 캐시 강제 삭제 (예: EPO)
Remove-Item C:\IPinsight\.rag_cache\epo\* -Force
# 또는
Invoke-RestMethod -Uri "http://localhost:8100/cache/clear?connector=epo" -Method Post

# 전체 캐시 초기화 (주의: 다음 요청 시 모든 API 재호출)
Remove-Item C:\IPinsight\.rag_cache\* -Recurse -Force
New-Item -ItemType Directory -Path C:\IPinsight\.rag_cache -Force

# 캐시 통계 조회
Invoke-RestMethod -Uri http://localhost:8100/cache/stats | ConvertTo-Json
```

---

## 6. 테스트 실행 방법

### 환경 준비

```powershell
Set-Location C:\IPinsight
C:\IPinsight\.venv\Scripts\Activate.ps1
```

### 단위 테스트 — 커넥터별

```powershell
# 전체 커넥터 단위 테스트
pytest tests/test_connectors.py -v

# 특정 커넥터만
pytest tests/test_connectors.py -v -k "epo"
pytest tests/test_connectors.py -v -k "fda"
pytest tests/test_connectors.py -v -k "openalex"

# NTIS (승인 대기 상태 — resCd:3 응답 처리 검증)
pytest tests/test_connectors.py -v -k "ntis" --tb=short
```

### E2E 파이프라인 테스트

```powershell
# 전체 E2E (서버 기동 상태 필요)
pytest tests/test_e2e_pipeline.py -v --timeout=120

# 단일 스테이지 테스트 (30초 제한)
pytest tests/test_e2e_pipeline.py -v -k "stage1" --timeout=30

# 오프라인 모드 (캐시만 사용, API 호출 없음)
$env:IPINSIGHT_OFFLINE = "1"
pytest tests/test_e2e_pipeline.py -v -k "cached"
Remove-Item Env:\IPINSIGHT_OFFLINE
```

### 커버리지 확인

```powershell
# HTML 리포트 생성
pytest tests/ --cov=api --cov-report=html:coverage_html --cov-report=term-missing

# 목표 커버리지 80% 미달 시 실패
pytest tests/ --cov=api --cov-fail-under=80

# 리포트 열기
Start-Process C:\IPinsight\coverage_html\index.html
```

### 빠른 스모크 테스트

```powershell
# 서버 기동 후 핵심 엔드포인트 확인 (30초 이내)
pytest tests/test_smoke.py -v --timeout=30 -x
```

---

## 7. 트러블슈팅

### EPO 403 — OAuth2 토큰 만료

**증상**: `403 Forbidden`, `{"error":"invalid_client"}`

```powershell
# 원인: Bearer 토큰 만료 (유효기간 20분)
# 해결: 토큰 캐시 삭제 후 자동 재발급 트리거
Invoke-RestMethod -Uri http://localhost:8100/cache/clear?connector=epo_token -Method Post

# 수동 토큰 재발급 확인
python -c "
import httpx, os
from dotenv import load_dotenv
load_dotenv('C:/IPinsight/.env')
r = httpx.post(
    'https://ops.epo.org/3.2/auth/accesstoken',
    data={'grant_type': 'client_credentials'},
    auth=(os.getenv('EPO_CLIENT_ID'), os.getenv('EPO_CLIENT_SECRET'))
)
print(r.status_code, r.json().get('token_type'), 'expires_in:', r.json().get('expires_in'))
"
# 기대 출력: 200 Bearer expires_in: 1199
```

**예방**: 토큰 만료 60초 전 자동 갱신 로직 (`api/connectors/epo.py` `_refresh_token_if_needed()`)

---

### Google Patents 503 — EPO OPS 자동 폴백

**증상**: `503 Service Unavailable` (간헐적)

```
동작 흐름:
Google Patents 503
  → 자동 폴백: EPO OPS 쿼리 변환 실행
  → 로그: [WARN] Google Patents 503, fallback to EPO OPS
  → 결과: EPO 데이터로 대체 반환
```

```powershell
# 폴백 로그 확인
Select-String -Path C:\IPinsight\logs\app.log -Pattern "fallback to EPO" | Select-Object -Last 10

# Google Patents 상태 강제 확인
Invoke-RestMethod -Uri http://localhost:8100/health/connectors/google_patents
# {"status": "degraded", "fallback": "epo_ops", "last_503": "2026-06-14T..."}

# EPO 주간 한도 여유 확인 (폴백 트래픽 포함)
Invoke-RestMethod -Uri http://localhost:8100/health/quota/epo
```

---

### NTIS resCd:3 — 승인 대기

**증상**: API 응답 `{"resCd": "3", "resMsg": "인증키 승인 대기 중"}`

```powershell
# 현재 NTIS 키 상태 확인
python -c "
import httpx
r = httpx.get(
    'https://api.ntis.go.kr/v1/rnd/project',
    params={'apiKey': 'yx6c98kg21bu649u2m8u', 'pageSize': 1}
)
print(r.json().get('resCd'), r.json().get('resMsg'))
"
# resCd:3 → 대기 중 / resCd:0 → 승인 완료

# 승인 완료 후 조치
# 1. .env의 NTIS_API_KEY 값 유지 (이미 설정됨)
# 2. NTIS 캐시 초기화 (이전 빈 결과 제거)
Remove-Item C:\IPinsight\.rag_cache\ntis\* -Force
# 3. 커넥터 상태 재확인
Invoke-RestMethod -Uri http://localhost:8100/health/connectors/ntis
```

---

### OpenAlex Rate Limit — 요청 간격 조정

**증상**: `429 Too Many Requests`, 헤더 `X-RateLimit-Remaining: 0`

```powershell
# 원인: 분당 요청 과다 (페이지네이션 루프 등)
# 즉시 해결: 인터벌 강제 설정 (환경변수)
$env:OPENALEX_REQUEST_INTERVAL = "1.0"  # 요청 간 1초 대기

# 권장 설정 (.env에 추가)
# OPENALEX_MAILTO=kyoyoung@gmail.com
# → User-Agent: mailto:kyoyoung@gmail.com 헤더 자동 추가 → 우선 처리 큐

# 복구 확인 (10초 대기 후)
Start-Sleep -Seconds 10
Invoke-RestMethod -Uri http://localhost:8100/health/connectors/openalex
```

---

### 일반 디버깅

```powershell
# 상세 로그 모드로 재기동
python -m uvicorn api.main:app --port 8100 --log-level debug 2>&1 | Tee-Object C:\IPinsight\logs\debug.log

# 최근 에러 로그 확인
Select-String -Path C:\IPinsight\logs\app.log -Pattern "ERROR|CRITICAL" | Select-Object -Last 20

# 포트 충돌 확인
netstat -ano | findstr :8100
```

---

## 8. 모니터링 지표

### 목표 지표

| 지표 | 목표 | 경보 임계 | 측정 방법 |
|------|------|----------|----------|
| 캐시 히트율 | >80% | <60% | `GET /health/cache/stats` |
| API 오류율 | <5% | >10% | `GET /health/error-rate` |
| 응답시간 (단일 스테이지) | <30초 | >45초 | `GET /health/latency` |
| EPO 주간 사용량 | <80% (2,000/2,500) | >90% | `GET /health/quota/epo` |
| FDA 일일 사용량 | <80% (96,000/120,000) | >90% | `GET /health/quota/fda` |

### 지표 조회 명령

```powershell
# 종합 대시보드 (JSON)
Invoke-RestMethod -Uri http://localhost:8100/health/metrics | ConvertTo-Json -Depth 4

# 캐시 히트율
Invoke-RestMethod -Uri http://localhost:8100/cache/stats |
  Select-Object -ExpandProperty hit_rate

# API 커넥터별 오류율
Invoke-RestMethod -Uri http://localhost:8100/health/error-rate | ConvertTo-Json

# 응답시간 퍼센타일 (p50/p95/p99)
Invoke-RestMethod -Uri http://localhost:8100/health/latency | ConvertTo-Json
```

### 일일 상태 점검 스크립트

```powershell
# C:\IPinsight\scripts\daily_check.ps1
$base = "http://localhost:8100"
$metrics = Invoke-RestMethod "$base/health/metrics"

Write-Host "=== IPInsight 일일 점검 $(Get-Date -Format 'yyyy-MM-dd HH:mm') ==="
Write-Host "캐시 히트율: $($metrics.cache_hit_rate)%  (목표: >80%)"
Write-Host "API 오류율: $($metrics.api_error_rate)%  (목표: <5%)"
Write-Host "EPO 주간 사용: $($metrics.epo_weekly_used)/2500"
Write-Host "FDA 일일 사용: $($metrics.fda_daily_used)/120000"
Write-Host "NTIS 상태: $($metrics.ntis_status)"

if ($metrics.cache_hit_rate -lt 60) { Write-Warning "캐시 히트율 경보!" }
if ($metrics.api_error_rate -gt 10) { Write-Warning "API 오류율 경보!" }
```

---

**문서 버전**: v1.0 | **작성일**: 2026-06-14 | **환경**: Windows 11 / Python 3.11 / FastAPI 0.111.0 / Port 8100
