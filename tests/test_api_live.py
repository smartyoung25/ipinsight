"""FastAPI 엔드포인트 실 HTTP 검증 — 실제 라우트 기준"""
import sys
sys.path.insert(0, "C:/IPinsight")

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

# 공통 입력
G0_INPUT = {
    "tech_name": "AI 스마트팜", "inventor": "홍길동", "institution": "KAASA",
    "tech_detail": "AI 기반 온실 환경제어", "problem_solved": "노동력·에너지 절감",
    "trl": 5, "ipc_codes": ["G06N"], "industry_sector": "AgriTech",
    "target_market": "Smart Farming",
}
G2_INPUT = {
    "tech_name": "AI 스마트팜", "current_trl": 5,
    "evidence": ["센서연동 완료", "PoC 농가 3개소"],
    "barriers": ["상용화 자금"], "target_trl": 7, "timeline_months": 12,
}
G6_INPUT = {
    "tech_name": "AI 스마트팜", "trl": 5, "industry_sector": "AgriTech",
    "revenue_forecast": [500000, 2000000, 5000000],
    "discount_rate_pct": 15, "royalty_rate_pct": 4,
    "tech_contribution_pct": 35, "patent_remaining_years": 18,
    "risk_adjustment_pct": 25, "monte_carlo_runs": 500,
}

TESTS = [
    # ── 상태 확인 ──────────────────────────────────────────
    ("GET",  "/health",               None,
     "서비스 상태"),
    ("GET",  "/stages",               None,
     "G0~G10 단계 목록"),
    ("GET",  "/ip/stages",            None,
     "IP Lifecycle 단계 목록"),
    ("GET",  "/demo/sample-input",    None,
     "샘플 입력 반환"),

    # ── 단일 스테이지 (숫자 기반) ───────────────────────────
    ("POST", "/stage/0",
     {"tech_id": "t1", "input_data": G0_INPUT},
     "G0 기술발굴"),
    ("POST", "/stage/2",
     {"tech_id": "t1", "input_data": G2_INPUT},
     "G2 TRL 평가"),
    ("POST", "/stage/6",
     {"tech_id": "t1", "input_data": G6_INPUT},
     "G6 가치평가 (Monte Carlo)"),

    # ── 전체 파이프라인 ─────────────────────────────────────
    ("POST", "/analyze",
     {
         "tech_id": "live_test_001",
         "stage_inputs": {
             0: G0_INPUT,
             2: G2_INPUT,
             6: G6_INPUT,
         },
         "stop_on_kill": False,
     },
     "G0→G2→G6 파이프라인"),

    # ── 자금조달 매칭 ───────────────────────────────────────
    ("POST", "/funding/match",
     {"trl": 5, "country": "KOR", "sector": "AgriTech", "stage_id": "G2"},
     "정부지원 프로그램 매칭"),
    ("GET",  "/funding/sequence?trl_current=5&trl_target=8&country=KOR", None,
     "TRL 5→8 자금 시퀀스"),

    # ── IP Lifecycle 신규 엔드포인트 ────────────────────────
    ("POST", "/ip/idf",
     {"tech_id": "t1", "input_data": {
         "tech_name": "AI 스마트팜", "tech_detail": "온실 AI제어",
         "inventor_info": [{"name": "홍길동", "contribution_pct": 100}],
         "security_classification": "일반", "licensing_potential": "높음",
     }},
     "IDF 발명공개서"),
    ("POST", "/ip/portfolio",
     {"tech_id": "t1", "input_data": {
         "core_patents": [{"title": "AI제어", "filing_no": "KR2024-001"}],
         "satellite_patents": [], "defensive_patents": [],
         "target_countries": ["KOR", "USA"], "budget_usd": 50000,
     }},
     "특허포트폴리오 전략"),
    ("POST", "/ip/patentability",
     {"tech_id": "t1", "input_data": {
         "tech_name": "AI 스마트팜",
         "spec_analysis": "신규성 있음",
         "prior_art_legal_opinion": "선행기술 없음",
         "dependent_claims_strength": 7,
         "enforceability_risk": "낮음",
     }},
     "권리성 심화 평가"),
    ("POST", "/ip/global-strategy",
     {"tech_id": "t1", "input_data": {
         "tech_name": "AI 스마트팜",
         "target_market_countries": ["KOR", "JPN", "USA"],
         "tam_by_country": {"KOR": 5000000, "JPN": 20000000, "USA": 100000000},
         "regulatory_requirement_by_country": {"USA": "FDA 불요"},
     }},
     "글로벌 IP 전략"),
    ("POST", "/ip/portfolio-optimize",
     {"tech_id": "t1", "input_data": {
         "portfolio_techs": [
             {"tech_id": "p1", "tech_name": "AI수확예측", "trl": 7, "mrl": 6, "arl": 5,
              "annual_revenue_usd": 500000, "annual_cost_usd": 80000,
              "market_growth_pct": 20, "competitive_position": "strong",
              "patent_remaining_years": 15, "licensing_revenue_usd": 100000},
         ],
         "total_ip_budget_usd": 100000, "strategic_focus": "growth",
     }},
     "포트폴리오 최적화"),
]


def run():
    passed = failed = 0
    print("=" * 70)
    print(f"  {'METHOD':<6} {'ENDPOINT':<34} {'ST':<5} {'설명':<14} 결과")
    print("=" * 70)

    for method, url, body, desc in TESTS:
        try:
            r = client.get(url) if method == "GET" else client.post(url, json=body)
            ok = r.status_code == 200
            if ok:
                passed += 1
                mark = "OK"
            else:
                failed += 1
                mark = "FAIL"
            d = r.json()
            # 결과 요약
            if "gate" in d:
                summary = f"gate={d['gate']} score={d.get('score','?')}"
            elif "result" in d and isinstance(d["result"], dict):
                g = d["result"].get("gate", "")
                s = d["result"].get("score", "")
                summary = f"gate={g} score={s}" if g else str(d["result"])[:40]
            elif "stages" in d:
                summary = f"{len(d['stages'])}개 스테이지"
            elif "ip_lifecycle_phases" in d:
                summary = f"{len(d['ip_lifecycle_phases'])}개 페이즈"
            elif "all_results" in d:
                gates = {k: v.get("gate", "?") for k, v in d["all_results"].items()}
                summary = str(gates)
            elif "matched_programs" in d:
                summary = f"{len(d['matched_programs'])}개 프로그램"
            elif "sequence" in d:
                summary = f"{len(d['sequence'])}단계 시퀀스"
            elif "status" in d:
                summary = d["status"]
            else:
                summary = str(d)[:45]
            print(f"[{mark:<4}] {method:<6} {url:<34} {r.status_code:<5} {desc:<14} {summary}")
        except Exception as e:
            failed += 1
            print(f"[ERR ] {method:<6} {url:<34} {'':5} {desc:<14} {str(e)[:40]}")

    print("=" * 70)
    print(f"결과: {passed}/{passed+failed} 통과  {'전체 통과' if failed == 0 else f'{failed}개 실패'}")
    return failed == 0


if __name__ == "__main__":
    run()
