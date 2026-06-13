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

### [D-2026-06-06] 컨텍스트 관리 — SPRINT+NEXT+DECISIONS 3파일 체계
**결정**: CLAUDE.md는 불변 원칙만, 상태는 SPRINT.md/NEXT.md로 분리
**대안**: CLAUDE.md 단일 파일에 모든 상태 기록 (기존 방식)
**이유**: CLAUDE.md가 800줄 이상이 되면 그 자체가 컨텍스트를 소비. 다음 세션에서 "행동으로 연결"이 안 됨.
**원칙**: NEXT.md = 다음 세션의 첫 번째 명령 단 1개
**영향 파일**: 이 파일 포함 SPRINT.md, NEXT.md
