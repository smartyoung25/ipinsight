# IPInsight — 글로벌 기술사업화 Agent OS

## 프로젝트 개요
글로벌 기술사업화 프로세스(G0~G10) 전주기를 AI Agent로 자동화하는 플랫폼.
WIPO Lab-to-Market · NASA TRL · NSF I-Corps · DOE ARL · MRL 통합 설계.

## 디렉토리 구조
```
IPinsight_a/
├── agents/                  # G0~G10 단계별 Agent 모듈
│   ├── g0_tech_scout.py     # 기술후보 발굴·등록
│   ├── g1_ip_structurer.py  # IP 구조화·FTO 분석
│   ├── g2_trl_assessor.py   # TRL 자동 평가
│   ├── g3_market_scanner.py # 시장성·산업매력도
│   ├── g4_customer_validator.py  # 고객발견·수요검증
│   ├── g5_bm_designer.py    # 사업모델·GTM 설계
│   ├── g6_valuation_engine.py    # IP·기술 가치평가
│   ├── g7_poc_manager.py    # PoC·실증·위험저감
│   ├── g8_mrl_arl_assessor.py    # MRL·ARL 3중 평가
│   ├── g9_deal_structurer.py     # 거래·투자 결정
│   └── g10_performance_tracker.py # 성과관리·환류
├── knowledge/               # 정적 지식 DB (JSON)
│   ├── trl_framework.json
│   ├── mrl_framework.json
│   ├── arl_framework.json
│   ├── country_programs.json
│   ├── royalty_benchmarks.json
│   └── regulatory_paths.json
├── pipeline/
│   ├── phase_gate_pipeline.py  # G0~G10 Stage Gate 실행
│   └── funding_matcher.py      # 단계별 정부지원 매칭
├── api/
│   ├── main.py              # FastAPI 앱
│   └── schemas.py           # Pydantic 모델
├── outputs/                 # 산출물 저장 (JSON/PDF)
└── tests/                   # 단위 테스트
```

## 핵심 프로세스 (G0~G10)
| 단계 | 이름 | 글로벌 기준 | 핵심 산출물 |
|------|------|------------|------------|
| G0 | 기술후보 발굴 | WIPO Lab-to-Market | 기술 후보 등록카드 |
| G1 | IP 구조화 | Stanford/MIT TLO | IP 구조분석서, FTO |
| G2 | TRL 평가 | NASA TRL 1~9 | TRL 평가표 |
| G3 | 시장성 평가 | EIC Transition | 시장성 분석보고서 |
| G4 | 고객검증 | NSF I-Corps | Customer Discovery Report |
| G5 | BM 설계 | BMC + Lean Startup | 사업모델 캔버스, GTM |
| G6 | 가치평가 | DCF·로열티·Real Option | 기술가치평가서 |
| G7 | PoC·실증 | Catapult·Fraunhofer | PoC 결과보고서 |
| G8 | MRL·ARL | DoD MRL + DOE ARL | 3중 성숙도 평가표 |
| G9 | 거래·투자 | TLO 라이선싱·SBIR | 라이선싱·투자 전략서 |
| G10 | 성과환류 | Horizon Europe | KPI Dashboard |

## Gate 판단 기준
- **Go**: 다음 단계 진행
- **Hold**: 추가 데이터/보완 필요
- **Kill**: 사업화 중단 또는 재설계

## 서버 실행
```bash
cd C:\IPinsight_a
python -m uvicorn api.main:app --port 8100 --reload
```
