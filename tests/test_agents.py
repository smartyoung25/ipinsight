"""Agent 동작 검증 스크립트"""
import sys
sys.path.insert(0, "C:/IPinsight")

from agents import TechScout, TRLAssessor, ValuationEngine, MarketScanner

def test_g0():
    scout = TechScout()
    r = scout.assess({
        "tech_name": "AI 스마트팜 수확량 예측",
        "tech_description": "딥러닝으로 온실 작물 수확량을 7일 전 예측하는 AI 시스템",
        "problem_statement": "온실 농가의 수확량 예측 불확실성 해결",
        "ipc_codes": ["G06N", "A01G"],
        "field_keywords": ["스마트팜", "AI"],
        "existing_solutions": "기상청 예보 기반 추정",
        "owner": "KAASA",
    })
    print(f"G0 기술발굴: score={r.score}, gate={r.gate}")
    assert r.score > 0
    assert r.gate in ["Go", "Hold", "Kill"]

def test_g2():
    agent = TRLAssessor()
    r = agent.assess({
        "claimed_trl": 5,
        "evidence_list": [
            {"type": "성능평가 보고서", "description": "MAPE 17.8%", "date": "2026-03"},
            {"type": "시제품 보고서", "description": "5농가 실증", "date": "2026-04"},
        ],
        "target_trl": 8,
    })
    current_trl = r.output_doc["trl_assessment"]["current_trl"]
    print(f"G2 TRL평가: trl={current_trl}, score={r.score}, gate={r.gate}")
    assert 1 <= current_trl <= 9

def test_g3():
    agent = MarketScanner()
    r = agent.assess({
        "tech_name": "스마트팜 AI",
        "target_market": "온실 농가",
        "tam_usd": 5_000_000_000,
        "sam_usd": 500_000_000,
        "som_usd": 10_000_000,
        "growth_rate_pct": 15,
        "competitors": ["Priva", "Ridder"],
        "entry_barriers": ["데이터 축적"],
        "substitute_technologies": ["기상청 예보"],
    })
    print(f"G3 시장성: score={r.score}, gate={r.gate}")
    assert r.score > 0

def test_g6():
    agent = ValuationEngine()
    r = agent.assess({
        "tech_name": "스마트팜 AI",
        "industry_sector": "스마트팜",
        "revenue_forecast": [500_000, 2_000_000, 5_000_000, 10_000_000, 15_000_000],
        "discount_rate_pct": 15,
        "royalty_rate_pct": 4,
        "tech_contribution_pct": 35,
        "patent_remaining_years": 18,
        "risk_adjustment_pct": 25,
        "monte_carlo_runs": 500,
    })
    val = r.output_doc["tech_valuation_report"]["weighted_value_usd"]
    print(f"G6 가치평가: value=${val:,.0f}, gate={r.gate}")
    assert val > 0

if __name__ == "__main__":
    test_g0()
    test_g2()
    test_g3()
    test_g6()
    print("\n전체 Agent 동작 확인 완료")
