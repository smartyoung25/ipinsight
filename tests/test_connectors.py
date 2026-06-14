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

    def test_analyze_jp_cn_in_ru(self):
        """JP·CN·IN·RU 독립 지역 분기 검증"""
        ctx = self.rc.analyze(["JP", "CN", "IN", "RU"], "manufacturing")
        d = ctx.to_dict()
        classified = d["regions"]["classified"]
        assert "JP" in classified, "일본 JP 독립 지역 없음"
        assert "CN" in classified, "중국 CN 독립 지역 없음"
        assert "IN" in classified, "인도 IN 독립 지역 없음"
        assert "RU" in classified, "러시아 RU 독립 지역 없음"

    def test_jp_ip_env(self):
        """일본 IP 환경 데이터 확인"""
        from pipeline.connectors.regional_connector import IP_ENV
        jp = IP_ENV.get("JP", {})
        assert "JPO" in jp.get("patent_office", "")
        assert jp.get("utility_model") is True
        assert jp.get("avg_grant_months") == 14

    def test_cn_special_risks(self):
        """중국 특수 리스크 데이터 확인"""
        from pipeline.connectors.regional_connector import IP_ENV
        cn = IP_ENV.get("CN", {})
        # special_risks 또는 caution 중 하나가 있어야 함
        assert "special_risks" in cn or "caution" in cn
        assert len(cn.get("special_risks", cn.get("caution", ""))) > 0

    def test_ru_sanction_risk(self):
        """러시아 제재 리스크 데이터 확인"""
        from pipeline.connectors.regional_connector import IP_ENV, FUNDING_ENV
        ru_ip  = IP_ENV.get("RU", {})
        ru_fin = FUNDING_ENV.get("RU", {})
        assert "sanction_risk" in ru_ip
        assert "sanction_risk" in ru_fin

    def test_sanction_check(self):
        """제재 체크 기능"""
        result = self.rc.sanction_check(["KR", "US", "RU", "CN", "VN"])
        checks = {c["country"]: c["risk_level"] for c in result["sanction_check"]}
        assert checks["RU"] == "HIGH"
        assert checks["CN"] == "MEDIUM"
        assert checks["KR"] == "LOW"
        assert checks["VN"] == "LOW"

    def test_analyze_includes_dev(self):
        ctx = self.rc.analyze(["KR", "VN", "NG", "BR"], "agritech")
        d = ctx.to_dict()
        assert "DEV" in d["regions"]["classified"]

    def test_in_not_in_dev(self):
        """IN이 DEV에서 독립했는지 확인"""
        from pipeline.connectors.regional_connector import classify_region
        assert classify_region("IN") == "IN", "인도는 DEV가 아닌 IN 지역이어야 함"
        assert classify_region("VN") == "DEV", "베트남은 DEV 지역이어야 함"

    def test_priority_sorted(self):
        ctx = self.rc.analyze(["KR", "US", "JP", "CN", "IN", "RU"], "manufacturing")
        scores = [p["entry_score"] for p in ctx.priority]
        assert scores == sorted(scores, reverse=True)
        # 러시아는 제재로 최하위여야 함
        ru_entry = next(p for p in ctx.priority if p["region"] == "RU")
        assert ru_entry["entry_score"] <= 40

    def test_country_profile_jp(self):
        result = self.rc.country_profile("JP", "agritech")
        assert result["region"] == "JP"
        assert "patent_office" in result["ip"]

    def test_patent_filing_strategy(self):
        result = self.rc.patent_filing_strategy(["KR", "US", "JP", "CN", "IN"], budget_usd=30_000)
        assert "recommended_order" in result
        assert "total_cost_usd" in result
        assert result["pct_first"] is True
        regions = [o["region"] for o in result["recommended_order"]]
        assert "JP" in regions
        assert "CN" in regions
        assert "IN" in regions

    def test_classify_regions(self):
        from pipeline.connectors.regional_connector import classify_regions
        result = classify_regions(["KR", "US", "DE", "JP", "CN", "IN", "RU", "VN", "NG"])
        assert "KR"  in result
        assert "US"  in result
        assert "EU"  in result
        assert "JP"  in result
        assert "CN"  in result
        assert "IN"  in result
        assert "RU"  in result
        assert "DEV" in result


# ─── TradeConnector ──────────────────────────────────────
class TestTradeConnector:
    def setup_method(self):
        from pipeline.connectors.trade_connector import TradeConnector
        self.tc = TradeConnector()

    def test_trade_flow_structure(self):
        result = self.tc.trade_flow("8432", "KR", "2022")
        assert "source" in result
        assert "UN Comtrade" in result["source"]
        assert "hs_code" in result
        assert "total_value_usd" in result or "error" in result

    def test_sector_summary_keys(self):
        result = self.tc.sector_trade_summary("agritech", ["KR", "US"], "2022")
        assert "source" in result
        assert "tech_type" in result
        assert "by_country" in result or "error" in result

    def test_market_size_from_trade(self):
        result = self.tc.market_size_from_trade("agritech", ["KR", "US"])
        assert "total_trade_bn_usd" in result
        assert result["total_trade_bn_usd"] >= 0
        assert "methodology" in result

    def test_hs_codes_defined(self):
        from pipeline.connectors.trade_connector import HS_CODES
        assert "agritech" in HS_CODES
        assert "medical_device" in HS_CODES
        assert "energy" in HS_CODES
        assert len(HS_CODES["agritech"]) >= 3


# ─── KiprisConnector ─────────────────────────────────────
class TestKiprisConnector:
    def setup_method(self):
        from pipeline.connectors.kipris_connector import KiprisConnector
        self.kc = KiprisConnector()

    def test_available_without_key(self, monkeypatch):
        monkeypatch.delenv("KIPRIS_API_KEY", raising=False)
        assert self.kc.available() is False

    def test_fetch_without_key_returns_none(self, monkeypatch):
        monkeypatch.delenv("KIPRIS_API_KEY", raising=False)
        result = self.kc.fetch("KR10-2021-0123456")
        assert result is None

    def test_build_application_candidates_kr_format(self):
        from pipeline.connectors.kipris_connector import _build_application_candidates
        candidates = _build_application_candidates("KR10-2021-0123456")
        assert any(c.startswith("10") for c in candidates)

    def test_build_application_candidates_13digit(self):
        from pipeline.connectors.kipris_connector import _build_application_candidates
        candidates = _build_application_candidates("1012345678901")
        # 13자리 → 10자리 추출
        assert any(len(c) == 10 for c in candidates)

    def test_parse_kipris_xml_empty_returns_none(self):
        from pipeline.connectors.kipris_connector import _parse_kipris_xml
        assert _parse_kipris_xml("<root></root>") is None

    def test_parse_kipris_xml_with_title(self):
        from pipeline.connectors.kipris_connector import _parse_kipris_xml
        xml = "<response><inventionTitle>스마트팜 시스템</inventionTitle><astrtCont>요약내용</astrtCont></response>"
        result = _parse_kipris_xml(xml)
        assert result is not None
        assert result["title"] == "스마트팜 시스템"
        assert "요약내용" in result["abstract"]


# ─── GooglePatentsConnector ───────────────────────────────
class TestGooglePatentsConnector:
    def setup_method(self):
        from pipeline.connectors.google_patents_connector import GooglePatentsConnector
        self.gc = GooglePatentsConnector()

    def test_available_with_httpx(self):
        assert self.gc.available() is True

    def test_normalize_kr_patent(self):
        from pipeline.connectors.google_patents_connector import _normalize_patent_number
        norm = _normalize_patent_number("KR10-2021-0123456")
        assert norm.startswith("KR")
        assert "10" in norm

    def test_normalize_us_patent(self):
        from pipeline.connectors.google_patents_connector import _normalize_patent_number
        norm = _normalize_patent_number("US20210123456")
        assert norm.startswith("US")

    def test_get_search_variants_no_empty(self):
        from pipeline.connectors.google_patents_connector import _get_search_variants
        variants = _get_search_variants("KR10-2021-0123456A1")
        assert all(v for v in variants)  # 빈 문자열 없음

    def test_parse_html_regex_fallback(self):
        from pipeline.connectors.google_patents_connector import _parse_html_regex
        html = "<html><title>스마트팜 장치 - Google Patents</title><div class='abstract'>초록내용</div></html>"
        result = _parse_html_regex(html, "http://test")
        assert result is not None
        assert "스마트팜 장치" in result["title"]


# ─── report_deps ─────────────────────────────────────────
class TestReportDeps:
    def test_all_reports_defined(self):
        from api.report_deps import REPORT_DEFS, ALL_REPORTS
        for rid in ALL_REPORTS:
            assert rid in REPORT_DEFS

    def test_r5_r6_dependency(self):
        from api.report_deps import check_availability, R5, R6
        # R5 미완료 → R6 불가
        avail = check_availability(R6, {})
        assert not avail.available
        assert R5 in avail.missing_deps

    def test_r5_r2_r7_dependency(self):
        from api.report_deps import check_availability, R2, R5, R7
        # R5+R2 완료 → R7 가능
        completed = {R5: {"status": "completed"}, R2: {"status": "completed"}}
        avail = check_availability(R7, completed)
        assert avail.available

    def test_r8_or_dependency(self):
        from api.report_deps import check_availability, R1, R2, R8
        # R1만 완료 → R8 가능 (OR 조건)
        avail = check_availability(R8, {R1: {"status": "completed"}})
        assert avail.available

    def test_r8_no_dep_unavailable(self):
        from api.report_deps import check_availability, R8
        avail = check_availability(R8, {})
        assert not avail.available
        assert avail.missing_or_deps  # OR 그룹 미충족

    def test_tier_1_no_deps(self):
        from api.report_deps import check_availability, R1, R3, R4, R9
        for rid in [R1, R3, R4, R9]:
            avail = check_availability(rid, {})
            assert avail.available, f"{rid} Tier1 보고서가 선행 보고서 없이 가용해야 함"

    def test_cascade_stale(self):
        from api.report_deps import mark_stale_cascade, R5, R6
        completed = {R6: {"status": "completed"}}
        staled = mark_stale_cascade(completed, R5)
        assert R6 in staled
        assert completed[R6]["status"] == "stale"

    def test_get_all_availability_sorted_by_tier(self):
        from api.report_deps import get_all_availability
        results = get_all_availability({})
        tiers = [r.tier for r in results]
        assert tiers == sorted(tiers)


# ─── ScreeningAgent ───────────────────────────────────────
class TestScreeningAgent:
    def setup_method(self):
        from agents.screening_agent import ScreeningAgent
        self.agent = ScreeningAgent()

    def test_assess_returns_stage_result(self):
        from agents.base_agent import StageResult
        result = self.agent.assess({
            "tech_id": "TEST-SCR-001",
            "pcml_result": {
                "shared_variables": {
                    "self_core_nodes": 5,
                    "support_coverage": 0.6,
                    "black_box_core_ratio": 0.2,
                    "legal_status_score": 0.8,
                    "family_coverage_rate": 0.3,
                },
                "patent_layer": {
                    "patent_info": {
                        "title": "테스트 발명",
                        "ipc_codes": ["A01G9/24"],
                        "application_number": "1020210123456",
                        "applicant": "테스트 주식회사",
                    }
                },
            },
            "scope": "basic",
        })
        assert isinstance(result, StageResult)
        assert result.stage == "G1.6-SCR"
        assert result.gate in ("G1", "G2", "G3", "G4")
        assert 0 <= result.score <= 100

    def test_scr_report_structure(self):
        result = self.agent.assess({"tech_id": "T", "pcml_result": {}, "scope": "basic"})
        out = result.output_doc
        assert "scrReport" in out
        scr = out["scrReport"]
        assert "gateRouting" in scr
        assert "kpiRatings" in scr
        assert "hardStops" in scr
        assert len(scr["hardStops"]) == 5

    def test_kpi_grades_valid(self):
        result = self.agent.assess({
            "tech_id": "T",
            "pcml_result": {
                "shared_variables": {
                    "self_core_nodes": 7,
                    "support_coverage": 0.8,
                    "black_box_core_ratio": 0.1,
                    "legal_status_score": 0.9,
                    "family_coverage_rate": 0.5,
                }
            },
        })
        kpi = result.output_doc["scrReport"]["kpiRatings"]
        for key in ("kpi1_claimStrength", "kpi4_evasionResistance", "kpi9_legalStability"):
            assert kpi[key]["grade"] in ("上", "中", "下"), f"{key} grade 유효하지 않음"

    def test_no_pct_hard_stop_detected(self):
        result = self.agent.assess({
            "tech_id": "T",
            "pcml_result": {
                "shared_variables": {"family_coverage_rate": 0.0}
            },
        })
        stops = result.output_doc["scrReport"]["hardStops"]
        no_pct = next(s for s in stops if s["id"] == "no_pct")
        assert no_pct["detected"] is True

    def test_high_core_nodes_gate_g1_or_g2(self):
        result = self.agent.assess({
            "tech_id": "T",
            "pcml_result": {
                "shared_variables": {
                    "self_core_nodes": 8,
                    "support_coverage": 1.0,
                    "black_box_core_ratio": 0.0,
                    "legal_status_score": 1.0,
                    "family_coverage_rate": 1.0,
                }
            },
        })
        assert result.gate in ("G1", "G2")


# ─── Reports API 엔드포인트 ──────────────────────────────
class TestReportsEndpoints:
    def test_definitions_all(self, client, auth_token):
        r = client.get(
            "/reports/definitions/all",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert r.status_code == 200
        body = r.json()
        for rid in ("R1_investment", "R5_valuation", "R8_gov_ir"):
            assert rid in body, f"{rid} 없음"
        # R5는 Tier 2
        assert body["R5_valuation"]["tier"] == 2
        # R8은 Tier 3
        assert body["R8_gov_ir"]["tier"] == 3

    def test_availability_tier1_no_stores(self, client, auth_token):
        r = client.post(
            "/reports/availability",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"completed": {}, "has_store_a": False, "has_store_b": False},
        )
        assert r.status_code == 200
        body = r.json()
        # store 없으면 아무것도 가용 불가
        for item in body:
            assert not item["available"]

    def test_availability_tier1_with_stores(self, client, auth_token):
        r = client.post(
            "/reports/availability",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"completed": {}, "has_store_a": True, "has_store_b": True},
        )
        assert r.status_code == 200
        body = r.json()
        # Tier 1 보고서(R1~R4, R9)는 가용해야 함
        tier1 = [i for i in body if i["tier"] == 1]
        for item in tier1:
            assert item["available"], f"Tier1 {item['report_id']} 불가"

    def test_availability_r6_requires_r5(self, client, auth_token):
        r = client.post(
            "/reports/availability",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "completed": {"R5_valuation": {"status": "completed"}},
                "has_store_a": True, "has_store_b": True,
            },
        )
        body = r.json()
        r6 = next(i for i in body if i["report_id"] == "R6_ir")
        assert r6["available"]

    def test_generate_tier1_fallback(self, client, auth_token):
        """LLM 없으면 폴백 반환 (구조만 검증)"""
        r = client.post(
            "/reports/generate",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "tech_id": "TEST-R1-001",
                "report_id": "R1_investment",
                "tier": "LITE",
                "store_a": {"_version": 1},
                "store_b": {"_version": 1},
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert "reportId" in body
        assert "content" in body
        assert body["reportType"] == "R1_investment"

    def test_generate_invalid_report_id(self, client, auth_token):
        r = client.post(
            "/reports/generate",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"tech_id": "X", "report_id": "R99_invalid"},
        )
        assert r.status_code == 400

    def test_generate_r6_without_r5_fails(self, client, auth_token):
        """R5 미완료 상태에서 R6 생성 시도 → 422"""
        r = client.post(
            "/reports/generate",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "tech_id": "TEST-R6-FAIL",
                "report_id": "R6_ir",
                "store_a": {},
                "store_b": {},
            },
        )
        assert r.status_code == 422

    def test_cascade_stale(self, client, auth_token):
        r = client.post(
            "/reports/cascade-stale",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "completed": {"R6_ir": {"status": "completed"}},
                "changed_report_id": "R5_valuation",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert "R6_ir" in body["staled"]

    def test_get_nonexistent_report(self, client, auth_token):
        r = client.get(
            "/reports/R1_investment",
            params={"tech_id": "NONEXISTENT"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert r.status_code == 404


# ─── 신규 엔드포인트 통합 테스트 ─────────────────────────
class TestNewEndpoints:
    def test_fetch_patent_no_id(self, client, auth_token):
        r = client.post(
            "/ip/fetch-patent",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"patent_id": ""},
        )
        # patent_id가 빈 문자열이면 404 (KIPRIS+Google 모두 실패)
        assert r.status_code in (404, 422)

    def test_screening_minimal_input(self, client, auth_token):
        r = client.post(
            "/ip/screening",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"tech_id": "TEST-SCR-API", "input_data": {"scope": "basic"}},
        )
        assert r.status_code == 200
        body = r.json()
        assert "gate" in body
        assert "scrReport" in body
        assert body["stage"] == "G1.6-SCR"

    def test_health_has_kipris_connector(self, client):
        body = client.get("/health").json()
        assert "kipris" in body["connectors"]
        assert "google_patents" in body["connectors"]
        assert body["connectors"]["google_patents"] is True


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
        # tech_id(1) + 7개 기존 + 4개 Phase1 + trade(1) + regional(1) = 14개
        assert len(keys) == 14, f"예상 14개 필드, 실제 {len(keys)}개: {keys}"

    def test_context_has_regional_field(self):
        from pipeline.code_linker import CodeContext
        ctx = CodeContext(tech_id="X")
        assert "regional" in ctx.to_dict(), "regional 필드 누락"


# ─── ★ A급 강화 엔드포인트 테스트 ───────────────────────────
class TestAGradeEndpoints:
    """G4 인터뷰·G10 KPI·analyze-chain·G5 Unit Economics 검증"""

    # ── G4 인터뷰 ──────────────────────────────────────────
    def test_g4_save_interviews(self, client, auth_token):
        r = client.post(
            "/g4/interviews",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "tech_id": "TECH-G4-TEST",
                "interviews": [
                    {
                        "customer_type": "온실농가",
                        "pain_point": "수확량 예측 불확실",
                        "willingness_to_pay": 500,
                        "urgency_1to5": 4,
                        "jtbd_functional": "수확 예측으로 계약재배",
                        "jtbd_emotional": "불안감 해소",
                    }
                ] * 35,
                "loi_count": 2,
                "poc_requests": 3,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 35
        assert body["status"] == "진행중"  # 30건 이상 but < 100

    def test_g4_get_interviews(self, client, auth_token):
        # 먼저 저장
        client.post(
            "/g4/interviews",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "tech_id": "TECH-G4-GET",
                "interviews": [
                    {"customer_type": "유통업체", "pain_point": "수급 예측 실패",
                     "willingness_to_pay": 300, "urgency_1to5": 3}
                ] * 5,
                "loi_count": 0, "poc_requests": 0,
            },
        )
        r = client.get(
            "/g4/interviews/TECH-G4-GET",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total_interviews"] >= 5
        assert "icorps" in body
        assert body["icorps"]["phase1_min"] == 30

    def test_g4_assess_uses_stored_interviews(self, client, auth_token):
        tech_id = "TECH-G4-ASSESS"
        # 인터뷰 저장
        client.post(
            "/g4/interviews",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "tech_id": tech_id,
                "interviews": [
                    {"customer_type": "농가", "pain_point": "폐기손실",
                     "willingness_to_pay": 400, "urgency_1to5": 4,
                     "jtbd_functional": "예측"}
                ] * 40,
                "loi_count": 3, "poc_requests": 2,
            },
        )
        r = client.post(
            "/g4/assess",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"tech_id": tech_id, "input_data": {}},
        )
        assert r.status_code == 200
        body = r.json()
        assert "result" in body
        assert body["result"]["score"] > 0

    # ── G10 KPI 피드 ───────────────────────────────────────
    def test_g10_kpi_record(self, client, auth_token):
        r = client.post(
            "/g10/kpi",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"tech_id": "TECH-KPI-01", "kpi_key": "revenue_usd", "value": 150000},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["recorded"] is True
        assert body["kpi_key"] == "revenue_usd"

    def test_g10_kpi_batch(self, client, auth_token):
        r = client.post(
            "/g10/kpi/batch",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "tech_id": "TECH-KPI-BATCH",
                "actuals": {
                    "revenue_usd": 200000,
                    "royalty_usd": 50000,
                    "new_customers": 8,
                },
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["recorded"] == 3

    def test_g10_kpi_feed(self, client, auth_token):
        tech_id = "TECH-KPI-FEED"
        # 데이터 먼저 넣기
        client.post(
            "/g10/kpi",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"tech_id": tech_id, "kpi_key": "new_customers", "value": 5},
        )
        r = client.get(
            f"/g10/kpi/{tech_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "latest_kpis" in body
        assert "events" in body
        assert body["event_count"] >= 1

    def test_g10_assess_with_kpi_store(self, client, auth_token):
        tech_id = "TECH-G10-ASSESS"
        # KPI batch 먼저 기록
        client.post(
            "/g10/kpi/batch",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"tech_id": tech_id, "actuals": {"revenue_usd": 500000, "new_customers": 6}},
        )
        r = client.post(
            "/g10/assess",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"tech_id": tech_id, "input_data": {"tech_name": "테스트기술"}},
        )
        assert r.status_code == 200
        body = r.json()
        assert "result" in body
        assert body["result"]["score"] >= 0

    # ── analyze-chain ───────────────────────────────────────
    def test_analyze_chain_minimal(self, client, auth_token):
        r = client.post(
            "/ip/analyze-chain",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"patent_id": "KR10-2021-0123456", "tech_id": "CHAIN-TEST", "scope": "basic"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "chain" in body
        assert "step1_patent_fetch" in body["chain"]
        assert "step2_pcml" in body["chain"]
        assert "step3_scr" in body["chain"]
        assert body["overall_gate"] in ("G1", "G2", "G3", "G4")
        assert "recommended_reports" in body

    # ── G5 Unit Economics ───────────────────────────────────
    def test_g5_unit_economics_in_output(self):
        from agents.g5_bm_designer import BMDesigner
        agent = BMDesigner()
        result = agent.assess({
            "tech_name": "스마트팜 AI",
            "value_proposition": "수확 7일 전 정확도 MAPE 17.8% 예측으로 폐기 손실 30% 절감",
            "revenue_model": ["saas"],
            "customer_segments": ["온실농가"],
            "channels": ["직접영업"],
            "gtm_target_market": "국내 온실 농가",
            "gtm_timeline_months": 12,
            "cac_usd": 2000,
            "ltv_usd": 10000,
            "gross_margin_pct": 70,
        })
        out = result.output_doc
        assert "unit_economics" in out
        ue = out["unit_economics"]
        assert ue["ltv_cac_ratio"] == 5.0
        assert ue["grades"]["ltv_cac"] == "Excellent"

    def test_g5_competitive_map_in_output(self):
        from agents.g5_bm_designer import BMDesigner
        agent = BMDesigner()
        result = agent.assess({
            "value_proposition": "정확한 수확 예측으로 공급 계획 최적화",
            "revenue_model": ["saas"],
            "customer_segments": ["농가"],
            "channels": ["온라인"],
            "gtm_target_market": "국내",
            "gtm_timeline_months": 12,
            "competitors": [
                {"name": "A사", "strength": "브랜드", "weakness": "고가", "market_share_pct": 40}
            ],
            "competitive_position": "niche",
            "tam_usd": 1_000_000_000,
        })
        out = result.output_doc
        assert "competitive_landscape" in out
        cl = out["competitive_landscape"]
        assert cl["position_label"] != ""
        assert cl["market_sizing"]["tam_usd"] == 1_000_000_000

    # ── G7 PoC 플랫폼 카탈로그 ─────────────────────────────
    def test_g7_poc_platform_recommendations(self):
        from agents.g7_poc_manager import PoCManager
        agent = PoCManager()
        result = agent.assess({
            "tech_name": "스마트팜 AI",
            "poc_objectives": ["MAPE < 20%"],
            "poc_kpis": [{"name": "MAPE", "target": 20, "actual": 17}],
            "customer_feedback": [{"sentiment": "positive"}],
            "risk_mitigations": ["데이터 백업"],
            "tech_type": "agritech",
            "target_regions": ["KR", "EU"],
            "trl": 5,
        })
        out = result.output_doc
        assert "poc_platform_recommendations" in out
        recs = out["poc_platform_recommendations"]
        assert len(recs["matched_platforms"]) >= 1
        assert recs["matched_platforms"][0]["funding_available"] is not None

    # ── G8 공급망 자동보강 ──────────────────────────────────
    def test_g8_supply_chain_enrichment(self):
        from agents.g8_mrl_arl_assessor import MRLARLAssessor
        agent = MRLARLAssessor()
        result = agent.assess({
            "trl": 7,
            "manufacturing_process_defined": True,
            "target_cost_usd": 100,
            "unit_cost_usd": 120,
            "certifications_required": [],
            "certifications_obtained": [],
            "market_interview_count": 30,
            "market_tam_validated": True,
            "customer_loi_count": 2,
            "customer_poc_count": 3,
            "economic_break_even_modeled": True,
            "economic_unit_economics_validated": True,
            "economic_pilot_revenue_usd": 80000,
            # 공급망 실데이터 자동 보강
            "auto_supply_chain_data": {
                "source": "UN Comtrade",
                "top_exporters": ["KR", "CN", "DE", "JP"],
                "concentration_hhi": 0.20,
                "total_trade_value_usd": 500_000_000,
            },
        })
        out = result.output_doc
        sc_info = out.get("triple_maturity_assessment", {})
        # supply_chain 보강 후 ARL ecosystem 개선 확인
        assert out.get("arl_assessment", {}).get("arl_level", 0) >= 4


class TestDeliverables:
    """사업화 필수 산출물 3종 — G5 로드맵·LoI·SMK 파이프라인"""

    @pytest.fixture(autouse=True)
    def _client(self, client, auth_token):
        self.client = client
        self.H = {"Authorization": f"Bearer {auth_token}"}

    def test_g5_roadmap_phases_and_funding(self):
        """G5 사업화 로드맵: Phase 3개 + 자금조달 계획 포함"""
        r = self.client.post("/g5/roadmap", headers=self.H, json={
            "tech_id": "DELIV-CR",
            "input_data": {
                "tech_name": "KAASA SmartOS",
                "current_trl": 4, "target_trl": 9,
                "tam_usd": 500_000_000, "som_usd": 10_000_000,
                "loi_count": 2, "poc_requests": 1,
                "revenue_model": ["saas", "license"],
                "team_size": 4, "industry_sector": "agtech",
                "target_market": "global",
            },
        })
        assert r.status_code == 200, r.text
        body = r.json()
        rm = body["roadmap"]
        assert rm["document_type"] == "사업화 로드맵 (Commercialization Roadmap)"
        assert len(rm["phases"]) == 3, "TRL 4→9: Phase 1+2+3 필요"
        assert len(rm["funding_plan"]) >= 3
        kpis = rm["kpi_targets"]
        assert kpis["year1"]["revenue_krw"] > 0
        assert kpis["year3"]["revenue_krw"] > kpis["year1"]["revenue_krw"]
        programs = [p["program"] for p in rm["government_programs"]]
        assert "TIPS" in programs
        assert "SBIR Phase I (미국)" in programs  # target_market=global

    def test_g4_loi_template_auto_generated(self):
        """G4 LoI: loi_count>=1 시 도입의향서 표준 양식 자동 생성"""
        r = self.client.post("/g4/loi-template", headers=self.H, json={
            "tech_id": "DELIV-LOI",
            "input_data": {
                "tech_name": "KAASA SmartOS",
                "tech_org": "(주)카사",
                "loi_count": 2,
                "poc_requests": 1,
                "interviews": [
                    {"customer_type": "온실 농가", "pain_point": "수동 제어 비효율",
                     "willingness_to_pay": 3000, "urgency_1to5": 4,
                     "jtbd_functional": "자동 환경 제어"},
                ] * 5,
            },
        })
        assert r.status_code == 200, r.text
        t = r.json()["loi_template"]
        assert t["document_type"] == "도입의향서 (Letter of Intent)"
        assert t["technology_overview"]["tech_name"] == "KAASA SmartOS"
        assert len(t["intent_clauses"]) >= 1
        assert t["commercial_intent"]["annual_budget_usd"] > 0
        assert "signature_block" in t
        assert len(t["usage_notes"]) >= 3

    def test_g4_loi_template_requires_loi_count(self):
        """loi_count=0, poc_requests=0이면 422 반환"""
        r = self.client.post("/g4/loi-template", headers=self.H, json={
            "tech_id": "DELIV-LOI-FAIL",
            "input_data": {"tech_name": "테스트", "loi_count": 0, "poc_requests": 0},
        })
        assert r.status_code == 422

    def test_smk_from_pipeline_integrates_g3_g4_g5(self):
        """SMK 파이프라인: G3+G4+G5 output 통합 SMK 생성"""
        r = self.client.post("/service/smk-from-pipeline", headers=self.H, json={
            "tech_id": "DELIV-SMK",
            "input_data": {
                "tech_name": "KAASA SmartOS",
                "industry_sector": "agtech",
                "value_proposition": "AI 기반 온실 자동화로 수확량 30% 향상",
                "revenue_model": "saas",
                "price_point_usd": 500,
                "g4_loi_count": 3,
                "g3_output": {
                    "market_sizing": {"tam_usd": 500_000_000, "sam_usd": 50_000_000, "cagr_pct": 18},
                    "industry": "agtech",
                },
                "g5_output": {
                    "business_model_canvas": {
                        "value_proposition": "AI 온실 자동화",
                        "revenue_streams": {"saas": "SaaS 구독"},
                    },
                    "competitive_landscape": {"position": "niche"},
                    "gtm_strategy": {"beachhead_market": "국내 딸기 농가"},
                },
            },
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["stage"] == "SMK"
        smk = body["smk"]
        assert smk.get("document_type") or smk.get("smk_summary")

    def test_g5_full_assess_auto_triggers_roadmap(self):
        """G5 /g5/assess: Go 게이트 달성 시 roadmap + smk 자동 첨부"""
        r = self.client.post("/g5/assess", headers=self.H, json={
            "tech_id": "DELIV-G5FULL",
            "input_data": {
                "tech_name": "KAASA SmartOS",
                "current_trl": 6, "target_trl": 9,
                "customer_segments": ["온실 농가", "스마트팜 사업자"],
                "value_proposition": "AI 온실 자동화 — 수확량 30% 향상",
                "channels": ["직판", "KOTRA"],
                "revenue_model": ["saas", "license"],
                "cost_structure": {"R&D": 40, "영업": 30, "운영": 30},
                "key_partners": ["농진청", "KAASA"],
                "gtm_target_market": "국내 온실 농가",
                "gtm_timeline_months": 12,
                "cac_usd": 2_000, "ltv_usd": 14_000,
                "arpu_usd": 500, "churn_rate_pct": 3.0,
                "gross_margin_pct": 75, "ndr_pct": 110,
                "tam_usd": 500_000_000, "sam_usd": 50_000_000, "som_usd": 10_000_000,
                "loi_count": 3, "poc_requests": 2,
                "team_size": 5, "industry_sector": "agtech",
                "competitors": [
                    {"name": "Priva", "strength": "글로벌", "weakness": "고가", "market_share_pct": 30}
                ],
                "competitive_position": "niche",
            },
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["gate"] == "Go", f"score={body['score']} gate={body['gate']}"
        out = body["output"]
        assert "commercialization_roadmap" in out, "G5 Go시 로드맵 자동 첨부 필요"
        assert "smk" in out, "G5 Go시 SMK 자동 첨부 필요"
        cr = out["commercialization_roadmap"]
        assert cr["trl_progression"]["current"] == 6
        assert len(cr["phases"]) >= 2
