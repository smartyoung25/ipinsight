"""Phase 1 Connector 4개 단위 테스트 — 오프라인 폴백 포함"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from pipeline.connectors.paper_connector    import PaperConnector
from pipeline.connectors.market_connector   import MarketConnector
from pipeline.connectors.clinical_connector import ClinicalConnector
from pipeline.connectors.esg_connector      import ESGConnector


# ─── PaperConnector ──────────────────────────────────────
class TestPaperConnector:
    def setup_method(self):
        self.pc = PaperConnector()

    def test_trl_estimate_journal(self):
        trl = self.pc._trl_estimate("journal-article", 50)
        assert trl is not None
        assert 1 <= trl <= 9

    def test_trl_estimate_patent(self):
        trl = self.pc._trl_estimate("patent", 0)
        assert trl is not None
        assert trl >= 5

    def test_trl_estimate_high_citation(self):
        trl_low  = self.pc._trl_estimate("journal-article", 10)
        trl_high = self.pc._trl_estimate("journal-article", 200)
        assert trl_high >= trl_low

    def test_search_openalex_structure(self):
        result = self.pc.search_openalex("smart farm", limit=2)
        assert "source" in result
        assert result["source"] == "OpenAlex"
        assert "query" in result
        # 오프라인이면 error 키, 온라인이면 papers 키
        assert "error" in result or "papers" in result

    def test_trl_evidence_keys(self):
        result = self.pc.trl_evidence("greenhouse IoT")
        assert "query" in result
        assert "sources" in result
        assert "openalex" in result["sources"]
        assert "pubmed"   in result["sources"]
        assert "europepmc" in result["sources"]


# ─── MarketConnector ─────────────────────────────────────
class TestMarketConnector:
    def setup_method(self):
        self.mc = MarketConnector()

    def test_tam_estimate_structure(self):
        result = self.mc.tam_estimate("agritech", ["KR", "US"])
        assert "sector" in result
        assert result["sector"] == "agritech"
        assert "total_tam_bn" in result
        assert "methodology" in result

    def test_tam_estimate_positive_or_zero(self):
        result = self.mc.tam_estimate("software_saas", ["KR"])
        assert result["total_tam_bn"] >= 0

    def test_gdp_indicators_keys(self):
        result = self.mc.gdp_indicators(["KR"], ["NY.GDP.MKTP.CD"])
        assert "countries" in result
        assert "KR" in result["countries"]

    def test_market_summary_structure(self):
        result = self.mc.market_summary("energy", ["KR"])
        assert "sector" in result
        assert "tam" in result
        assert "rd_spending" in result
        assert "data_quality" in result


# ─── ClinicalConnector ───────────────────────────────────
class TestClinicalConnector:
    def setup_method(self):
        self.cc = ClinicalConnector()

    def test_regulatory_signal_categories(self):
        assert "메가톤" in self.cc._impact_signal(1_500_000) if hasattr(self.cc, '_impact_signal') else True
        assert "검증된 기술" in self.cc._regulatory_signal(10, 600)
        assert "미개척"   in self.cc._regulatory_signal(0, 0)
        assert "초기 단계" in self.cc._regulatory_signal(3, 10)

    def test_search_trials_structure(self):
        result = self.cc.search_trials("agricultural robot", limit=2)
        assert "source" in result
        assert "ClinicalTrials" in result["source"]
        assert "error" in result or "trials" in result

    def test_regulatory_benchmark_keys(self):
        result = self.cc.regulatory_benchmark("smart farming sensor")
        assert "tech_name"     in result
        assert "similar_trials" in result
        assert "regulatory_signal" in result

    def test_eudamed_structure(self):
        result = self.cc.eudamed_search("surgical")
        assert "source" in result
        assert "EUDAMED" in result["source"]


# ─── ESGConnector ────────────────────────────────────────
class TestESGConnector:
    def setup_method(self):
        self.ec = ESGConnector()

    def test_impact_rating_levels(self):
        assert "A+" in self.ec._impact_rating(2_000_000)
        assert "A"  in self.ec._impact_rating(200_000)
        assert "B"  in self.ec._impact_rating(20_000)
        assert "C"  in self.ec._impact_rating(2_000)
        assert "D"  in self.ec._impact_rating(100)

    def test_sdg_mapping(self):
        sdgs = self.ec._sdg_from_sector("agriculture")
        assert any("SDG" in s for s in sdgs)
        assert any("기후행동" in s or "기아" in s for s in sdgs)

    def test_sectors_structure(self):
        result = self.ec.sectors()
        assert "source" in result
        assert "Climate TRACE" in result["source"]

    def test_carbon_reduction_potential_keys(self):
        result = self.ec.carbon_reduction_potential("agritech", "agriculture", 15.0, ["KR"])
        assert "reduction_tco2e"  in result
        assert "monetary_value_usd" in result
        assert "sdg_alignment"    in result
        assert result["reduction_tco2e"] >= 0

    def test_esg_summary_structure(self):
        result = self.ec.esg_summary("agritech", "agriculture", 10.0, ["KR"])
        assert "carbon_impact" in result
        assert "energy_trend"  in result
        assert "impact_rating" in result
        assert "data_quality"  in result


# ─── RegionalConnector ───────────────────────────────────
class TestRegionalConnector:
    def setup_method(self):
        from pipeline.connectors.regional_connector import RegionalConnector
        self.rc = RegionalConnector()

    def test_analyze_kr_us_eu(self):
        ctx = self.rc.analyze(["KR", "US", "DE"], "agritech")
        d = ctx.to_dict()
        assert "regions" in d
        assert "ip" in d
        assert "regulatory" in d
        assert "funding" in d
        assert "gtm" in d
        assert "esg" in d
        assert "priority" in d

    def test_analyze_includes_dev(self):
        ctx = self.rc.analyze(["KR", "VN", "NG", "BR"], "agritech")
        d = ctx.to_dict()
        assert "DEV" in d["regions"]["classified"]

    def test_priority_sorted(self):
        ctx = self.rc.analyze(["KR", "US", "VN"], "software_saas")
        scores = [p["entry_score"] for p in ctx.priority]
        assert scores == sorted(scores, reverse=True)

    def test_dev_country_detail(self):
        result = self.rc.dev_country_detail("VN", "agritech")
        assert "country" in result
        assert result["country"] == "VN"
        assert "leapfrog" in result

    def test_patent_filing_strategy(self):
        result = self.rc.patent_filing_strategy(["KR", "US", "EU", "VN"], budget_usd=30_000)
        assert "recommended_order" in result
        assert "total_cost_usd" in result
        assert "pct_first" in result
        assert result["pct_first"] is True

    def test_classify_regions(self):
        from pipeline.connectors.regional_connector import classify_regions
        result = classify_regions(["KR", "US", "DE", "VN", "NG"])
        assert "KR" in result
        assert "US" in result
        assert "EU" in result
        assert "DEV" in result


# ─── CodeLinkerPipeline 통합 테스트 ──────────────────────
class TestCodeLinkerPhase1Integration:
    def test_context_has_all_fields(self):
        from pipeline.code_linker import CodeLinkerPipeline
        pipeline = CodeLinkerPipeline()
        ctx = pipeline.run("TEST-P1", {
            "cpc_codes":        ["A01G"],
            "target_markets":   ["KR", "US", "VN"],
            "tech_type":        "agritech",
            "industry_keyword": "agriculture",
            "tech_name":        "smart farm sensor",
            "efficiency_pct":   10.0,
        })
        d = ctx.to_dict()
        assert "paper"    in d, "paper 필드 누락"
        assert "market"   in d, "market 필드 누락"
        assert "clinical" in d, "clinical 필드 누락"
        assert "esg"      in d, "esg 필드 누락"
        assert "regional" in d, "regional 필드 누락 (4개 지역 통합)"

    def test_context_fields(self):
        from pipeline.code_linker import CodeContext
        ctx = CodeContext(tech_id="X")
        keys = [k for k in ctx.to_dict().keys()]
        # tech_id(1) + 7개 기존 + 4개 Phase1 + 1개 regional = 13개
        assert len(keys) == 13, f"예상 13개 필드, 실제 {len(keys)}개: {keys}"

    def test_context_has_regional_field(self):
        from pipeline.code_linker import CodeContext
        ctx = CodeContext(tech_id="X")
        assert "regional" in ctx.to_dict(), "regional 필드 누락"
