# NEXT — 다음 세션 시작점
> 생성: 2026-06-15 / 마지막 커밋: bc1ed1f feat(workspace): G1→G2→G3 연속 파이프라인 UI 연결

## 현재 상태 (1줄)
3단 위저드 홈 UI + /ip/analyze-chain-extended (G1→G2→G3) 완료, 테스트 221개 전부 통과.

## 이번 세션 목표 (1개만)
[ ] IP Hub 페이지에서 analyze-chain-extended 결과를 시각적으로 표시 (단계별 게이지 + 화이트스페이스 카드)

## 다음 3개 작업 (우선순위 순)
1. IP Hub 페이지 — chain-extended 결과 시각화 (게이지 차트, 화이트스페이스 카드)
2. G3 시장성 페이지 신규 또는 워크스페이스에 TAM/SAM/SOM 시각화 추가
3. 보고서 영속화 — SQLite에 chain 결과 저장 + `/reports/history` 엔드포인트

## 열린 문제 / 블로커
- Groq 429 rate limit 간헐적 — openai SDK 재시도로 처리됨
- KIPRIS_API_KEY 미설정 → patent_text 직접 입력 우회 가능
- PitchBook·IBISWorld 절대 통합 금지 (영구 제약)

## 서버 실행 (복붙용)
```powershell
cd C:\IPinsight
$env:PYTHONIOENCODING="utf-8"
python -m uvicorn api.main:app --port 8001
# Streamlit
python -m streamlit run frontend/app.py --server.port 8503
```

## 주의사항
- pytest: 반드시 `cd C:\IPinsight`에서 실행 (221개 기준)
- PCML `release_status`: releasable | internal_only | blocked (partial 아님)
- 에이전트 메서드: `.assess(input_data: dict)` (.run() 아님)
- analyze-chain-extended: TAM 미입력 시 기본값 5억 달러 자동 적용
