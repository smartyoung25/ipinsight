# IPInsight — 후속전환 패키지 v1.0

**기준일**: 2026-06-14 | **테스트**: 98 passed / 46s | **서버**: FastAPI v2.0.0 port 8100

---

## 1. 현재 → 상용화 전환 로드맵

### 즉시 실행 (D+0 ~ D+7)

**NTIS 키 연동**
- [ ] 승인 확인 즉시 `.env`에 `NTIS_API_KEY=<값>` 추가 (이미 설정됨 — 승인만 대기)
- [ ] `python -m pytest tests/test_connectors.py -q -k ntis` 로 연동 단독 검증
- [ ] `scheduled_refresh.py`의 `"regulatory"` job에 NTIS 작업 항목 추가 (현재 `_static_check`만 존재 — `scripts/scheduled_refresh.py` L79~85)

**EPO OPS 토큰 갱신 확인**
- [ ] `pipeline/code_linker.py`의 `PatentConnector` 토큰 만료 로직 확인 (20분 캐시 — 장시간 배치 시 만료 위험)
- [ ] G3 시장스캔 / G4 IP전략 배치 실행 전 토큰 자동 재발급 확인:
  ```
  python -c "from pipeline.code_linker import PatentConnector; c = PatentConnector(); print(c._get_token()[:10])"
  ```
- [ ] EPO 무료 한도 확인: 4,000 요청/주 (OPS Fair Use Policy) — 초과 시 다음날 자동 해제

**서버 기동 자동화**
```powershell
# NSSM으로 Windows 서비스 등록 (관리자 권한)
nssm install IPInsight "C:\tools\python311\python.exe" "-m uvicorn api.main:app --host 0.0.0.0 --port 8100"
nssm set IPInsight AppDirectory C:\IPinsight
nssm set IPInsight AppEnvironmentExtra "PYTHONPATH=C:\IPinsight"
nssm start IPInsight
```
- [ ] 서비스 등록 후 `curl http://localhost:8100/health` 확인
- [ ] 로그 디렉토리 지정: `nssm set IPInsight AppStdout C:\IPinsight\logs\server.log`

**.env 백업**
- [ ] KeePass 또는 BitLocker 암호화 볼륨에 `.env` 복사
- [ ] 백업 위치를 팀 내 안전한 공유 저장소(예: OneDrive 암호화 폴더)에 이중 보관
- [ ] `.gitignore`에 `.env` 포함 여부 재확인 (`git check-ignore -v .env`)

---

### 단기 (D+7 ~ D+30): 서비스 안정화

**Nginx 리버스 프록시 + HTTPS**
```nginx
# /etc/nginx/sites-available/ipinsight.conf
server {
    listen 443 ssl;
    server_name api.ipinsight.kr;
    ssl_certificate     /etc/letsencrypt/live/api.ipinsight.kr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.ipinsight.kr/privkey.pem;

    location / {
        proxy_pass         http://127.0.0.1:8100;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_read_timeout 120s;   # G3 시장스캔 최대 응답시간
    }
}
server { listen 80; return 301 https://$host$request_uri; }
```
- [ ] Let's Encrypt 인증서 발급: `certbot --nginx -d api.ipinsight.kr`
- [ ] 자동 갱신 크론 등록: `0 3 * * * certbot renew --quiet`
- [ ] FastAPI CORS `allow_origins=["*"]` → 허용 도메인 목록으로 교체 (`api/main.py` L35)

**구조화 로깅**
```python
# api/main.py에 추가
import structlog
logger = structlog.get_logger()

@app.middleware("http")
async def log_requests(request, call_next):
    start = time.time()
    response = await call_next(request)
    logger.info("request", path=request.url.path,
                status=response.status_code,
                elapsed_ms=round((time.time()-start)*1000))
    return response
```
- [ ] `pip install structlog` 및 `requirements.txt` 갱신
- [ ] 로그 파일 로테이션: `logs/` 디렉토리 30일 보존, 일별 분할

**에러 알림 (Slack Webhook)**
```python
# api/services/alerter.py (신규)
import httpx, os

SLACK_URL = os.getenv("SLACK_WEBHOOK_URL")

def alert(msg: str, level: str = "warn"):
    if not SLACK_URL: return
    color = {"error": "#e53e3e", "warn": "#d69e2e", "info": "#38a169"}.get(level, "#718096")
    httpx.post(SLACK_URL, json={"attachments": [{"color": color, "text": f"[IPInsight] {msg}"}]})
```
- [ ] `.env`에 `SLACK_WEBHOOK_URL=<Slack Incoming Webhook URL>` 추가
- [ ] G3·G6·G8 에러 시 `alert()` 호출 추가 (응답시간 60초 초과, API 에러율 10% 초과)

**캐시 갱신 Task Scheduler 등록**
```
트리거1: 매일 02:00 → python scripts/scheduled_refresh.py --target patent
트리거2: 매일 03:00 → python scripts/scheduled_refresh.py --target paper
트리거3: 매주 일 01:00 → python scripts/scheduled_refresh.py --target market,esg
트리거4: 매월 1일 01:00 → python scripts/scheduled_refresh.py --target regulatory
```
- [ ] `schtasks /create /tn "IPInsight-Patent" /tr "C:\tools\python311\python.exe C:\IPinsight\scripts\scheduled_refresh.py --target patent" /sc DAILY /st 02:00`
- [ ] 실행 계정: 서비스 전용 로컬 계정 (관리자 계정 공유 금지)
- [ ] `logs/refresh.jsonl` 정상 기록 여부 다음날 확인

**API Rate Limit 모니터링**
- [ ] `GET /health` 응답에 커넥터별 잔여 한도 필드 추가:
```python
# api/main.py /health 확장
return {
    "status": "ok",
    "limits": {
        "epo_remaining_week": cache.get("epo_quota_remaining", "unknown"),
        "fda_remaining_day":  cache.get("fda_quota_remaining", "unknown"),
    }
}
```

---

### 중기 (D+30 ~ D+90): 기능 확장

**유료 데이터 소스 추가 — 우선순위 순**

| 소스 | 월 비용 | 적용 Agent | 기대 효과 |
|------|---------|-----------|----------|
| Crunchbase Basic | $49 | G9 DealStructurer | 실거래 밸류에이션 데이터 확보 (현재 규칙 기반 추정) |
| Royalty Range | $300~ | G6 ValuationEngine | 로열티율 3만건 DB — DCF 정밀도 향상 |
| Lens.org 상업 | 수익화 후 | G2/G3 | 특허 패밀리·인용 완전 데이터 (현재 EPO OPS 부분 커버) |

- [ ] Crunchbase: `pipeline/connectors/crunchbase_connector.py` 신규 작성, `G9` `_STAGE_CONNECTOR_MAP`에 `"company"` 교체
- [ ] Royalty Range: `pipeline/connectors/royalty_connector.py` 신규, `G6` `ValuationEngine` royalty_rate 함수 실데이터 전환
- [ ] 두 소스 모두 `scheduled_refresh.py`에 weekly job 추가

**웹 프론트엔드**
- [ ] Next.js 14 App Router 기반 (`/frontend` 디렉토리)
- [ ] G0~G10 단계별 진행 현황 대시보드 (현재 FastAPI Swagger UI만 존재)
- [ ] `GET /stages` 응답(현재 구현 완료)을 사이드바 네비게이션으로 렌더링
- [ ] 보고서 PDF 출력: `api/report_builder.py`의 `build_report()` 결과를 HTML→PDF 변환 (WeasyPrint)

**멀티테넌트 지원**
```python
# api/middleware/tenant.py (신규)
# X-Tenant-ID 헤더로 기관별 API 키·캐시 격리
async def tenant_middleware(request, call_next):
    tenant_id = request.headers.get("X-Tenant-ID", "default")
    request.state.tenant_id = tenant_id
    request.state.cache_prefix = f"tenant:{tenant_id}:"
    return await call_next(request)
```
- [ ] `.rag_cache/` 하위에 `tenant_{id}/` 서브디렉토리 구조로 캐시 격리
- [ ] 기관별 환경변수 세트 관리 (PostgreSQL `tenant_config` 테이블 or 개별 `.env.{tenant_id}`)

**G0~G10 배치 자동화**
- [ ] `pipeline/phase_gate_pipeline.py`의 `PhaseGatePipeline` 전체 실행을 CLI 진입점으로 노출:
```bash
python -m pipeline.phase_gate_pipeline --tech "스마트팜 IoT" --trl 4 --region KR --output report.json
```
- [ ] `--output` 플래그로 `api/report_builder.py` 자동 호출하여 PDF 동시 생성

---

### 장기 (D+90+): 고도화

**실시간 특허 모니터링**
- EPO OPS Register Notifications API (베타) — 특허 상태 변경 웹훅
- `pipeline/connectors/epo_webhook.py` 신규: IPC 클래스별 구독, 경쟁사 특허 등록 실시간 알림

**다국어 지원 우선순위**
1. 영어 (현재 한국어 고정 — `smk_generator.py`, `g0_idf_generator.py` 출력 언어 파라미터화)
2. 일본어 (J-PlatPat 연동 병행)
3. 중국어 (CNIPA 연동)

**FedAvg 연합학습** — 기관별 특허 포트폴리오 패턴 공유(원본 미반출), 현재 스캐폴드 부재 → Flower 도입 후 구현

---

## 2. 운영 체계 전환

### 서버 운영

| 항목 | 현재 | 전환 목표 |
|------|------|----------|
| 프로세스 관리 | 수동 uvicorn | NSSM Windows Service |
| 재시작 정책 | 없음 | 실패 시 30초 후 자동 재시작 |
| 환경 격리 | 글로벌 Python | venv (`C:\IPinsight\.venv`) |
| 포트 노출 | 8100 직접 | Nginx 443 → 8100 프록시 |

```powershell
# venv 기반 전환
cd C:\IPinsight
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
nssm set IPInsight Application C:\IPinsight\.venv\Scripts\python.exe
```

### 데이터 갱신 주기 (query_router.py `CACHE_TTL` 기준)

| 커넥터 | TTL | Task Scheduler 스케줄 | 현재 job 수 |
|--------|-----|--------------------|------------|
| patent / wipo | 24h | 매일 02:00 | 3개 |
| paper | 24h | 매일 03:00 | 3개 |
| market / trade | 168h (7일) | 매주 일 01:00 | 4개 |
| esg | 168h | 매주 일 01:00 | 3개 |
| clinical | 24h | 매일 03:30 | 2개 |
| regulatory / regional | 720h (30일) | 매월 1일 | static check |

### 키 관리 로드맵

| 키 | 현재 상태 | 만료·갱신 | 전환 목표 |
|----|---------|---------|---------| 
| EPO_CLIENT_ID/SECRET | .env | 연간 갱신 | Azure Key Vault |
| FDA_API_KEY | .env | 만료 없음 | Azure Key Vault |
| NTIS_API_KEY | 승인 대기 | 연간 갱신 | 승인 즉시 .env → Vault |
| SLACK_WEBHOOK_URL | 미설정 | 만료 없음 | .env |
| LLM_API_KEY | 미설정 | 사용량 기반 | 수익화 후 추가 |

---

## 3. 품질 보증 체계

### 현재 테스트 현황 (2026-06-14 기준)

```
98 passed / 0 failed / 46.02s
```

| 테스트 파일 | 커버 범위 |
|------------|---------| 
| `test_connectors.py` | 커넥터 13개 단위 |
| `test_agents.py` | G0~G10 Agent 단위 |
| `test_e2e_pipeline.py` | PhaseGatePipeline 전체 |
| `test_ip_lifecycle.py` | IP 라이프사이클 4단계 |
| `test_arl_5d.py` | ARL 5차원 평가 |
| `test_v3_fixes.py` / `test_v5_improvements.py` | 회귀 |

### CI 파이프라인 (GitHub Actions 권장)

```yaml
# .github/workflows/ci.yml
name: IPInsight CI
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.11'}
      - run: pip install -r requirements.txt
      - run: pytest tests/ -q --tb=short --timeout=120
      - run: |
          python -m uvicorn api.main:app --port 8100 &
          sleep 5 && curl http://localhost:8100/health
```

- [ ] `tests/test_api_live.py` 이미 존재 — CI에서 서버 기동 후 live 테스트 포함
- [ ] PR 머지 조건: 98개 이상 통과 + `/health` 200 OK

### 모니터링 지표 및 알림 기준

| KPI | 목표 | 경고 | 위험 | 알림 채널 |
|-----|------|------|------|---------| 
| 캐시 히트율 | >80% | <70% | <60% | Slack #ops |
| EPO API 에러율 | <3% | >5% | >10% | Slack #ops |
| G3 시장스캔 응답시간 | <30s | >45s | >60s | Slack #ops |
| G6 가치평가 응답시간 | <45s | >60s | >90s | Slack #ops |
| EPO 잔여 한도 | >1,000/주 | <500/주 | <200/주 | Email |
| FDA 잔여 한도 | >15,000/일 | <10,000/일 | <5,000/일 | Slack #ops |
| 전체 테스트 통과 | 98개 | <95개 | <90개 | GitHub PR 차단 |

```python
# api/services/health_monitor.py (신규 — /health 확장용)
THRESHOLDS = {
    "epo_remaining_week": {"warn": 500, "crit": 200},
    "fda_remaining_day":  {"warn": 10000, "crit": 5000},
    "cache_hit_rate":     {"warn": 0.70, "crit": 0.60},
}
```

---

## 4. 보안 전환

### 현재 리스크 평가

| 리스크 | 심각도 | 현재 상태 | 조치 |
|--------|--------|---------|------|
| .env 로컬 단독 저장 | 높음 | 로컬만 존재 | KeePass 암호화 백업 즉시 |
| EPO Client Secret 노출 | 높음 | .env 평문 | Key Vault 전환 (D+30) |
| CORS `allow_origins=["*"]` | 중간 | api/main.py L35 | 허용 도메인 목록 교체 (D+7) |
| HTTP 강제 차단 없음 | 중간 | 포트 8100 직접 노출 | Nginx HTTPS 전환 후 8100 방화벽 차단 |
| 내부 API Rate Limit 없음 | 낮음 | 제한 없음 | D+30 slowapi 적용 |

### 즉시 조치 (D+0)

```powershell
# 1. .env KeePass 백업
# 2. 방화벽: 외부에서 8100 직접 접근 차단 (Nginx 경유만 허용)
netsh advfirewall firewall add rule name="Block IPInsight Direct" dir=in action=block protocol=tcp localport=8100 remoteip=!127.0.0.1

# 3. git 상태 확인
git check-ignore -v .env  # .env가 추적되면 즉시 git rm --cached .env
```

### D+30 조치

```python
# 내부 API Rate Limit (slowapi)
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/stage/{stage_num}")
@limiter.limit("10/minute")    # G0~G10 단일 단계: 분당 10회
def run_single_stage(...): ...

@app.post("/pipeline/run")
@limiter.limit("2/minute")     # 전체 파이프라인: 분당 2회
def run_pipeline(...): ...
```

---

## 5. 사업화 전환 시나리오

### 시나리오 A: SaaS 구독형 (권장)

**가격 구조**

| 플랜 | 월정액 | G-Stage 범위 | 조회 한도/월 |
|------|--------|-------------|------------|
| Basic | $199 | G0~G5 | 20건 |
| Standard | $399 | G0~G10 | 50건 |
| Pro | $999 | G0~G10 + 배치 | 200건 |
| Enterprise | 협의 | 전용 인스턴스 | 무제한 |

**비용 구조 (Standard 기준, 50건/월)**

| 항목 | 월 비용 |
|------|--------|
| EPO OPS | 무료 (4,000 req/주 Fair Use) |
| FDA | 무료 (1,000 req/시간) |
| NTIS | 무료 (공공) |
| Crunchbase Basic | $49 |
| Royalty Range | $300 |
| LLM (Claude Haiku 추정) | ~$30 (50건 × 평균 20K 토큰) |
| 서버 (VPS 4core/8GB) | $40 |
| **합계** | **~$420** |

**BEP**: Standard 플랜 기준 2개 기관 구독 시 손익분기 ($420 비용 vs $798 매출)

### 시나리오 B: 프로젝트형 컨설팅

| 분석 범위 | 단가 | 소요시간 | 마진 |
|----------|------|--------|------|
| G0~G3 (기술성·시장성) | $3,000 | 24~36h | ~75% |
| G0~G6 (G5 규제 포함) | $7,000 | 48h | ~72% |
| G0~G10 완전 분석 | $12,000 | 72h | ~70% |
| 특허 포트폴리오 (G1+G4+G10) | $5,000 | 36h | ~74% |

- 소요시간은 `PhaseGatePipeline` 자동화 기준 (현재 구현 완료)
- 주 비용: API 키 사용료 + LLM 토큰 + 인건비(검수 4h)
- 연 목표: 월 4건 × $7,000 = $28,000/월 → $336,000/년

### 시나리오 C: 기술이전 기관 내재화 라이선스

대상: 대학 TLO, 공공연구기관(ETRI·KIST·KITECH), 지역 테크노파크

| 라이선스 유형 | 연간 | 포함 |
|-------------|------|-----|
| 단독 기관 | $15,000 | 설치·교육 2일·1년 유지보수 |
| 컨소시엄 (3~5개 기관) | $30,000 | 공유 인스턴스·우선 지원 |
| 정부사업 패키지 | 협의 ($50,000+) | 커스터마이징·NDA |

- 선결 조건: 웹 프론트엔드 완성 (D+60), 한국어 보고서 템플릿 표준화
- 영업 채널: KIAT(한국산업기술진흥원) 기술이전 지원사업 연계

---

## 6. 잔여 기술 부채 (우선순위 재평가)

| # | 항목 | 중요도 | 예상 공수 | 담당 Agent/파일 |
|---|------|--------|---------|----------------|
| 1 | EPO OPS 특허 상세 (서지정보·청구항 전문) | 높음 | 2일 | `pipeline/code_linker.py` PatentConnector |
| 2 | 프론트엔드 UI (Next.js) | 높음 | 2~4주 | `frontend/` (미존재) |
| 3 | NTIS XML 파싱 완성 | 중간 | 1일 (승인 후) | `pipeline/connectors/` 신규 |
| 4 | G3 실시간 스트리밍 (SSE) | 중간 | 3일 | `api/main.py` + EventSource |
| 5 | Lens.org 대체 확보 | 중간 | 계약 후 1일 구현 | `pipeline/code_linker.py` |
| 6 | Google Patents 503 간헐 오류 제거 | 낮음 | EPO 안정화 후 | code_linker.py — 이미 EPO로 대체됨 |

### EPO OPS 특허 상세 구현 방향 (즉시 착수 권장)

현재 `PatentConnector`는 검색 결과(특허번호·제목·출원일)만 반환. G2 TRL 평가와 G4 IP전략에서 청구항 전문이 필요하나 미구현.

```python
# pipeline/code_linker.py PatentConnector에 추가할 메서드
def get_patent_detail(self, pub_number: str) -> dict:
    """EPO OPS published-data/publication/{pub_number}/biblio+claims"""
    token = self._get_token()
    url = f"{self.BASE_URL}/published-data/publication/epodoc/{pub_number}/biblio,claims"
    r = self._session.get(url, headers={"Authorization": f"Bearer {token}"})
    # 청구항·발명자·인용특허·CPC 분류 파싱
    ...
```

---

## 7. 즉시 실행 체크리스트 (D+0 ~ D+3)

```
[ ] D+0  .env 백업 (KeePass 또는 BitLocker)
[ ] D+0  git check-ignore -v .env 확인
[ ] D+0  netsh 방화벽: 외부 8100 직접 차단
[ ] D+0  NSSM 서비스 등록 + 자동 재시작 설정
[ ] D+1  NTIS 키 승인 확인 → .env 추가 → pytest -k ntis
[ ] D+1  EPO 토큰 갱신 로직 장시간 배치 테스트 (3h 연속 G3 실행)
[ ] D+2  Task Scheduler 4개 크론 등록 (patent/paper/market/regulatory)
[ ] D+2  Slack Webhook URL 발급 → .env 추가 → alert() 테스트
[ ] D+3  Nginx + Let's Encrypt HTTPS 설정
[ ] D+3  CORS allow_origins 도메인 목록으로 교체
[ ] D+3  /health 엔드포인트 EPO/FDA 잔여 한도 필드 추가
```

---

**핵심 파일 경로**
- 서버 진입점: `C:\IPinsight\api\main.py`
- 스케줄러: `C:\IPinsight\scripts\scheduled_refresh.py`
- 커넥터 등록: `C:\IPinsight\pipeline\connectors\__init__.py`
- 쿼리 라우터 (70% 절감 로직): `C:\IPinsight\pipeline\query_router.py`
- 테스트 전체: `C:\IPinsight\tests\` (98 passed 기준)
- 캐시 디렉토리: `C:\IPinsight\.rag_cache\`
- 갱신 로그: `C:\IPinsight\logs\refresh.jsonl`
