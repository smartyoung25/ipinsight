# NEXT — 다음 세션 시작점
> 생성: 2026-06-16 / 마지막 커밋: 68694b4

## 현재 상태 (1줄)
G3 탭 TAM/SAM/SOM 3차트(퍼널·파이도넛·막대) 완료 + G3→G5 성장률 자동인계 안정화 확인.

## 이번 세션 목표 (1개만)
[x] G3 시장성 TAM/SAM/SOM 인터랙티브 Plotly 차트 + G3→G5 성장률 자동인계 안정화

## 다음 3개 작업 (우선순위 순)
1. 보고서 영속화 — SQLite에 chain 결과 저장 + `/reports/history` 엔드포인트
2. FTO 보고서 자동생성 — G1 탭에 FTO 결과 → R3 보고서 다운로드 버튼
3. G6 가치평가 — DCF 파라미터 슬라이더 + 민감도 분석 Plotly 차트

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
