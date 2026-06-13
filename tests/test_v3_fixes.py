"""v3 4개 수정 검증 — 가치평가 주법·JTBD·규제Gate·화이트스페이스"""
import sys
sys.path.insert(0, "C:/IPinsight_a")

from agents import ValuationEngine, CustomerValidator, MRLARLAssessor, WhitespaceAnalyzer


def test_g6_primary_method_trl5():
    """TRL<7 이면 로열티구제법이 주법"""
    r = ValuationEngine().assess({
        "tech_name": "AI 스마트팜", "trl": 5,
        "industry_sector": "스마트팜",
        "revenue_forecast": [500000, 2000000, 5000000, 8000000, 12000000],
        "discount_rate_pct": 15, "royalty_rate_pct": 4,
        "tech_contribution_pct": 35, "patent_remaining_years": 18,
        "risk_adjustment_pct": 25, "monte_carlo_runs": 300,
    })
    method = r.output_doc["tech_valuation_report"]["primary_method"]
    print(f"G6 TRL5 주법: {method}")
    assert method == "relief_from_royalty", f"FAIL: {method}"


def test_g6_primary_method_trl8():
    """TRL>=7 이면 DCF가 주법"""
    r = ValuationEngine().assess({
        "tech_name": "AI 스마트팜 v2", "trl": 8,
        "revenue_forecast": [2000000, 5000000, 10000000],
        "discount_rate_pct": 12, "royalty_rate_pct": 4,
        "tech_contribution_pct": 35, "patent_remaining_years": 15,
        "risk_adjustment_pct": 20, "monte_carlo_runs": 200,
    })
    method = r.output_doc["tech_valuation_report"]["primary_method"]
    print(f"G6 TRL8 주법: {method}")
    assert method == "dcf", f"FAIL: {method}"


def test_g4_jtbd():
    """JTBD 3차원 기록 시 검증건수 증가"""
    interviews = [
        {
            "customer_type": "온실농가",
            "pain_point": "수확량 불확실",
            "willingness_to_pay": 3000,
            "urgency_1to5": 4,
            "jtbd_functional": "수확량 7일 전 예측",
            "jtbd_emotional": "불안감 해소",
            "jtbd_social": "스마트팜 선도 농가로 인정",
        }
    ] * 35
    r = CustomerValidator().assess({
        "interviews": interviews,
        "loi_count": 3,
        "poc_requests": 2,
    })
    jtbd = r.output_doc["jtbd_analysis"]
    print(f"G4 JTBD 검증건수: {jtbd['jtbd_verified_count']}")
    print(f"G4 경고: {r.warnings}")
    assert jtbd["jtbd_verified_count"] > 0
    # 35건 = Phase I 기준 통과, National 기준 미달 -> 경고 존재
    assert any("100" in w for w in r.warnings), "100건 미달 경고 없음"


def test_g8_regulatory_penalty():
    """규제 미취득 인증 -> Gate 패널티 부과"""
    r = MRLARLAssessor().assess({
        "trl": 6,
        "manufacturing_process_defined": True,
        "supply_chain_ready": True,
        "quality_system": "ISO9001",
        "unit_cost_usd": 500,
        "target_cost_usd": 400,
        "customer_pilots": 5,
        "repeat_purchase_rate_pct": 25,
        "regulatory_approved": False,
        "certifications_required": ["CE Mark", "FDA 510k"],
        "certifications_obtained": [],
    })
    triple = r.output_doc["triple_maturity_assessment"]
    print(f"G8 규제리스크: {triple['regulatory_risk_level']}  패널티: {triple['regulatory_gate_penalty']}점")
    assert triple["regulatory_gate_penalty"] > 0, "미인증인데 패널티 0"
    assert triple["regulatory_risk_level"] in ("Medium", "High")


def test_g1_whitespace():
    """화이트스페이스 분석 — 융합 공백 + 지리적 공백 탐색"""
    r = WhitespaceAnalyzer().assess({
        "tech_name": "AI 스마트팜",
        "ipc_codes": ["G06N", "A01G"],
        "competitor_filings": [
            {"assignee": "Priva BV", "ipc_codes": ["A01G"], "filed_year": 2023, "status": "active"},
            {"assignee": "Ridder", "ipc_codes": ["G05B"], "filed_year": 2022, "status": "abandoned"},
        ],
        "target_countries": ["KOR", "USA", "EU"],
        "technology_trends": ["Edge AI", "Digital Twin"],
        "own_filed_ipc": ["G06N"],
    })
    ws = r.output_doc["whitespace_summary"]
    print(f"화이트스페이스 기회: {ws['total_opportunities']}건  "
          f"(융합: {ws['combination_gaps']}건, 지리: {ws['geographic_gaps']}건, "
          f"포기: {ws['abandoned_areas']}건)")
    assert ws["total_opportunities"] > 0
    assert ws["combination_gaps"] > 0


if __name__ == "__main__":
    test_g6_primary_method_trl5()
    test_g6_primary_method_trl8()
    test_g4_jtbd()
    test_g8_regulatory_penalty()
    test_g1_whitespace()
    print("\n4개 수정 전체 검증 통과")
