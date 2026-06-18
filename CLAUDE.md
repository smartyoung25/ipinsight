# IPInsight — 글로벌 기술사업화 Agent OS
> 세션 시작 시: NEXT.md만 읽을 것. 이 파일은 아키텍처 변경 시만 참조.

---

## 영구 제약 (절대 위반 금지)

- **PitchBook ($1,000+)** — 절대 통합 금지
- **IBISWorld ($1,000+)** — 절대 통합 금지

## 서버 실행

```powershell
cd C:\IPinsight
$env:PYTHONIOENCODING="utf-8"
python -m uvicorn api.main:app --port 8100 --reload
python -m pytest tests/ -q    # 반드시 C:\IPinsight에서 실행
```

## PCML v2.0 핵심 규칙 (절대 변경 금지)

#### 6계층 아키텍처
| 계층 | 이름 | 필수 여부 |
|------|------|---------|
| L1 | Patent Layer | 필수 |
| L2 | Claim Graph Layer | 필수 (L1 전제) |
| L3 | Specification Support Layer | 입력자료 있을 때 |
| L4 | Metadata Layer | 입력자료 있을 때 |
| L5 | Legal & Family Layer | 입력자료 있을 때 |
| L6 | Enforcement Evidence Layer | 입력자료 있을 때 |

#### 핵심 타입 제약
- **Node element_class**: Core | Supporting | Peripheral (미부여 = QC FAIL)
- **Node observability**: 0/25/50/75/100 (5단계)
- **Link relation_type**: 13개 허용값만 (includes/has/performs/inputs/receives/outputs/transmits/controls/based_on/stores/retrieves/connected_to/depends_on)
- **Attribute attr_type**: 12개 허용값 (algorithm/decision_rule/range/material/function 등)
- **Release gate**: releasable | **internal_only** | blocked (partial 아님)
- **QC FAIL** 5조건 × 20점 / **QC WARN** 10조건 × 5점 / QC_grade A~D
- **Shared Variables** 9종: self_core_nodes, self_core_links, support_coverage, explicit_support_ratio, evidence_linkage_ratio, black_box_core_ratio, claim_clarity_penalty, legal_status_score, family_coverage_rate

#### ⚠️ None-Safe 패턴 (screening_agent.py 버그 이력)
```python
# shared.get("key", 0) 은 None 반환 가능 — or 패턴 필수
value = shared.get("key") or 0          # 0 기본값
ratio = shared.get("ratio") if shared.get("ratio") is not None else 0.5  # 0.5 기본값
```

## 인증 아키텍처 결정사항

- **bcrypt**: passlib 1.7.4 + bcrypt==4.0.1 핀 (`requirements.txt`)
- **SHA-256 폴백**: 고정 솔트 `"ipinsight-default-salt-v1"` (JWT_SECRET_KEY 없을 때)
- **개발 모드 자동 통과**: JWT_SECRET_KEY + ADMIN_API_KEY 모두 미설정 시
- **POST 전체 인증**: `post_auth_gate` HTTP 미들웨어
- **미들웨어 역순 실행**: 마지막 등록 = 첫 실행 → post_auth_gate가 logging보다 먼저 실행
- **users.json**: `api/data/users.json` (admin/admin1234 SHA-256 해시)

## 디렉토리 구조

```
C:\IPinsight\
├── agents/                    # G0~G10 에이전트 + PCML + SCR + SMK
├── api/
│   ├── main.py                    # FastAPI 앱 (47+ 엔드포인트)
│   ├── schemas.py                 # Pydantic 스키마 10종
│   ├── auth.py                    # JWT + API Key + bcrypt/SHA-256
│   ├── middleware.py              # logging + metrics + POST auth gate
│   └── routers/reports.py         # R1~R9 보고서 엔드포인트
├── pipeline/
│   ├── phase_gate_pipeline.py
│   ├── funding_matcher.py
│   └── connectors/                # KIPRIS·GooglePatents·Market·Clinical 등
├── tests/                     # conftest + test_api + test_auth + test_connectors
└── requirements.txt
```

## 핵심 프로세스 (G0~G10)

| 단계 | 이름 | 핵심 산출물 |
|------|------|------------|
| G0 | 기술후보 발굴 | 기술 후보 등록카드 |
| G1 | IP 구조화 + G1.6-SCR | IP 구조분석서, FTO, SCR 보고서 |
| G1.5 | PCML v2.0 | 6계층 청구항 구조 JSON + KPI |
| G2 | TRL 평가 | TRL 평가표 |
| G3 | 시장성 평가 | 시장성 분석보고서 |
| G4 | 고객검증 + LoI 자동생성 | Customer Discovery + 도입의향서 |
| G5 | BM 설계 + G5-CR + SMK | BM 캔버스 + 사업화 로드맵 + SMK |
| G6 | 가치평가 | 기술가치평가서 (DCF·로열티·Real Option) |
| G7 | PoC·실증 | PoC 결과보고서 |
| G8 | MRL·ARL | 3중 성숙도 평가표 |
| G9 | 거래·투자 | 라이선싱·투자 전략서 |
| G10 | 성과환류 | KPI Dashboard |

## 핵심 결정 로그

| 결정 | 내용 |
|------|------|
| G6 주법 | TRL<7 → 로열티구제법, TRL≥7 → DCF |
| G4 | JTBD 3차원 + NSF I-Corps 100건 기준 |
| G8 ARL | 5차원, 병목원칙: 단일차원≤2→전체최대4 |
| G10 BCG | X축 = IP강도35%+특허수명25%+TRL20%+ARL20% |
| Monte Carlo | TRL낮을수록 rev_std 커짐 (trl_factor=(9-trl)/9) |
| PCML | 6계층 L1~L6, relation_type 13개, element_class 3종 |
| 인증 | JWT+APIKey, bcrypt==4.0.1 핀, SHA-256 고정솔트 폴백 |
| G5-CR | KIAT/KEIT 협약 표준 + DOE Commercialization Plan 구조 |
| G4 LoI | loi_count≥1 or poc_requests≥1 시 도입의향서 자동생성 |
| SMK | G5 Go 게이트 시 G3+G4+G5 통합 SMK 자동생성 |

## 보고서 생성 안전장치 (JS ip-insight 패턴 이식)

| 패턴 | 함수 | 설명 |
|------|------|------|
| StoreA 강제 인계 | `_enrich_from_store_a(report_id, result, store_a)` | LLM이 청구항/구성요소를 비우거나 환각해도 PCML 결과로 강제 덮어씀 |
| 의존 보고서 컴팩션 | `_compact_dep_reports(dep_reports)` | R6→R5, R7→R5+R2 의존 시 전체 보고서 대신 keyFindings + 핵심 블록만 전달 (토큰 절감) |

**수정 시 주의**: `_enrich_from_store_a` 를 변경하면 `structuredData.claims`/`.components` 필드가 사라질 수 있음. 반드시 R1~R9 전체 출력 콘솔 검증.

## 코딩 규칙 (절대 준수)

- 모든 에이전트 메서드: `.assess(input_data: dict)` (`.run()` 아님)
- `CodeLinkerPipeline.run()` — 클래스·메서드 이름 정확히
- `release_status`: releasable | **internal_only** | blocked (**partial 아님**)
- PowerShell: `&&` 없음, `$env:PYTHONIOENCODING="utf-8"` 필수
- pytest: 반드시 `cd C:\IPinsight` 에서 실행 (smart_farm pytest.ini 간섭 방지)
