# 다음 세션 첫 번째 명령

## 상태
**완료**: IP Lifecycle × G0~G10 v2 통합 — 17개 Agent, 15개 API 엔드포인트, 전 테스트 통과 (b826beb)

## 다음 세션 시작 명령
```
cd C:\IPinsight_a
python tests\test_agents.py && python tests\test_ip_lifecycle.py
```
→ 두 테스트 모두 통과 확인 후 SPRINT.md 작성하여 다음 작업 시작

## 왜 여기서 멈췄는가
IP Lifecycle × 기술사업화 통합 구현 완료. 다음 목표 미정.

## 절대 잊으면 안 되는 것
- ARL(Adoption Readiness Level, DOE 공식 표준) — BRL이 아님
- G10 = 성과관리 + Global IP + Competitive + Portfolio Optimizer 4개 병렬
- BaseAgent._llm()는 ANTHROPIC_API_KEY 없으면 규칙 기반 폴백 자동 작동
