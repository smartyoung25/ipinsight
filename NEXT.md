# NEXT — 다음 세션 시작점
> 생성: 2026-06-14 / 테스트: 216개 전부 통과

## 현재 상태 (1줄)
Groq LLM 완전 연동 완료 — PCML(llama-3.3-70b) + SCR(llama-3.3-70b) 실 분석 정상 작동, 경고 없음.

## 이번 세션 목표 (1개만)
[x] Groq LLM 실 분석 품질 검증 완료 (PCML Gate=Go/Score=80, SCR Gate=G2/Score=75, Gap=5)

## 다음 3개 작업 (우선순위 순)
1. 216개 테스트 실행 확인 (`cd C:\IPinsight && python -m pytest -x -q`)
2. PCML Gate=Hold/Kill 유도 특허로 경계값 검증 (약한 청구항 입력)
3. G2→G3 연속 파이프라인 엔드포인트 (`/ip/analyze-chain-extended`)

## 열린 문제 / 블로커
- Anthropic 크레딧 부족 → Groq로 대체 완료, 문제없음
- KIPRIS_API_KEY 미설정 → patent_text 직접 입력으로 우회 가능
- Groq 429 (rate limit) 간헐적 발생 → openai SDK 자동 재시도로 처리됨

## 서버 실행 (복붙용)
```powershell
cd C:\IPinsight
$env:PYTHONIOENCODING="utf-8"
python -m uvicorn api.main:app --port 8001
```

## 주의사항
- pytest: **반드시 `cd C:\IPinsight`에서** 실행
- PCML `release_status`: releasable | **internal_only** | blocked (**partial 아님**)
- 에이전트 메서드: `.assess(input_data: dict)` (`.run()` 아님)
- PitchBook·IBISWorld 절대 통합 금지
- SCR JSON 파싱: 마크다운 코드블록 제거 + 불완전 JSON 자동 복구 로직 내장

## 다음 스프린트 후보
- FTO 보고서 (G1)
- 클레임 차트 자동 생성
- G2→G5 연속 파이프라인 엔드포인트
- 보고서 영속화 (SQLite)
