"""Gap ② 중기 + ③ 장기 보완 모듈 단위 테스트 (6개 모듈)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents import (
    IRDeckGenerator, ESGImpactAssessor, TradeSecretAnalyzer, EcosystemMatcher,
    ExitStrategyDesigner, PatentMaintenanceOptimizer,
)


# ──────────────────────────────────────────────
# 공통 헬퍼
# ──────────────────────────────────────────────
def _assert_stage_result(result, expected_stage: str):
    d = result.to_dict()
    assert d["stage"] == expected_stage, f"stage 불일치: {d['stage']} != {expected_stage}"
    assert d["score"] >= 0
    assert d["gate"] in ("Go", "Hold", "Kill")
    assert isinstance(d["next_actions"], list)
    assert len(d["next_actions"]) >= 1
    assert isinstance(d["output_doc"], dict)
    return d


# ──────────────────────────────────────────────
# ② 중기 Gap 모듈 테스트
# ──────────────────────────────────────────────

class TestIRDeckGenerator:
    def test_basic_vc_deck(self):
        result = IRDeckGenerator().assess({
            "company_name": "KAASA AgriTech",
            "one_liner": "AI 기반 온실 수확량 예측으로 농가 소득 30% 향상",
            "investor_type": "vc",
            "problem_statement": "온실 농가는 수확량 예측 불확실로 과잉생산·손실 발생",
            "solution_description": "딥러닝 + IoT 센서 기반 7일 전 수확량 예측",
            "tam_usd": 5_000_000_000,
            "sam_usd": 500_000_000,
            "som_usd": 10_000_000,
            "growth_rate_pct": 15,
            "revenue_model": "SaaS",
            "arr_usd": 120_000,
            "customer_count": 40,
            "cac_usd": 2_500,
            "ltv_usd": 18_000,
            "patent_count": 3,
            "trl": 7,
            "team_size": 8,
            "prior_exits": 1,
            "funding_ask_usd": 2_000_000,
            "use_of_funds": {"R&D": 40, "영업마케팅": 35, "인프라": 15, "운영": 10},
            "target_valuation_usd": 12_000_000,
            "revenue_3yr": [500_000, 2_000_000, 5_000_000],
            "competitors": ["Priva", "Ridder", "LetsGrow"],
            "key_differentiators": ["국내 작물 특화 AI", "ERA5 기상 연동", "저비용 설치"],
            "exit_targets": ["LG CNS", "KT Agro"],
        })
        d = _assert_stage_result(result, "G6-IR")
        assert "ir_deck" in d["output_doc"]
        assert d["output_doc"]["ir_deck"]["slide_count"] == 12
        assert "pitch_scripts" in d["output_doc"]
        assert "use_of_funds" in d["output_doc"]

    def test_government_deck(self):
        result = IRDeckGenerator().assess({
            "company_name": "GreenFarm",
            "one_liner": "스마트팜 탄소중립 솔루션",
            "investor_type": "government",
            "problem_statement": "농업 탄소배출 감축 필요",
            "solution_description": "태양광 연동 스마트팜",
            "tam_usd": 1_000_000_000,
            "revenue_model": "license",
            "funding_ask_usd": 500_000,
        })
        d = _assert_stage_result(result, "G6-IR")
        assert d["output_doc"]["ir_deck"]["investor_type"] == "정부·공공펀드"

    def test_empty_input_no_crash(self):
        result = IRDeckGenerator().assess({})
        d = _assert_stage_result(result, "G6-IR")
        assert d["score"] < 50  # 데이터 부족 → 낮은 점수


class TestESGImpactAssessor:
    def test_high_esg_score(self):
        result = ESGImpactAssessor().assess({
            "tech_name": "스마트팜 AI",
            "tech_description": "스마트팜 IoT 자동화 시스템으로 탄소 절감 및 일자리 창출",
            "industry_sector": "AgriTech",
            "carbon_reduction_tco2_per_year": 500,
            "energy_efficiency_improvement_pct": 20,
            "uses_hazardous_materials": False,
            "biodiversity_impact": "positive",
            "jobs_created": 15,
            "target_vulnerable_groups": True,
            "health_safety_improvement": "농약 사용량 40% 감소로 농업인 건강 개선",
            "community_programs": True,
            "publishes_impact_report": True,
            "board_female_pct": 33,
            "has_ethics_policy": True,
            "data_privacy_certified": True,
            "beneficiaries_count": 200,
        })
        d = _assert_stage_result(result, "G10-ESG")
        assert d["score"] >= 60
        assert "sdg_alignment" in d["output_doc"]
        assert "esg_scorecard" in d["output_doc"]
        sdg = d["output_doc"]["sdg_alignment"]
        assert sdg["sdg_count"] >= 1

    def test_sdg_keyword_matching(self):
        result = ESGImpactAssessor().assess({
            "tech_name": "태양광 ESS",
            "tech_description": "태양광 에너지저장 배터리 시스템으로 탄소중립 기여",
            "industry_sector": "Energy_CleanTech",
            "uses_hazardous_materials": False,
            "biodiversity_impact": "neutral",
        })
        d = _assert_stage_result(result, "G10-ESG")
        sdg_names = [s["sdg_name"] for s in d["output_doc"]["sdg_alignment"]["matched_sdgs"]]
        assert any("에너지" in n or "기후" in n for n in sdg_names)

    def test_low_esg_score(self):
        result = ESGImpactAssessor().assess({
            "tech_name": "산업 화학 공정",
            "uses_hazardous_materials": True,
            "biodiversity_impact": "negative",
            "jobs_created": 0,
        })
        d = _assert_stage_result(result, "G10-ESG")
        assert d["score"] < 50


class TestTradeSecretAnalyzer:
    def test_recommend_trade_secret(self):
        result = TradeSecretAnalyzer().assess({
            "tech_name": "독점 AI 알고리즘",
            "tech_type": "algorithm",
            "trl": 6,
            "reverse_engineerable": False,
            "licensing_goal": False,
            "competitor_count": 2,
            "complex_product": False,
            "software_only": False,
            "annual_revenue_protected_usd": 1_000_000,
            "analysis_years": 10,
            "employee_nda_in_place": True,
            "key_person_dependency": False,
        })
        d = _assert_stage_result(result, "G1-TS")
        assert d["output_doc"]["recommended_strategy"]["strategy"] == "trade_secret"
        assert "cost_benefit_comparison" in d["output_doc"]
        assert "risk_assessment" in d["output_doc"]

    def test_recommend_patent_for_licensing(self):
        result = TradeSecretAnalyzer().assess({
            "tech_name": "제조 공정 특허",
            "tech_type": "process",
            "trl": 7,
            "reverse_engineerable": True,
            "licensing_goal": True,
            "competitor_count": 5,
            "employee_nda_in_place": True,
        })
        d = _assert_stage_result(result, "G1-TS")
        assert d["output_doc"]["recommended_strategy"]["strategy"] == "patent"

    def test_hybrid_for_software(self):
        result = TradeSecretAnalyzer().assess({
            "tech_name": "SaaS 플랫폼",
            "tech_type": "software",
            "software_only": True,
            "trl": 5,
        })
        d = _assert_stage_result(result, "G1-TS")
        assert d["output_doc"]["recommended_strategy"]["strategy"] == "hybrid"

    def test_cost_comparison_all_strategies(self):
        result = TradeSecretAnalyzer().assess({
            "tech_name": "신소재",
            "tech_type": "product",
            "annual_revenue_protected_usd": 2_000_000,
            "analysis_years": 10,
        })
        d = _assert_stage_result(result, "G1-TS")
        comparison = d["output_doc"]["cost_benefit_comparison"]
        assert "patent" in comparison
        assert "trade_secret" in comparison
        assert "hybrid" in comparison
        for strat in comparison.values():
            assert "total_cost_usd" in strat
            assert "roi_ratio" in strat


class TestEcosystemMatcher:
    def test_smartfarm_matching(self):
        result = EcosystemMatcher().assess({
            "tech_name": "스마트팜 AI",
            "industry_sector": "SmartFarm",
            "trl": 6,
            "commercialization_type": "startup",
            "partnership_goals": ["자금조달", "시장진입", "공동개발"],
            "target_countries": ["KOR", "USA"],
        })
        d = _assert_stage_result(result, "G3-Eco")
        assert "ecosystem_map" in d["output_doc"]
        assert d["output_doc"]["ecosystem_map"]["total_categories_matched"] >= 2
        assert "top_recommendations" in d["output_doc"]
        assert len(d["output_doc"]["domain_partner_pool"]) > 0

    def test_low_trl_filters_corporate(self):
        result = EcosystemMatcher().assess({
            "tech_name": "초기 기술",
            "industry_sector": "BioTech",
            "trl": 2,
            "commercialization_type": "spinout",
            "partnership_goals": ["공동개발"],
        })
        d = _assert_stage_result(result, "G3-Eco")
        matches = d["output_doc"]["ecosystem_map"]["all_matches"]
        cats = [m["category"] for m in matches]
        assert "corporate_partner" not in cats  # TRL 2는 corporate(TRL 5 이상) 제외

    def test_priority_ordering(self):
        result = EcosystemMatcher().assess({
            "tech_name": "AI SW",
            "industry_sector": "AI_Software",
            "trl": 5,
            "commercialization_type": "startup",
            "partnership_goals": ["자금조달", "멘토링"],
        })
        d = _assert_stage_result(result, "G3-Eco")
        top = d["output_doc"]["top_recommendations"]
        if len(top) >= 2:
            assert top[0]["goal_match_score"] >= top[-1]["goal_match_score"]


# ──────────────────────────────────────────────
# ③ 장기 Gap 모듈 테스트
# ──────────────────────────────────────────────

class TestExitStrategyDesigner:
    def test_strategic_ma_feasible(self):
        result = ExitStrategyDesigner().assess({
            "company_name": "KAASA AgriTech",
            "trl": 8,
            "arr_usd": 1_500_000,
            "ebitda_usd": -200_000,
            "growth_rate_yoy_pct": 80,
            "current_valuation_usd": 10_000_000,
            "total_invested_usd": 3_000_000,
            "founder_equity_pct": 55,
            "investor_equity_pct": 35,
            "target_exit_years": 3,
            "preferred_exit": "strategic_ma",
            "strategic_acquirer_candidates": ["LG CNS", "KT", "농협경제지주"],
            "industry_sector": "AgriTech",
            "ip_strength_score": 75,
            "patent_count": 5,
        })
        d = _assert_stage_result(result, "G10-Exit")
        assert "exit_scenarios" in d["output_doc"]
        assert len(d["output_doc"]["exit_scenarios"]) == 5
        # 전략적 M&A 시나리오 확인
        strategic = next(s for s in d["output_doc"]["exit_scenarios"] if s["exit_type"] == "strategic_ma")
        assert "valuation_mid" in strategic
        assert strategic["moic"] >= 0

    def test_license_exit_low_arr(self):
        result = ExitStrategyDesigner().assess({
            "company_name": "EarlyStage",
            "trl": 5,
            "arr_usd": 50_000,
            "growth_rate_yoy_pct": 30,
            "total_invested_usd": 500_000,
            "founder_equity_pct": 70,
            "investor_equity_pct": 20,
            "target_exit_years": 3,
            "strategic_acquirer_candidates": [],
        })
        d = _assert_stage_result(result, "G10-Exit")
        # 낮은 ARR → 라이선스 엑시트가 feasible
        license_s = next(s for s in d["output_doc"]["exit_scenarios"] if s["exit_type"] == "license_exit")
        assert license_s["feasible"] is True

    def test_ipo_requires_high_arr(self):
        result = ExitStrategyDesigner().assess({
            "company_name": "PreIPO",
            "trl": 9,
            "arr_usd": 500_000,  # IPO 기준 $10M 미달
            "growth_rate_yoy_pct": 60,
            "total_invested_usd": 5_000_000,
            "founder_equity_pct": 40,
            "investor_equity_pct": 50,
            "target_exit_years": 5,
        })
        d = _assert_stage_result(result, "G10-Exit")
        ipo = next(s for s in d["output_doc"]["exit_scenarios"] if s["exit_type"] == "ipo")
        assert ipo["feasible"] is False  # ARR < $10M → IPO 불가

    def test_scores_and_actions(self):
        result = ExitStrategyDesigner().assess({
            "trl": 7,
            "arr_usd": 800_000,
            "growth_rate_yoy_pct": 50,
            "total_invested_usd": 2_000_000,
            "founder_equity_pct": 50,
            "investor_equity_pct": 40,
            "strategic_acquirer_candidates": ["CompA", "CompB", "CompC"],
        })
        d = _assert_stage_result(result, "G10-Exit")
        assert d["score"] > 0
        assert len(d["next_actions"]) >= 1


class TestPatentMaintenanceOptimizer:
    def _sample_portfolio(self):
        return [
            {
                "patent_id": "KR-2021-001234",
                "title": "AI 수확량 예측 방법",
                "filing_year": 2021,
                "countries": ["KOR", "USA", "EU"],
                "remaining_years": 15,
                "annual_licensing_revenue_usd": 50_000,
                "strategic_importance": 85,
                "trl": 7,
                "competitor_blocking_value": 30_000,
                "market_size_usd": 500_000_000,
            },
            {
                "patent_id": "KR-2019-005678",
                "title": "레거시 센서 인터페이스",
                "filing_year": 2019,
                "countries": ["KOR"],
                "remaining_years": 13,
                "annual_licensing_revenue_usd": 0,
                "strategic_importance": 20,
                "trl": 5,
                "competitor_blocking_value": 0,
                "market_size_usd": 10_000_000,
            },
            {
                "patent_id": "KR-2022-009012",
                "title": "IoT 데이터 전처리 알고리즘",
                "filing_year": 2022,
                "countries": ["KOR", "CHN"],
                "remaining_years": 18,
                "annual_licensing_revenue_usd": 20_000,
                "strategic_importance": 60,
                "trl": 6,
                "competitor_blocking_value": 15_000,
                "market_size_usd": 200_000_000,
            },
        ]

    def test_portfolio_decisions(self):
        result = PatentMaintenanceOptimizer().assess({
            "portfolio": self._sample_portfolio(),
            "annual_budget_usd": 20_000,
            "company_stage": "growth",
        })
        d = _assert_stage_result(result, "G1-Maint")
        assert "portfolio_summary" in d["output_doc"]
        ps = d["output_doc"]["portfolio_summary"]
        assert ps["total_patents"] == 3
        assert ps["maintain_count"] + ps["transfer_count"] + ps["abandon_count"] == 3

    def test_high_value_patent_maintained(self):
        result = PatentMaintenanceOptimizer().assess({
            "portfolio": [
                {
                    "patent_id": "HIGH-001",
                    "title": "핵심 특허",
                    "countries": ["KOR"],
                    "remaining_years": 10,
                    "annual_licensing_revenue_usd": 100_000,
                    "strategic_importance": 90,
                    "competitor_blocking_value": 50_000,
                }
            ],
            "annual_budget_usd": 50_000,
        })
        d = _assert_stage_result(result, "G1-Maint")
        decisions = d["output_doc"]["patent_decisions"]
        assert decisions[0]["decision"] == "유지"

    def test_zero_value_patent_abandoned(self):
        result = PatentMaintenanceOptimizer().assess({
            "portfolio": [
                {
                    "patent_id": "LOW-001",
                    "title": "구형 특허",
                    "countries": ["KOR"],
                    "remaining_years": 5,
                    "annual_licensing_revenue_usd": 0,
                    "strategic_importance": 10,
                    "competitor_blocking_value": 0,
                }
            ],
            "annual_budget_usd": 10_000,
        })
        d = _assert_stage_result(result, "G1-Maint")
        decisions = d["output_doc"]["patent_decisions"]
        assert decisions[0]["decision"] == "포기"

    def test_country_optimization(self):
        result = PatentMaintenanceOptimizer().assess({
            "portfolio": [
                {
                    "patent_id": "MULTI-001",
                    "title": "글로벌 특허",
                    "countries": ["KOR", "USA", "EU", "JPN", "CHN"],
                    "remaining_years": 10,
                    "annual_licensing_revenue_usd": 5_000,
                    "strategic_importance": 40,
                    "competitor_blocking_value": 2_000,
                }
            ],
        })
        d = _assert_stage_result(result, "G1-Maint")
        decisions = d["output_doc"]["patent_decisions"]
        country_opt = decisions[0]["country_optimization"]
        assert len(country_opt) == 5
        # USA는 비용이 $2,200로 가장 높음 → ROI 낮을 것
        usa = next(c for c in country_opt if c["country"] == "USA")
        assert usa["annual_cost_usd"] == 2_200

    def test_empty_portfolio(self):
        result = PatentMaintenanceOptimizer().assess({"portfolio": []})
        d = _assert_stage_result(result, "G1-Maint")
        assert d["score"] == 0.0


# ──────────────────────────────────────────────
# API 엔드포인트 통합 테스트
# ──────────────────────────────────────────────

class TestGapEndpoints:
    def setup_method(self):
        from fastapi.testclient import TestClient
        from api.main import app
        self.client = TestClient(app)

    def test_ir_deck_endpoint(self):
        resp = self.client.post("/gap/ir-deck", json={
            "tech_id": "test-ir",
            "input_data": {
                "company_name": "TestCo",
                "one_liner": "AI 솔루션",
                "investor_type": "vc",
                "funding_ask_usd": 1_000_000,
            }
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["stage"] == "G6-IR"

    def test_esg_endpoint(self):
        resp = self.client.post("/gap/esg-impact", json={
            "tech_id": "test-esg",
            "input_data": {
                "tech_name": "클린테크",
                "tech_description": "탄소 절감 신재생 에너지",
                "uses_hazardous_materials": False,
                "biodiversity_impact": "positive",
            }
        })
        assert resp.status_code == 200
        assert resp.json()["stage"] == "G10-ESG"

    def test_trade_secret_endpoint(self):
        resp = self.client.post("/gap/trade-secret", json={
            "tech_id": "test-ts",
            "input_data": {
                "tech_name": "알고리즘",
                "tech_type": "algorithm",
                "trl": 6,
                "reverse_engineerable": False,
            }
        })
        assert resp.status_code == 200
        assert resp.json()["stage"] == "G1-TS"

    def test_ecosystem_endpoint(self):
        resp = self.client.post("/gap/ecosystem-match", json={
            "tech_id": "test-eco",
            "input_data": {
                "tech_name": "스마트팜",
                "industry_sector": "SmartFarm",
                "trl": 5,
                "partnership_goals": ["자금조달"],
            }
        })
        assert resp.status_code == 200
        assert resp.json()["stage"] == "G3-Eco"

    def test_exit_strategy_endpoint(self):
        resp = self.client.post("/gap/exit-strategy", json={
            "tech_id": "test-exit",
            "input_data": {
                "company_name": "ExitCo",
                "trl": 7,
                "arr_usd": 800_000,
                "growth_rate_yoy_pct": 60,
                "total_invested_usd": 2_000_000,
                "founder_equity_pct": 55,
                "investor_equity_pct": 35,
            }
        })
        assert resp.status_code == 200
        assert resp.json()["stage"] == "G10-Exit"

    def test_patent_maintenance_endpoint(self):
        resp = self.client.post("/gap/patent-maintenance", json={
            "tech_id": "test-maint",
            "input_data": {
                "portfolio": [{
                    "patent_id": "KR-001",
                    "title": "테스트 특허",
                    "countries": ["KOR"],
                    "remaining_years": 10,
                    "annual_licensing_revenue_usd": 5_000,
                    "strategic_importance": 50,
                    "competitor_blocking_value": 2_000,
                }],
                "annual_budget_usd": 5_000,
            }
        })
        assert resp.status_code == 200
        assert resp.json()["stage"] == "G1-Maint"

    def test_gap_stages_list(self):
        resp = self.client.get("/gap/stages")
        assert resp.status_code == 200
        data = resp.json()["gap_modules"]
        assert "critical_gap_1" in data
        assert "medium_gap_2" in data
        assert "long_term_gap_3" in data
        assert len(data["medium_gap_2"]) == 4
        assert len(data["long_term_gap_3"]) == 2
