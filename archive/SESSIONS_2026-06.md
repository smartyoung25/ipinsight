# IPInsight 세션 아카이브 — 2026년 6월

---

## 2026-06-16 세션 — MECE 구조화 + 컨텍스트 관리

**주요 커밋**: d1ffb37 → 55db174 → 2439018 → 1ec1440 → b6db9c2

### 완료 작업
- **MECE Phase 1** (d1ffb37): 좀비 alias 5개 제거, roadmap → G5 redirect, G6 4탭 확장(DCF/CCA/ROA/비교)
- **G0 검증탭 + G5 TAM 자동인계** (55db174): G0 "기술성립 검증" 탭, G5 SMK 탭 g3_tam/g3_growth 자동인계 배너
- **G4 데이터 추적** (2439018): interview_count·loi_count·poc_requests·WTP 누적평균 갱신
- **데이터 플로우 완성** (1ec1440): G3→G5 growth 이중 fallback, G5 Unit Economics G4 WTP 자동참조, G9→REPORTS 저장 버튼(R6/R7/R9)
- **G10 gate map** (b6db9c2): 전체 게이트 Plotly 막대차트, 감사 이력 10건
- **컨텍스트 관리**: HOME 기술사업화 명언 20개 순환, CLAUDE.md 133→120줄, archive 신설

### 기술 결정
- `_home_quote` session_state 캐시 → 세션당 1회만 random.choice() 실행
- G3 widget key `g3_growth` ≠ 구 key `g3_grow` → 이중 fallback으로 해결

---

## 2026-06-15 세션 — PCML + 연속 파이프라인

**마지막 커밋**: bc1ed1f

- G1→G2→G3 analyze-chain-extended 파이프라인 (workspace 3단 위저드)
- 테스트 216→221개 / SCR NoneType 버그 수정

---

## 2026-06-14 이전 — Phase 1~4 구현 누적

- G0~G10 전 스테이지 기본 UI
- PCML v2.0 6계층 아키텍처, G4 LoI·G5-CR·SMK 파이프라인
- 인증 아키텍처 (JWT + bcrypt 4.0.1 핀)
- 테스트 216개 달성
