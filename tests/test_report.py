"""POST /ip/report 종합 리포트 엔드포인트 검증"""
import sys
sys.path.insert(0, "C:/IPinsight")

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

PIPELINE_INPUTS = {
    0: {
        "tech_name": "AI 스마트팜", "inventor": "홍길동", "institution": "KAASA",
        "tech_detail": "AI 온실 환경제어", "problem_solved": "절감", "trl": 5,
        "ipc_codes": ["G06N"], "industry_sector": "AgriTech", "target_market": "Smart Farming",
    },
    2: {
        "tech_name": "AI 스마트팜", "current_trl": 5, "evidence": ["PoC 3개소"],
        "barriers": ["자금"], "target_trl": 7, "timeline_months": 12,
    },
    6: {
        "tech_name": "AI 스마트팜", "trl": 5, "industry_sector": "AgriTech",
        "revenue_forecast": [500000, 2000000, 5000000],
        "discount_rate_pct": 15, "royalty_rate_pct": 4,
        "tech_contribution_pct": 35, "patent_remaining_years": 18,
        "risk_adjustment_pct": 25, "monte_carlo_runs": 500,
    },
    8: {
        "tech_name": "AI 스마트팜", "trl": 5, "industry_sector": "AgriTech",
        "target_countries": ["KOR"], "regulatory_requirements": {},
        "market_size_usd": 5000000, "customer_segments": ["온실농가"],
        "distribution_channels": ["직판"],
    },
    9: {
        "tech_name": "AI 스마트팜", "trl": 7, "mrl": 6, "arl": 5,
        "ip_strength_score": 65, "valuation_usd": 3000000,
        "team_commercialization_capability": 3,
        "is_b2b": True, "corporate_customer_interest": True,
        "potential_partners": ["Bosch"], "target_countries": ["KOR"],
    },
}


def test_report_generation():
    r = client.post("/ip/report", json={
        "tech_id": "kaasa_report_test",
        "stage_inputs": PIPELINE_INPUTS,
        "stop_on_kill": False,
    })
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"

    data = r.json()
    assert "report" in data
    rpt = data["report"]

    # 필수 섹션 존재 확인
    for key in ["executive_summary", "scorecard", "maturity_profile",
                "valuation_snapshot", "deal_structure", "bottleneck_analysis",
                "priority_actions", "report_meta"]:
        assert key in rpt, f"섹션 누락: {key}"

    ex = rpt["executive_summary"]
    sc = rpt["scorecard"]
    vs = rpt["valuation_snapshot"]
    ds = rpt["deal_structure"]
    bn = rpt["bottleneck_analysis"]

    print("\n" + "=" * 55)
    print("  IP 기술사업화 종합 진단 리포트")
    print("=" * 55)
    print(f"  기술 ID    : {data['tech_id']}")
    print(f"  평가 단계  : {rpt['report_meta']['stages_evaluated']}개")
    print()
    print(f"  종합 판정  : {ex['overall_icon']} {ex['overall_gate']}  ({ex['verdict']})")
    print(f"  평균 점수  : {ex['avg_score']}점")
    cnt = ex["stage_counts"]
    print(f"  단계 현황  : Go {cnt['go']}  Hold {cnt['hold']}  Kill {cnt['kill']}  / 총 {cnt['total']}개")
    print()
    print("  ── Scorecard ───────────────────────────────")
    for row in sc:
        print(f"  {row['gate_icon']} {row['stage_id']:<4} {row['stage_name']:<12}  "
              f"{row['score']:>6.1f}점  {row['gate_ko']}")
    print()
    mp = rpt["maturity_profile"]
    print("  ── Maturity Profile ────────────────────────")
    for k, v in mp.items():
        print(f"  {k.upper()}: {v}")
    print()
    if vs:
        print("  ── Valuation Snapshot ──────────────────────")
        print(f"  기준가치   : ${vs['weighted_value_usd']:>12,.0f}")
        print(f"  리스크조정 : ${vs['risk_adjusted_usd']:>12,.0f}")
        print(f"  P10/P50/P90: "
              f"${vs['p10_usd']:,.0f} / ${vs['p50_usd']:,.0f} / ${vs['p90_usd']:,.0f}")
    print()
    if ds:
        print("  ── Deal Structure ──────────────────────────")
        print(f"  추천 거래  : {ds['recommended_deal']}")
        print(f"  Venture Client: {ds['venture_client']}  {ds['vc_matched_programs']}")
    print()
    print("  ── Bottleneck ──────────────────────────────")
    print(f"  {bn['recommendation']}")
    print()
    print("  ── Priority Actions (Top 5) ────────────────")
    for i, a in enumerate(rpt["priority_actions"], 1):
        print(f"  {i}. {a}")
    print("=" * 55)

    # 검증
    assert ex["overall_gate"] in ("Go", "Hold", "Kill")
    assert ex["avg_score"] > 0
    assert len(sc) > 0
    assert vs.get("weighted_value_usd", 0) > 0, "가치평가 값 없음"
    assert ds.get("recommended_deal") == "venture_client", \
        f"TRL7 B2B → venture_client 기대, got: {ds.get('recommended_deal')}"
    assert len(rpt["priority_actions"]) > 0
    print("\n[PASS] /ip/report 종합 리포트 검증 통과")


if __name__ == "__main__":
    test_report_generation()
