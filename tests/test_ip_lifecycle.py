"""IP Lifecycle 확장 Agent 6개 동작 검증"""
import sys
sys.path.insert(0, "C:/IPinsight")

from agents import (
    IDFGenerator, PatentPortfolioStrategist, PatentabilityAssessor,
    GlobalIPStrategist, CompetitiveMonitor, PortfolioOptimizer,
)


def test_g0_idf():
    agent = IDFGenerator()
    r = agent.assess({
        "tech_name": "AI 스마트팜 수확량 예측",
        "tech_detail": (
            "딥러닝과 IoT 센서를 결합하여 온실 작물의 수확량을 7일 전 예측하는 AI 시스템. "
            "환경 데이터(온도/습도/일사량)와 생육 데이터를 실시간 수집하여 LSTM 모델로 예측."
        ),
        "problem_solved": "온실 농가의 수확량 예측 불확실성 해결",
        "inventor_info": [
            {"name": "홍길동", "affiliation": "KAASA", "contribution_pct": 60},
            {"name": "김철수", "affiliation": "KAASA", "contribution_pct": 40},
        ],
        "key_features": ["IoT 센서 실시간 수집", "LSTM 기반 예측", "MAPE 17.8%"],
        "prior_art_known": ["기상청 예보 시스템", "단순 통계 모델"],
        "security_classification": "internal",
        "licensing_potential": "non_exclusive",
        "research_funding": "정부 IITP 과제",
    })
    print(f"G0-IDF: score={r.score}, gate={r.gate}")
    assert r.score > 0
    assert "idf_document" in r.output_doc
    assert len(r.output_doc.get("funding_warnings", [])) > 0  # 정부과제 경고 확인


def test_g1_portfolio():
    agent = PatentPortfolioStrategist()
    r = agent.assess({
        "tech_name": "AI 스마트팜",
        "core_patents": [
            {"title": "IoT 기반 수확량 예측", "ipc": "G06N", "claims_count": 8, "status": "출원중"}
        ],
        "satellite_patents": [
            {"title": "센서 보정 방법", "ipc": "A01G", "claims_count": 5},
            {"title": "데이터 전처리", "ipc": "G06F", "claims_count": 4},
        ],
        "defensive_patents": [],
        "target_countries": ["KOR", "USA", "EU", "JPN"],
        "budget_usd": 50000,
        "priority_date": "2026-01-15",
    })
    print(f"G1-Portfolio: score={r.score}, gate={r.gate}")
    assert "portfolio_map" in r.output_doc
    assert "filing_timeline" in r.output_doc
    cost = r.output_doc["cost_projection"]["total_estimated_usd"]
    print(f"  예상 출원 비용: ${cost:,.0f}")


def test_g2_patentability():
    agent = PatentabilityAssessor()
    r = agent.assess({
        "tech_name": "AI 스마트팜 수확량 예측",
        "spec_analysis": (
            "본 발명은 IoT 센서에서 수집된 온실 환경 데이터와 생육 데이터를 "
            "LSTM 신경망으로 학습하여 7일 전 수확량을 예측하는 방법 및 시스템에 관한 것으로, "
            "종래 기상 예보 기반 방식 대비 MAPE 17.8%의 정확도를 달성한다."
        ),
        "independent_claims": [
            "IoT 센서로부터 환경 데이터를 수집하는 단계; LSTM 모델로 수확량을 예측하는 단계를 포함하는 수확량 예측 방법",
        ],
        "prior_art_legal_opinion": "기상청 예보 기반 시스템과 본 발명은 LSTM 활용 여부에서 명백히 구별됨",
        "closest_prior_art": "단순 기상 예보 기반 수확량 추정 시스템 (비교예 1)",
        "technical_difference": "본 발명은 LSTM 딥러닝과 IoT 센서 실시간 데이터를 결합하여 선행기술 대비 MAPE 20%p 개선",
        "dependent_claims_strength": "strong",
        "enablement_evidence": [
            {"type": "실험데이터", "desc": "딸기 5농가 6개월 실증"},
            {"type": "논문", "desc": "MAPE 17.8% 성능 보고서"},
        ],
        "fto_risk": "low",
    })
    print(f"G2-Patentability: score={r.score}, gate={r.gate}")
    assert "patentability_assessment" in r.output_doc
    assert "legal_risk_matrix" in r.output_doc


def test_g10_global():
    agent = GlobalIPStrategist()
    r = agent.assess({
        "tech_name": "AI 스마트팜",
        "target_market_countries": ["KOR", "USA", "EU", "JPN", "SGP"],
        "tam_by_country": {
            "KOR": 200_000_000, "USA": 2_000_000_000,
            "EU": 1_500_000_000, "JPN": 500_000_000, "SGP": 100_000_000,
        },
        "regulatory_requirement_by_country": {
            "USA": ["FCC"], "EU": ["CE Mark"], "KOR": ["KC인증"],
        },
        "current_filings": ["KOR"],
        "filing_strategy_preference": "pct_first",
        "annual_ip_budget_usd": 80000,
    })
    print(f"G10-Global: score={r.score}, gate={r.gate}")
    matrix = r.output_doc["country_priority_matrix"]
    top1 = matrix[0]["country"]
    print(f"  우선순위 1위 국가: {top1}")
    assert len(matrix) == 5


def test_g10_competitive():
    agent = CompetitiveMonitor()
    r = agent.assess({
        "tech_name": "AI 스마트팜",
        "competitor_patents": [
            {"patent_no": "US123456", "title": "AI crop prediction", "assignee": "Priva BV",
             "ipc": "G06N", "claim_summary": "LSTM기반 수확예측", "overlap_risk": "high", "filed_date": "2025-06"},
            {"patent_no": "EP789012", "title": "IoT greenhouse system", "assignee": "Ridder",
             "ipc": "A01G", "claim_summary": "IoT 온실 제어", "overlap_risk": "medium", "filed_date": "2024-03"},
        ],
        "market_intelligence": ["Priva 2026 Q1 AI 모듈 출시"],
        "technology_trends": ["엣지AI 도입 가속", "오픈소스 농업AI 플랫폼 증가"],
        "own_patent_count": 2,
        "own_ip_strength_score": 65,
    })
    print(f"G10-Competitive: score={r.score}, gate={r.gate}")
    plan = r.output_doc["threat_response_plan"]
    print(f"  위협 대응 계획: {len(plan)}건 / 최우선={plan[0]['recommended_action']}")
    assert len(r.warnings) > 0  # high 위협 경고


def test_g10_portfolio_optimizer():
    agent = PortfolioOptimizer()
    r = agent.assess({
        "portfolio_techs": [
            {
                "tech_id": "t1", "tech_name": "AI수확량예측", "trl": 7, "mrl": 6, "arl": 5,
                "annual_revenue_usd": 500000, "annual_cost_usd": 80000,
                "market_growth_pct": 18, "competitive_position": "strong",
                "patent_remaining_years": 16, "licensing_revenue_usd": 100000,
            },
            {
                "tech_id": "t2", "tech_name": "구형센서모듈", "trl": 5, "mrl": 4, "arl": 3,
                "annual_revenue_usd": 20000, "annual_cost_usd": 60000,
                "market_growth_pct": 2, "competitive_position": "weak",
                "patent_remaining_years": 3, "licensing_revenue_usd": 0,
            },
        ],
        "total_ip_budget_usd": 150000,
        "strategic_focus": "growth",
    })
    print(f"G10-Portfolio: score={r.score}, gate={r.gate}")
    cats = r.output_doc["portfolio_optimization_plan"]["category_summary"]
    print(f"  Star={cats['star']['count']}건, Dog={cats['dog']['count']}건")
    assert cats["star"]["count"] >= 1
    assert cats["dog"]["count"] >= 1
    divest = r.output_doc["divestment_recommendation"]
    print(f"  매각 절감 비용: ${divest['estimated_cost_savings_usd']:,.0f}")


if __name__ == "__main__":
    test_g0_idf()
    test_g1_portfolio()
    test_g2_patentability()
    test_g10_global()
    test_g10_competitive()
    test_g10_portfolio_optimizer()
    print("\nIP Lifecycle 전체 Agent 동작 확인 완료")
