# 결정 등록부 (Decision Register)
> 왜 이 설계를 택했는가 — 필요할 때만 참조, 항상 로드 불필요

---

### [D-2026-06-01] G0~G10 Stage Gate 구조 채택
**결정**: WIPO Lab-to-Market 기반 11단계 Stage Gate
**대안**: 선형 폭포수 모델, 린 스타트업 4단계
**이유**: Stage Gate는 Go/Hold/Kill 명시적 결정점이 있어 자동화 가능. 스코어 기반 게이팅이 LLM 없이도 작동함
**영향 파일**: `pipeline/phase_gate_pipeline.py`

---

### [D-2026-06-02] ARL 채택 (BRL 기각)
**결정**: 3축 성숙도 = TRL(NASA) + MRL(DoD) + ARL(DOE)
**대안**: BRL(Business Readiness Level) — VC 에코시스템에서 비공식 사용
**이유**: ARL은 DOE 공식 표준(1~9 스케일). BRL은 표준화되지 않아 벤치마킹 불가
**영향 파일**: `agents/g8_mrl_arl_assessor.py`

---

### [D-2026-06-03] 4단계 IP 라이프사이클 × G0~G10 이중축 통합
**결정**: 외부 축 = 4단계 IP Phase, 내부 게이트 = G0~G10
**대안**: 두 프레임워크 완전 별도 운영
**이유**: 65% 커버리지가 이미 존재. IP개발(G0-IDF·G1-Portfolio) + IP전략(G10 확장)만 추가하면 100% 달성
**영향 파일**: `api/main.py` `/ip/*` 엔드포인트 6개

---

### [D-2026-06-04] Venture Client → G7 PoC 선택 연동
**결정**: Venture Client는 G7 PoC의 옵션 파라미터로 (필수 아님)
**대안**: 별도 G7.5 스테이지로 분리
**이유**: 모든 PoC가 기업 고객과 진행되는 건 아님. 강제화하면 사용성 저하
**영향 파일**: `agents/g7_poc_manager.py` (`venture_client_partner` optional)

---

### [D-2026-06-05] knowledge/ JSON = 정적 DB (벡터DB 미사용)
**결정**: knowledge/*.json 파일로 도메인 지식 저장
**대안**: 벡터 DB(Chroma, Pinecone), SQLite
**이유**: 프로젝트 초기이고 규모 小. JSON은 git 추적 가능, 투명, 의존성 없음. 확장 필요 시 마이그레이션 가능
**영향 파일**: `knowledge/` 전체

---

### [D-2026-06-07] G6 Monte Carlo — 4변수 독립 샘플링 + TRL 연동 불확실성
**결정**: 4개 변수(매출·할인율·로열티·기여도)를 독립 샘플링, TRL별 분산 차등
**대안**: 단일 revenue_shock 가우시안 (기존 방식)
**이유**: 단일 쇼크는 변수 간 상관을 가정해 P10/P90 폭이 과소 또는 과대 추정됨. TRL 낮을수록 매출 예측 불확실성이 실질적으로 크므로 `trl_factor = (9-trl)/9` 로 rev_std 스케일
**결과**: TRL1 rev_std=35%, TRL5=19.4%, TRL9=3.9%. P10/P50/P90 bear/base/bull 레이블 추가
**영향 파일**: `agents/g6_valuation_engine.py` `_monte_carlo()`

---

### [D-2026-06-08] Venture Client Model — G9 7번째 거래유형으로 통합
**결정**: TRL 6-8 + B2B 조건 충족 시 venture_client 거래유형 자동 추천
**대안**: 별도 G9.5 Venture Client 스테이지 분리
**이유**: 거래유형 선택은 G9 Deal Structurer의 핵심 출력. 분리하면 사용자가 G9를 건너뛰고 Venture Client를 볼 방법이 없음. 7번째 옵션으로 통합이 UX 면에서 자연스러움
**벤치마크**: BMW i Ventures·Porsche·Bosch·BASF·Siemens 5개 프로그램 (대기업 PoC 비용 부담, 스타트업 지분 희석 없음)
**영향 파일**: `agents/g9_deal_structurer.py` `_VENTURE_CLIENT_PROGRAMS`, `_recommend_deal()`

---

### [D-2026-06-09] BCG Matrix X축 — 자기선언 대신 복합 객관 점수
**결정**: X축 = competitive_position_score(0~100) = 자기선언(35%) + 특허수명(25%) + TRL(20%) + ARL(20%)
**대안**: 자기선언 strong/medium/weak 단순 매핑 (기존)
**이유**: 자기선언만 쓰면 모든 기술이 "strong"으로 신고해 BCG가 무의미해짐. TRL·ARL·특허수명은 외부 검증 가능한 지표이므로 편향 완화
**결과**: X임계값 50점 기준선. 객관 점수가 35% 이상이므로 자기선언 영향력은 최대 35점
**영향 파일**: `agents/g10_portfolio_optimizer.py` `_competitive_position_score()`, `_classify_tech()`

---

### [D-2026-06-06] 컨텍스트 관리 — SPRINT+NEXT+DECISIONS 3파일 체계
**결정**: CLAUDE.md는 불변 원칙만, 상태는 SPRINT.md/NEXT.md로 분리
**대안**: CLAUDE.md 단일 파일에 모든 상태 기록 (기존 방식)
**이유**: CLAUDE.md가 800줄 이상이 되면 그 자체가 컨텍스트를 소비. 다음 세션에서 "행동으로 연결"이 안 됨.
**원칙**: NEXT.md = 다음 세션의 첫 번째 명령 단 1개
**영향 파일**: 이 파일 포함 SPRINT.md, NEXT.md
