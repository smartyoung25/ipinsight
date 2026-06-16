# NEXT — 다음 세션 시작점
> 생성: 2026-06-16 / 마지막 커밋: b6db9c2 (G10 gate map + REPORTS prefill)

## 현재 상태 (1줄)
MECE 구조화 완료(G0~G10 단일 route 키, 좀비 alias 제거) + HOME 기술사업화 명언 순환 + 테스트 221개.

## 이번 세션 목표 (1개만)
[ ] G3 시장성 TAM/SAM/SOM 인터랙티브 Plotly 차트 + G3→G5 성장률 자동인계 안정화

## 다음 3개 작업 (우선순위 순)
1. G3 시장성 — TAM/SAM/SOM Plotly 파이·막대 차트 시각화 (`frontend/app.py` G3 탭)
2. 보고서 영속화 — SQLite에 chain 결과 저장 + `/reports/history` 엔드포인트
3. FTO 보고서 자동생성 — G1 탭에 FTO 결과 → R3 보고서 다운로드 버튼

## 열린 문제 / 블로커
- KIPRIS_API_KEY 미설정 → patent_text 직접 입력 우회 가능
- PitchBook·IBISWorld 절대 통합 금지 (영구 제약)
- Groq 429 rate limit 간헐적 — openai SDK 재시도로 처리됨

## 서버 실행 (복붙용)
```powershell
cd C:\IPinsight ; $env:PYTHONIOENCODING="utf-8"
python -m uvicorn api.main:app --port 8001 --reload
python -m streamlit run frontend/app.py --server.port 8503
```

## 주의사항
- pytest: 반드시 `cd C:\IPinsight`에서 실행 (smart_farm pytest.ini 간섭 방지)
- PCML `release_status`: releasable | internal_only | blocked (partial 아님)
- 에이전트 메서드: `.assess(input_data: dict)` (.run() 아님)
- G3→G5 성장률 키: `g3_growth` (위젯 key) / `g3_grow` (구 key) 이중 fallback 적용됨
