# 글로벌 기술사업화 프로세스 벤치마킹 — 실행 관점 통합 정리

## 1. 비교 대상 3대 프레임워크

| # | 프레임워크 | 출처 | 특징 |
|---|-----------|------|------|
| A | **IPInsight G0~G10** | WIPO Lab-to-Market 기반 | 11단계 全주기, TRL·MRL·ARL 3축, Stage Gate |
| B | **글로벌 28개 벤치마킹 맵** | MIT/Stanford TLO, EIC, NIST MEP 등 | 6범주 30+ 방법론 |
| C | **IPInsight Agent OS (구현)** | 본 저장소 G0~G10 코드 | 자동화 스코어링·LLM 연동 |

---

## 2. 28개 글로벌 벤치마크 → 실행 적합도 분류

### 2-1. ★★★ 즉시 실행 가능 (구현 우선)

| 방법론 | 근거 | 현 구현 상태 |
|--------|------|-------------|
| **WIPO Lab-to-Market** | 전주기 표준, G0~G10 기반 | ✅ 전체 구조 채택 |
| **NASA TRL 1~9** | 증빙 기반 기술성숙도, 세계 통용 | ✅ G2 완전 구현 |
| **NSF I-Corps 고객발견** | 30회 인터뷰→LoI, 가장 검증된 방법론 | ✅ G4 구현 |
| **DoD MRL 1~10** | 양산준비도, TRL과 병행 필수 | ✅ G8 구현 |
| **DOE ARL 1~9** | 채택준비도, 시장·규제 리스크 계량화 | ✅ G8 구현 |
| **Stage Gate (Cooper)** | 단계별 Go/Hold/Kill, 의사결정 표준 | ✅ PhaseGatePipeline |
| **DCF + 로열티역산 + 실옵션** | 기술가치평가 3법 동시 적용 | ✅ G6 구현 |
| **EIC Pathfinder→Transition→Accelerator** | 유럽 딥테크 표준 3단계 자금 시퀀스 | ✅ country_programs.json |
| **SBIR/STTR Phase I→II→III** | 미국 공공R&D 자금 시퀀스 | ✅ country_programs.json |
| **TIPS (한국)** | 민간투자 선행+정부 매칭, 국내 최고 IRR | ✅ country_programs.json |
| **Yozma 2.0 (이스라엘)** | 정부 지분참여→민간 옵션 매입, 레버리지 | ✅ country_programs.json |

### 2-2. ★★ 높은 실행 가치 (G11 확장 또는 knowledge/ 보강)

| 방법론 | 실행 관점 핵심 | 현 구현 상태 |
|--------|--------------|-------------|
| **Venture Client Model** (BMW i Ventures) | 기업이 스타트업 고객 되어 PoC 비용 부담→빠른 상업화 | ⬜ G7 PoC에 추가 가능 |
| **FLC Federal Lab Consortium** | 미국 국립연구소 기술이전 표준절차(CRADA·라이선스) | ⬜ G9 거래구조에 추가 |
| **Stanford Biodesign** | 관찰→수요정의→발명→사업화, 의료기기 특화 | ⬜ G0~G2 의료 버티컬 |
| **Design Council Double Diamond** | 문제발견(Discover·Define)→해결(Develop·Deliver) | ⬜ G0 기술발굴 선행 |
| **ISO 56000/56005** | 혁신경영 국제표준, 기업 혁신 포트폴리오 관리 | ⬜ G10 성과관리에 연동 |
| **NIST MEP (Manufacturing Extension Partnership)** | 중소제조업 공정개선→TRL 7~9 빠른 양산 | ⬜ G8 MRL 갭 분석에 추가 |
| **A*STAR TRL 점프 모델** (싱가포르) | 공공연구원이 기업과 공동 TRL 점프, 지분참여 없음 | ⬜ G7~G8에 R&D 파트너십 옵션 |

### 2-3. ★ 참고 가치 (중장기 로드맵)

| 방법론 | 설명 |
|--------|------|
| **Open Innovation (P&G Connect+Develop)** | 외부기술 흡수(Inbound) + 내부기술 외부화(Outbound). G9 Out-licensing에 적용 |
| **EIT Knowledge Triangle** | 교육-연구-혁신 삼각형, 스핀오프 인재 확보에 적용 |
| **Deep-Tech Venture Builder** | 자체 스핀오프 스튜디오 모델, G9 Spinoff 옵션 강화 |
| **NIH I-Corps (바이오헬스)** | NSF I-Corps 의료 버티컬 확장, 임상파트너 발굴 특화 |
| **Fraunhofer-Gesellschaft 모델** | 용역연구(계약)→기술이전 혼합. G9 Joint Dev 계약구조 참고 |
| **Catapult Network (영국)** | 분야별 기술사업화 센터(제조·디지털·에너지). G7 실증 파트너십 |

---

## 3. 실행 관점 통합 최적 프로세스 (IPInsight Execution Stack)

```
G0  기술발굴         → IPC 분류 + Problem Statement 명확화 (Double Diamond 선행)
  ↓ Gate: 기술등록카드
G1  IP구조화         → 청구항 재구성 + FTO 1차 + 회피설계 (FLC/CRADA 준비)
  ↓ Gate: IP 방어력 점수≥60
G2  TRL 평가         → 증빙기반 TRL + MRL 예비평가 + 정부자금 매칭 (SBIR/TIPS 진입점)
  ↓ Gate: TRL≥3, 자금경로 확정
G3  시장성 분석       → TAM/SAM/SOM + Porter 5 Forces + Beachhead 선정
  ↓ Gate: SOM≥$1M
G4  고객검증          → NSF I-Corps 30회 인터뷰 + LoI 3건 + WTP 확인
  ↓ Gate: WTP 확인율≥40% + LoI≥2건
G5  BM 설계          → BMC + 6개 사업화 경로 선택 + GTM 전략 (Venture Client 우선)
  ↓ Gate: 수익모델 선택 완료
G6  가치평가          → DCF + 로열티역산 + 실옵션 + Monte Carlo P10/P50/P90
  ↓ Gate: P50 가치≥협상 하한
G7  PoC 실증         → KPI 설계 + Venture Client or Catapult 파트너 + 결과 분석
  ↓ Gate: KPI 달성률≥70%
G8  MRL·ARL 평가     → 양산준비(MRL 1~10) + 채택준비(ARL 1~9) + 인증 갭 (CE/FDA/KC)
  ↓ Gate: 복합성숙도 점수≥60
G9  거래·투자 구조     → 6가지 경로(License/Transfer/JD/Spinoff/JV/조달) + 텀시트
  ↓ Gate: LOI 체결
G10 성과관리          → 6대 KPI 추적 + ISO 56000 포트폴리오 + 재학습 트리거
```

---

## 4. 28개 프로세스 중 구현 우선순위 결론

### 현 구현(G0~G10 Agent OS)이 이미 커버하는 핵심 방법론 (11개)
WIPO Lab-to-Market / NASA TRL / NSF I-Corps / DoD MRL / DOE ARL / Cooper Stage Gate /
DCF+로열티+실옵션 / EIC 3단계 / SBIR/STTR / TIPS / Yozma 2.0

### 다음 우선 보강 대상 (실행 가치 高)
1. **Venture Client Model** → G7 `g7_poc_manager.py`에 `venture_client_partner` 필드 추가
2. **FLC/CRADA** → G9 `g9_deal_structurer.py`에 국립연구소 협약 경로 추가
3. **NIST MEP** → G8 MRL 갭 분석에 중소제조업 공정 체크리스트 추가
4. **ISO 56000** → G10 KPI에 혁신경영 지표 추가

### 실행 관점에서 제외(중장기 참고만)
- Open Innovation, EIT Knowledge Triangle, Deep-Tech Venture Builder:
  구현 대비 다양성 효과 낮음, 현 G9 Spinoff/Out-licensing으로 커버 가능

---

## 5. IPInsight Agent OS vs. 벤치마크 차별화 포인트

| 차별 요소 | IPInsight Agent OS | 벤치마크 평균 |
|----------|-------------------|-------------|
| 자동화 스코어링 | G0~G10 전 단계 0~100점 자동 | 수동 체크리스트 |
| 3축 성숙도 | TRL+MRL+ARL 복합 | TRL 단독 多 |
| 정부자금 자동매칭 | 7개국 11개 프로그램 DB | 수동 조사 필요 |
| LLM 강화 분석 | FTO/Porter/가치평가 LLM 옵션 | 없음 |
| Monte Carlo 가치평가 | P10/P50/P90 분포 | DCF 단독 |
| Stage Gate 자동 판정 | Go/Hold/Kill 기준 점수 | 위원회 주관 판단 |

---

*최종 업데이트: 2026-06-13*
*기반 문서: WIPO Technology Transfer Manual, NASA TRL Handbook, NSF I-Corps Program Guide,
DoD MRL Deskbook, DOE ARL Framework, Cooper Stage-Gate Manual*
