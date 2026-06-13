"""실행전략 4모듈 통합 테스트 — 팀·단위경제성·자금조달·규제 로드맵"""
import sys
sys.path.insert(0, "C:/IPinsight")

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
TECH_ID = "exec_strategy_test"


# ── G4-Team ───────────────────────────────────────────────────────────────────
TEAM_INPUT = {
    "team_type": "spinout",
    "members": [
        {"role": "technical_lead",      "background": "AI PhD 10년", "startup_experience": "startup_growth",
         "domain_years": 8, "ip_deals_count": 2, "has_network": True},
        {"role": "business_lead",       "background": "McKinsey 5년 + 스타트업 CEO",
         "startup_experience": "serial", "domain_years": 5, "ip_deals_count": 1, "has_network": True},
        {"role": "domain_expert",       "background": "농업 현장 전문가 15년",
         "startup_experience": "none",  "domain_years": 15, "ip_deals_count": 0, "has_network": True},
        {"role": "ip_commercialization","background": "KAIST TLO 기술이전 담당 7년",
         "startup_experience": "academic","domain_years": 7, "ip_deals_count": 5, "has_network": True},
    ],
    "advisors": [{"role": "투자자", "affiliation": "KDB"}, {"role": "도메인", "affiliation": "농진청"}],
    "prior_exits": 1,
    "full_time_committed": 3,
    "total_team_size": 4,
    "missing_roles": ["financial_ops"],
}

def test_team_assessor():
    r = client.post("/execution/team", json={"tech_id": TECH_ID, "input_data": TEAM_INPUT})
    assert r.status_code == 200, r.text
    data = r.json()
    result = data["result"]
    assert result["score"] >= 60, f"팀 점수 낮음: {result['score']}"
    assert result["gate"] in ("Go", "Hold")
    out = result["output_doc"]
    assert "team_assessment" in out
    assert "five_dimension_profile" in out
    assert "hiring_priority" in out
    assert len(out["five_dimension_profile"]) == 5
    print(f"\n[G4-Team] 점수={result['score']} 판정={result['gate']}")
    print(f"  5차원: {out['five_dimension_profile']}")
    print(f"  채용우선순위: {[h['role'] for h in out['hiring_priority']]}")


# ── G5-UE ────────────────────────────────────────────────────────────────────
UE_INPUT = {
    "revenue_model": "saas",
    "avg_contract_value_usd": 12_000,
    "avg_contract_months": 12,
    "churn_rate_monthly_pct": 1.5,
    "gross_margin_pct": 75,
    "sales_marketing_spend_usd": 50_000,
    "new_customers_per_month": 10,
    "monthly_burn_usd": 120_000,
    "cash_on_hand_usd": 2_400_000,
    "monthly_revenue_usd": 80_000,
    "headcount": 12,
}

def test_unit_economics():
    r = client.post("/execution/unit-economics", json={"tech_id": TECH_ID, "input_data": UE_INPUT})
    assert r.status_code == 200, r.text
    data = r.json()
    result = data["result"]
    out = result["output_doc"]
    ue = out["unit_economics"]
    fh = out["financial_health"]
    assert ue["cac_usd"] == 5_000,           f"CAC 오류: {ue['cac_usd']}"
    assert ue["ltv_cac_ratio"] >= 1.0,        f"LTV/CAC 낮음: {ue['ltv_cac_ratio']}"
    assert fh["runway_months"] >= 12,          f"런웨이 낮음: {fh['runway_months']}"
    assert "benchmark_comparison" in out
    assert "improvements" in out
    print(f"\n[G5-UE] 점수={result['score']} 판정={result['gate']}")
    print(f"  CAC=${ue['cac_usd']:,}  LTV=${ue['ltv_usd']:,}  LTV/CAC={ue['ltv_cac_ratio']}")
    print(f"  Payback={ue['payback_months']}개월  런웨이={fh['runway_months']}개월")
    print(f"  손익분기 고객수={fh['breakeven_customers']}")


# ── G2-Funding ───────────────────────────────────────────────────────────────
FUNDING_INPUT = {
    "current_trl": 5,
    "target_trl": 8,
    "commercialization_type": "startup",
    "current_valuation_usd": 3_000_000,
    "current_cash_usd": 500_000,
    "monthly_burn_usd": 40_000,
    "total_funding_needed_usd": 5_000_000,
    "founder_equity_pct": 80.0,
    "country": "KOR",
    "has_revenue": False,
}

def test_funding_planner():
    r = client.post("/execution/funding", json={"tech_id": TECH_ID, "input_data": FUNDING_INPUT})
    assert r.status_code == 200, r.text
    data = r.json()
    result = data["result"]
    out = result["output_doc"]
    fp  = out["funding_plan"]
    assert len(fp["stages"]) >= 2,            f"자금 단계 부족: {len(fp['stages'])}"
    assert fp["total_plan_usd"] > 0,           "총 자금 0"
    assert "dilution_simulation" in out
    assert "funding_strategy" in out
    print(f"\n[G2-Funding] 점수={result['score']} 판정={result['gate']}")
    print(f"  총 자금계획=${fp['total_plan_usd']:,}  총희석={fp['total_dilution_pct']}%")
    print(f"  최종 창업자지분={fp['founder_equity_final_pct']}%")
    for s in fp["stages"]:
        print(f"    └ {s['stage']}: ${s['amount_usd']:,} / 희석{s.get('dilution_pct',0)}% → 지분{s.get('equity_after_pct',100)}%")


# ── G8-Reg (의료기기) ──────────────────────────────────────────────────────────
REG_MD_INPUT = {
    "domain": "medical_device",
    "product_class": "2등급",
    "target_countries": ["KOR", "USA", "EU"],
    "trl": 7,
    "has_clinical_data": True,
    "has_qms": True,
    "regulatory_budget_usd": 200_000,
    "timeline_target_months": 24,
    "previous_approvals": [],
}

# G8-Reg (SaMD)
REG_SAMD_INPUT = {
    "domain": "samd",
    "target_countries": ["KOR", "USA"],
    "trl": 6,
    "has_clinical_data": False,
    "has_qms": False,
    "regulatory_budget_usd": 100_000,
    "timeline_target_months": 18,
    "previous_approvals": [],
}

def test_regulatory_roadmap_medical():
    r = client.post("/execution/regulatory", json={"tech_id": TECH_ID, "input_data": REG_MD_INPUT})
    assert r.status_code == 200, r.text
    data = r.json()
    result = data["result"]
    out = result["output_doc"]
    rr  = out["regulatory_roadmap"]
    assert rr["domain"] == "의료기기"
    assert len(rr["certifications"]) >= 1
    assert "compliance_framework" in out
    assert "readiness_gaps" in out
    print(f"\n[G8-Reg 의료기기] 점수={result['score']} 판정={result['gate']}")
    for c in rr["certifications"][:3]:
        print(f"  {c['country']} {c['certification']}: {c['months']}개월 / ${c['cost_usd']:,} ({'가능' if c['feasible'] else '예산초과'})")

def test_regulatory_roadmap_samd():
    r = client.post("/execution/regulatory", json={"tech_id": TECH_ID, "input_data": REG_SAMD_INPUT})
    assert r.status_code == 200, r.text
    data = r.json()
    result = data["result"]
    out = result["output_doc"]
    gaps = out["readiness_gaps"]
    # QMS 없으면 gap 있어야 함
    assert any("QMS" in g["item"] for g in gaps), f"QMS gap 누락: {gaps}"
    print(f"\n[G8-Reg SaMD] 점수={result['score']} 판정={result['gate']}")
    print(f"  준비 격차: {[g['item'] for g in gaps]}")


# ── execution/stages 목록 ─────────────────────────────────────────────────────
def test_execution_stages_list():
    r = client.get("/execution/stages")
    assert r.status_code == 200
    data = r.json()
    assert len(data["execution_modules"]) == 4
    endpoints = [m["endpoint"] for m in data["execution_modules"]]
    assert "/execution/team" in endpoints
    assert "/execution/unit-economics" in endpoints
    assert "/execution/funding" in endpoints
    assert "/execution/regulatory" in endpoints
    print(f"\n[execution/stages] 모듈 {len(data['execution_modules'])}개 등록 확인")


if __name__ == "__main__":
    test_team_assessor()
    test_unit_economics()
    test_funding_planner()
    test_regulatory_roadmap_medical()
    test_regulatory_roadmap_samd()
    test_execution_stages_list()
    print("\n[ALL PASS] 실행전략 4모듈 전체 통과")
