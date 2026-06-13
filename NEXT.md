# 다음 세션 첫 번째 명령

## 상태
**완료**: 글로벌 벤치마크 경쟁력 수정 8개 (63 → 84점)

| # | 수정 내용 | 커밋 |
|---|-----------|------|
| ① | G6 주법 교체: TRL<7 → 로열티구제법 주법 (Stanford OTL/MIT TLO/AICPA) | b99a504 |
| ② | G4 JTBD 3차원 + NSF I-Corps 100건 기준 | b99a504 |
| ③ | G8 규제 경로 Gate 패널티 연결 (EIC Accelerator) | b99a504 |
| ④ | G1-Whitespace 신규: WIPO FTO + White Space 2축 완성 | b99a504 |
| ⑤ | G8 ARL 5차원 독립 평가 — DOE 공식 표준 완전 정합 | ea4b1ab |
| ⑥ | G6 Monte Carlo 4변수 독립 샘플링·TRL연동·P10/P50/P90 시나리오 | 9e80b12 |
| ⑦ | G9 Venture Client Model (BMW i Ventures 5개사 벤치마크) | 9e80b12 |
| ⑧ | G10 BCG X축 객관화 (IP강도·TRL·ARL 복합) + 예산배분 3모드 | 9e80b12 |

## 다음 세션 시작 명령
```powershell
cd C:\IPinsight_a
$env:PYTHONIOENCODING="utf-8"
python tests\test_agents.py
python tests\test_v3_fixes.py
python tests\test_arl_5d.py
python tests\test_ip_lifecycle.py
python tests\test_v5_improvements.py
```
→ 5개 테스트 전부 통과 확인 후 SPRINT.md 확인하여 다음 목표 논의

## 다음 목표 후보

### C. 실사용 테스트 (권장 다음 단계)
- FastAPI 서버 기동 (`uvicorn api.main:app --port 8100 --reload`)
- Swagger UI (http://localhost:8100/docs) 에서 전 엔드포인트 확인
- 실제 기술 사례 1개로 G0→G10 전 파이프라인 실행
- `POST /ip/pipeline/run` 엔드포인트 동작 확인

### D. DECISIONS.md 업데이트 (선택)
- v5 수정 결정 3건 기록

## 절대 잊으면 안 되는 것
- ARL = Adoption Readiness Level (DOE 공식) — BRL이 아님
- ARL 5차원: market(25%) customer(25%) regulatory(20%) economic(20%) ecosystem(10%)
- 병목 원칙: 단일 차원 ARL<=2 → 전체 최대 ARL 4
- G6: TRL<7 → 로열티구제법 주법, TRL>=7 → DCF 주법
- G9: Venture Client = 대기업 첫 유료 고객, 지분 희석 없음
- G10 BCG X축: competitive_score = 자기선언(35%) + 특허수명(25%) + TRL(20%) + ARL(20%)
- Monte Carlo: TRL 낮을수록 rev_std 커짐 (trl_factor = (9-trl)/9)
- PowerShell: `&&` 없음, `$env:PYTHONIOENCODING="utf-8"` 필수 (한글 출력)
