"""경쟁력 80점+ 수정 검증 — Monte Carlo P10/P50/P90 · Venture Client · BCG Matrix"""
import sys
sys.path.insert(0, "C:/IPinsight")

from agents import ValuationEngine, DealStructurer, PortfolioOptimizer


def test_monte_carlo_distribution():
    """Monte Carlo P10/P50/P90 분포 + 시나리오 레이블 + 불확실성 드라이버"""
    r = ValuationEngine().assess({
        "tech_name": "AI 스마트팜", "trl": 5,
        "revenue_forecast": [500_000, 2_000_000, 5_000_000, 8_000_000, 12_000_000],
        "discount_rate_pct": 15, "royalty_rate_pct": 4,
        "tech_contribution_pct": 35, "patent_remaining_years": 18,
        "risk_adjustment_pct": 25, "monte_carlo_runs": 1000,
    })
    mc = r.output_doc["monte_carlo_simulation"]
    print(f"Monte Carlo P10: ${mc['p10']:,.0f}  P50: ${mc['p50']:,.0f}  P90: ${mc['p90']:,.0f}")
    print(f"  std_dev: ${mc['std_dev']:,.0f}")
    print(f"  시나리오: {list(mc['scenarios'].keys())}")
    print(f"  불확실성 드라이버: {mc['uncertainty_drivers']}")
    print(f"  80% CI: ${mc['confidence_interval_80pct']['lower_usd']:,.0f} ~ ${mc['confidence_interval_80pct']['upper_usd']:,.0f}")

    # P10 < P50 < P90 순서
    assert mc["p10"] < mc["p50"] < mc["p90"], "분포 순서 오류"
    # 시나리오 레이블 확인
    assert set(mc["scenarios"].keys()) == {"bear", "base", "bull"}
    # 불확실성 드라이버 확인
    assert "trl_uncertainty_factor" in mc["uncertainty_drivers"]
    assert mc["uncertainty_drivers"]["trl_uncertainty_factor"] > 0
    # std_dev 확인
    assert mc["std_dev"] > 0
    # TRL 9 시 불확실성이 TRL 5보다 작아야 함
    r2 = ValuationEngine().assess({
        "tech_name": "성숙 기술", "trl": 9,
        "revenue_forecast": [5_000_000, 10_000_000, 15_000_000],
        "discount_rate_pct": 12, "royalty_rate_pct": 4,
        "tech_contribution_pct": 35, "patent_remaining_years": 10,
        "risk_adjustment_pct": 15, "monte_carlo_runs": 1000,
    })
    mc2 = r2.output_doc["monte_carlo_simulation"]
    trl5_factor = mc["uncertainty_drivers"]["trl_uncertainty_factor"]
    trl9_factor = mc2["uncertainty_drivers"]["trl_uncertainty_factor"]
    print(f"  TRL5 불확실성: {trl5_factor:.2f}  TRL9 불확실성: {trl9_factor:.2f}")
    assert trl9_factor < trl5_factor, "TRL 높을수록 불확실성 낮아야 함"


def test_venture_client_recommendation():
    """Venture Client — TRL 6-8 + B2B 시 추천 + BMW i Ventures 등 프로그램 매칭"""
    r = DealStructurer().assess({
        "tech_name": "IoT 스마트팜 AI",
        "trl": 7, "mrl": 6, "arl": 5,
        "ip_strength_score": 65,
        "valuation_usd": 3_000_000,
        "team_commercialization_capability": 3,
        "is_b2b": True,
        "corporate_customer_interest": True,
        "potential_partners": ["Bosch", "Siemens"],
        "target_countries": ["KOR", "EU"],
    })
    rec = r.output_doc["deal_type_recommendation"]["recommended"]
    vc = r.output_doc["venture_client_strategy"]
    print(f"추천 거래방식: {rec}")
    print(f"Venture Client 적용: {vc['applicable']}")
    print(f"매칭 프로그램: {[p['corp'] for p in vc['matched_programs']]}")
    print(f"장점 수: {len(vc['advantages_vs_vc'])}")

    assert rec == "venture_client", f"B2B TRL7이면 venture_client 추천 필요, got: {rec}"
    assert vc["applicable"] is True
    assert len(vc["matched_programs"]) > 0
    assert "no_equity_dilution" in vc["advantages_vs_vc"]
    assert len(vc["contract_structure"]) > 0


def test_venture_client_not_applicable():
    """B2C or TRL 5 이하 시 Venture Client 미추천"""
    r = DealStructurer().assess({
        "tech_name": "소비자앱",
        "trl": 4, "mrl": 3, "arl": 2,
        "ip_strength_score": 80,
        "valuation_usd": 1_000_000,
        "team_commercialization_capability": 2,
        "is_b2b": False,
        "corporate_customer_interest": False,
        "potential_partners": [],
        "target_countries": ["KOR"],
    })
    rec = r.output_doc["deal_type_recommendation"]["recommended"]
    print(f"TRL4 B2C 추천: {rec}")
    assert rec != "venture_client", "TRL4 B2C는 venture_client 미추천"
    # Venture Client 섹션은 TRL 6-8이 아니면 applicable=False
    vc = r.output_doc["venture_client_strategy"]
    assert vc["applicable"] is False


def test_bcg_matrix_objective_position():
    """BCG Matrix X축 객관화 — IP강도·TRL·ARL·특허수명 복합 점수로 competitive_position 보완"""
    r = PortfolioOptimizer().assess({
        "portfolio_techs": [
            {
                "tech_id": "t1", "tech_name": "AI수확량예측",
                "trl": 8, "mrl": 7, "arl": 6,
                "annual_revenue_usd": 600_000, "annual_cost_usd": 80_000,
                "market_growth_pct": 20, "competitive_position": "strong",
                "patent_remaining_years": 18, "licensing_revenue_usd": 120_000,
            },
            {
                "tech_id": "t2", "tech_name": "구형센서",
                "trl": 3, "mrl": 3, "arl": 2,
                "annual_revenue_usd": 15_000, "annual_cost_usd": 55_000,
                "market_growth_pct": 1, "competitive_position": "weak",
                "patent_remaining_years": 2, "licensing_revenue_usd": 0,
            },
            {
                "tech_id": "t3", "tech_name": "신규IoT플랫폼",
                "trl": 6, "mrl": 5, "arl": 4,
                "annual_revenue_usd": 100_000, "annual_cost_usd": 70_000,
                "market_growth_pct": 25, "competitive_position": "medium",
                "patent_remaining_years": 15, "licensing_revenue_usd": 0,
            },
        ],
        "total_ip_budget_usd": 200_000,
        "strategic_focus": "growth",
    })

    plan = r.output_doc["portfolio_optimization_plan"]
    bcg = plan["bcg_matrix"]
    alloc = plan["budget_allocation"]

    print(f"BCG 데이터포인트: {len(bcg['data_points'])}개")
    for dp in bcg["data_points"]:
        print(f"  {dp['tech_name']}: X={dp['x']:.1f}, Y={dp['y']}%, {dp['quadrant']}")

    print(f"예산 배분 (growth 모드):")
    for cat, info in alloc.items():
        print(f"  {cat}: {info['alloc_pct']}% = ${info['budget_usd']:,.0f}")

    # BCG 좌표 검증
    t1_dp = next(dp for dp in bcg["data_points"] if dp["tech_name"] == "AI수확량예측")
    t2_dp = next(dp for dp in bcg["data_points"] if dp["tech_name"] == "구형센서")
    assert t1_dp["x"] > t2_dp["x"], "TRL8·ARL6 > TRL3·ARL2 경쟁점수여야 함"
    assert t1_dp["quadrant"] == "star", f"고TRL고성장 → Star 예상, got {t1_dp['quadrant']}"
    assert t2_dp["quadrant"] == "dog", f"저TRL저성장 → Dog 예상, got {t2_dp['quadrant']}"

    # growth 모드: Star 45% 배분 확인
    assert alloc["star"]["alloc_pct"] == 45.0
    assert alloc["dog"]["alloc_pct"] == 5.0

    # BCG matrix note 확인 (객관화 설명)
    assert "TRL+ARL" in bcg["note"]


if __name__ == "__main__":
    test_monte_carlo_distribution()
    test_venture_client_recommendation()
    test_venture_client_not_applicable()
    test_bcg_matrix_objective_position()
    print("\n경쟁력 80점+ 수정 전체 검증 통과")
