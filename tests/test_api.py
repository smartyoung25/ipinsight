"""API 전체 엔드포인트 통합 테스트
실행: pytest tests/ -v
"""
from __future__ import annotations
import time
import pytest


# ══════════════════════════════════════════════════════════════
# 1. 공개 엔드포인트 (인증 불필요)
# ══════════════════════════════════════════════════════════════

class TestPublicEndpoints:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "version" in body
        assert "connectors" in body

    def test_health_has_all_connector_flags(self, client):
        body = client.get("/health").json()
        for key in ("epo_ops", "fda", "anthropic", "ntis", "slack"):
            assert key in body["connectors"]

    def test_stages_list(self, client):
        r = client.get("/stages")
        assert r.status_code == 200
        stages = r.json()["stages"]
        assert len(stages) == 11  # G0~G10
        ids = [s["stage_id"] for s in stages]
        assert "G0" in ids and "G10" in ids

    def test_demo_sample_input(self, client):
        r = client.get("/demo/sample-input")
        assert r.status_code == 200
        body = r.json()
        assert "tech_id" in body
        assert "stage_inputs" in body

    def test_ip_stages(self, client):
        r = client.get("/ip/stages")
        assert r.status_code == 200
        phases = r.json()["ip_lifecycle_phases"]
        assert len(phases) == 4

    def test_funding_sequence(self, client):
        r = client.get("/funding/sequence", params={"trl_current": 3, "trl_target": 7, "country": "KOR"})
        assert r.status_code == 200

    def test_execution_stages(self, client):
        r = client.get("/execution/stages")
        assert r.status_code == 200

    def test_gap_stages(self, client):
        r = client.get("/gap/stages")
        assert r.status_code == 200

    def test_service_stages(self, client):
        r = client.get("/service/stages")
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════
# 2. 인증 — /auth/token
# ══════════════════════════════════════════════════════════════

class TestAuth:
    def test_login_success(self, client):
        r = client.post("/auth/token", json={"username": "admin", "password": "admin1234"})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    def test_login_wrong_password(self, client):
        r = client.post("/auth/token", json={"username": "admin", "password": "wrong_pw"})
        assert r.status_code == 401

    def test_login_unknown_user(self, client):
        r = client.post("/auth/token", json={"username": "no_such_user", "password": "x"})
        assert r.status_code == 401

    def test_login_response_structure(self, client):
        r = client.post("/auth/token", json={"username": "admin", "password": "admin1234"})
        body = r.json()
        # JWT 3파트 구조 확인
        if "access_token" in body:
            parts = body["access_token"].split(".")
            assert len(parts) == 3


# ══════════════════════════════════════════════════════════════
# 3. 보호 엔드포인트 — 토큰 필요 (개발 모드에서 자동 통과)
# ══════════════════════════════════════════════════════════════

class TestProtectedEndpoints:
    def test_metrics_accessible(self, client, auth_headers):
        r = client.get("/metrics", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "requests" in body
        assert "errors" in body
        assert "avg_ms" in body

    def test_metrics_invalid_token(self, client):
        """JWT_SECRET_KEY 설정 환경에서는 401. 개발 모드에서는 200."""
        import os
        if os.environ.get("JWT_SECRET_KEY"):
            r = client.get("/metrics", headers={"Authorization": "Bearer invalid.token.here"})
            assert r.status_code == 401
        else:
            pass  # 개발 모드 — 스킵

    def test_stage_0_run(self, client, auth_headers):
        """G0 단계 실행 — 최소 입력"""
        r = client.post(
            "/stage/0",
            json={
                "tech_id": "TEST-001",
                "input_data": {
                    "tech_name": "테스트 기술",
                    "owner": "테스터",
                    "tech_description": "단위 테스트용 기술 설명",
                    "problem_statement": "문제 정의",
                    "field_keywords": ["AI", "테스트"],
                    "ipc_codes": ["G06N"],
                    "existing_solutions": "없음",
                },
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert "tech_id" in body
        assert "result" in body

    def test_stage_invalid_num(self, client, auth_headers):
        r = client.post(
            "/stage/99",
            json={"tech_id": "T", "input_data": {}},
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_funding_match(self, client, auth_headers):
        r = client.post(
            "/funding/match",
            json={"trl": 4, "country": "KOR", "sector": "AgriTech", "stage_id": "G3"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert "matched_programs" in body


# ══════════════════════════════════════════════════════════════
# 4. 비동기 Job 큐
# ══════════════════════════════════════════════════════════════

class TestAsyncJobs:
    def test_submit_job(self, client, auth_headers):
        r = client.post(
            "/analyze/async",
            json={"tech_id": "ASYNC-001", "input_data": {}},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert "job_id" in body
        assert body["status"] in ("queued", "running", "completed", "failed")

    def test_job_polling(self, client, auth_headers):
        """Job 제출 → 5초 후 완료 여부 확인"""
        sub = client.post(
            "/analyze/async",
            json={"tech_id": "ASYNC-002", "input_data": {}},
            headers=auth_headers,
        )
        assert sub.status_code == 200
        job_id = sub.json()["job_id"]

        time.sleep(5)

        poll = client.get(f"/jobs/{job_id}", headers=auth_headers)
        assert poll.status_code == 200
        body = poll.json()
        assert body["job_id"] == job_id
        assert body["status"] in ("completed", "failed", "running")

    def test_job_not_found(self, client, auth_headers):
        r = client.get("/jobs/nonexistent-job-id", headers=auth_headers)
        assert r.status_code == 404


# ══════════════════════════════════════════════════════════════
# 5. Phase 2 타입 스키마 엔드포인트
# ══════════════════════════════════════════════════════════════

class TestTypedSchemaEndpoints:
    def test_valuation_dcf(self, client, auth_headers):
        r = client.post(
            "/valuation/dcf",
            json={
                "tech_id": "VAL-001",
                "revenue_forecast": {"2025": 500000, "2026": 1000000, "2027": 2000000},
                "discount_rate": 0.15,
                "royalty_rate": 0.05,
                "method": "dcf",
            },
            headers=auth_headers,
        )
        assert r.status_code == 200

    def test_gap_analyze(self, client, auth_headers):
        r = client.post(
            "/gap/analyze",
            json={
                "tech_id": "GAP-001",
                "tech_name": "스마트팜 AI",
                "industry_sector": "AgriTech",
                "trl": 4,
            },
            headers=auth_headers,
        )
        assert r.status_code == 200

    def test_execution_strategy(self, client, auth_headers):
        r = client.post(
            "/execution/strategy",
            json={
                "tech_id": "EXEC-001",
                "tech_name": "스마트팜 AI",
                "business_model": "B2B",
            },
            headers=auth_headers,
        )
        assert r.status_code == 200

    def test_regulation_roadmap(self, client, auth_headers):
        r = client.post(
            "/regulation/roadmap",
            json={
                "tech_id": "REG-001",
                "product_type": "소프트웨어",
                "target_countries": ["KR", "US"],
                "fda_510k": False,
            },
            headers=auth_headers,
        )
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════
# 6. IP / Gap / Service 에이전트 엔드포인트
# ══════════════════════════════════════════════════════════════

class TestAgentEndpoints:
    COMMON = {"tech_id": "AGT-001", "input_data": {"tech_name": "테스트 기술", "trl": 3}}

    def test_ip_idf(self, client, auth_headers):
        r = client.post("/ip/idf", json=self.COMMON, headers=auth_headers)
        assert r.status_code == 200
        assert "result" in r.json()

    def test_ip_patentability(self, client, auth_headers):
        r = client.post("/ip/patentability", json=self.COMMON, headers=auth_headers)
        assert r.status_code == 200

    def test_execution_team(self, client, auth_headers):
        r = client.post("/execution/team", json=self.COMMON, headers=auth_headers)
        assert r.status_code == 200

    def test_execution_unit_economics(self, client, auth_headers):
        r = client.post("/execution/unit-economics", json=self.COMMON, headers=auth_headers)
        assert r.status_code == 200

    def test_gap_ir_deck(self, client, auth_headers):
        r = client.post("/gap/ir-deck", json=self.COMMON, headers=auth_headers)
        assert r.status_code == 200

    def test_gap_esg_impact(self, client, auth_headers):
        r = client.post("/gap/esg-impact", json=self.COMMON, headers=auth_headers)
        assert r.status_code == 200

    def test_gap_ecosystem_match(self, client, auth_headers):
        r = client.post("/gap/ecosystem-match", json=self.COMMON, headers=auth_headers)
        assert r.status_code == 200

    def test_service_demand_survey(self, client, auth_headers):
        r = client.post("/service/demand-survey", json=self.COMMON, headers=auth_headers)
        assert r.status_code == 200

    def test_service_smk(self, client, auth_headers):
        r = client.post("/service/smk", json=self.COMMON, headers=auth_headers)
        assert r.status_code == 200

    def test_service_roadmap(self, client, auth_headers):
        r = client.post(
            "/service/roadmap",
            json={
                "tech_id": "RDM-001",
                "input_data": {"tech_name": "AI 기술", "current_trl": 3, "target_trl": 7},
            },
            headers=auth_headers,
        )
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════
# 7. PCML 청구항 구조 분석
# ══════════════════════════════════════════════════════════════

SAMPLE_PATENT_TEXT = """
특허 제10-2270171호
발명의 명칭: 스마트팜 환경 제어 시스템 및 방법

청구항 1.
온실 내 환경을 제어하는 시스템으로서,
온도 센서와 습도 센서를 포함하는 센서부;
상기 센서부로부터 환경 데이터를 수신하는 제어부; 및
상기 제어부의 제어 신호에 따라 온실 환경을 조절하는 구동부를 포함하는,
스마트팜 환경 제어 시스템.

청구항 2.
제1항에 있어서,
상기 제어부는 인공지능 모델을 이용하여 최적 환경 파라미터를 산출하는,
스마트팜 환경 제어 시스템.

청구항 3.
청구항 1에 기재된 스마트팜 환경 제어 시스템을 이용한 방법으로서,
센서부가 환경 데이터를 측정하는 단계;
제어부가 상기 데이터를 분석하는 단계; 및
구동부가 환경을 조절하는 단계를 포함하는, 방법.
"""


class TestPCMLEndpoint:
    """PCML v2.0 — New PCML v2.0 6계층 구조 검증"""

    def test_pcml_v2_version_field(self, client, auth_headers):
        """v2.0 버전 필드 확인"""
        r = client.post(
            "/ip/pcml",
            json={"tech_id": "KR10-2270171", "patent_text": SAMPLE_PATENT_TEXT},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["pcml_version"] == "2.0"
        assert body["stage"] == "G1.5-PCML"
        assert body["gate"] in ("Go", "Hold", "Kill")

    def test_pcml_six_layers_present(self, client, auth_headers):
        """6계층 최상위 키 존재 확인"""
        r = client.post(
            "/ip/pcml",
            json={"tech_id": "PCML-LAYERS-001", "patent_text": SAMPLE_PATENT_TEXT},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        for key in ("patent_layer", "claim_graph_layer", "support_layer",
                    "metadata_layer", "legal_family_layer", "evidence_layer"):
            assert key in body, f"계층 키 누락: {key}"

    def test_pcml_patent_layer_fields(self, client, auth_headers):
        """L1 Patent Layer 필수 필드 검증"""
        r = client.post(
            "/ip/pcml",
            json={"tech_id": "KR10-2270171", "patent_id": "KR10-2270171",
                  "patent_text": SAMPLE_PATENT_TEXT},
            headers=auth_headers,
        )
        assert r.status_code == 200
        pl = r.json()["patent_layer"]
        for field in ("patent_id", "jurisdiction", "language", "input_mode"):
            assert field in pl, f"patent_layer 필드 누락: {field}"

    def test_pcml_claim_graph_layer(self, client, auth_headers):
        """L2 Claim Graph Layer — claims/nodes/links/attributes 존재"""
        r = client.post(
            "/ip/pcml",
            json={"tech_id": "PCML-CGL-001", "patent_text": SAMPLE_PATENT_TEXT},
            headers=auth_headers,
        )
        assert r.status_code == 200
        cgl = r.json()["claim_graph_layer"]
        for key in ("claims", "nodes", "links", "attributes",
                    "dependency_tree", "essential_requirement_set"):
            assert key in cgl, f"claim_graph_layer 키 누락: {key}"
        assert isinstance(cgl["claims"], list)
        assert isinstance(cgl["nodes"], list)

    def test_pcml_node_element_class_valid(self, client, auth_headers):
        """Node element_class 허용값 검증 (Core|Supporting|Peripheral)"""
        r = client.post(
            "/ip/pcml",
            json={"tech_id": "PCML-NODE-001", "patent_text": SAMPLE_PATENT_TEXT},
            headers=auth_headers,
        )
        assert r.status_code == 200
        nodes = r.json()["claim_graph_layer"]["nodes"]
        valid_classes = {"Core", "Supporting", "Peripheral"}
        for node in nodes:
            assert node.get("element_class") in valid_classes, \
                f"node {node.get('node_id')} element_class 비허용값: {node.get('element_class')}"

    def test_pcml_link_relation_type_valid(self, client, auth_headers):
        """Link relation_type 허용값 검증"""
        r = client.post(
            "/ip/pcml",
            json={"tech_id": "PCML-LINK-001", "patent_text": SAMPLE_PATENT_TEXT},
            headers=auth_headers,
        )
        assert r.status_code == 200
        valid_relations = {
            "includes", "has", "performs", "inputs", "receives", "outputs",
            "transmits", "controls", "based_on", "stores", "retrieves",
            "connected_to", "depends_on",
        }
        links = r.json()["claim_graph_layer"]["links"]
        for link in links:
            assert link.get("relation_type") in valid_relations, \
                f"link {link.get('link_id')} 비표준 relation_type: {link.get('relation_type')}"

    def test_pcml_shared_variables(self, client, auth_headers):
        """Shared Variables 9종 필드 존재 확인"""
        r = client.post(
            "/ip/pcml",
            json={"tech_id": "PCML-SV-001", "patent_text": SAMPLE_PATENT_TEXT},
            headers=auth_headers,
        )
        assert r.status_code == 200
        sv = r.json()["shared_variables"]
        for field in ("self_core_nodes", "self_core_links", "support_coverage",
                      "explicit_support_ratio", "black_box_core_ratio",
                      "claim_clarity_penalty"):
            assert field in sv, f"shared_variables 필드 누락: {field}"

    def test_pcml_governance_release_status(self, client, auth_headers):
        """Governance release_status 허용값 검증"""
        r = client.post(
            "/ip/pcml",
            json={"tech_id": "PCML-GOV-001", "patent_text": SAMPLE_PATENT_TEXT},
            headers=auth_headers,
        )
        assert r.status_code == 200
        gov = r.json()["governance"]
        assert gov.get("release_status") in ("releasable", "internal_only", "blocked")
        assert "structure_version" in gov
        assert "status_version" in gov
        assert "evidence_version" in gov

    def test_pcml_qc_v2_fields(self, client, auth_headers):
        """QC v2.0 필드 구조 검증"""
        r = client.post(
            "/ip/pcml",
            json={"tech_id": "PCML-QCV2-001", "patent_text": SAMPLE_PATENT_TEXT},
            headers=auth_headers,
        )
        assert r.status_code == 200
        qc = r.json()["qc"]
        assert "fail_count" in qc
        assert "warn_count" in qc
        assert "qc_grade" in qc
        assert qc["qc_grade"] in ("A", "B", "C", "D")
        assert "qc_confidence" in qc
        assert 0 <= qc["qc_confidence"] <= 100
        assert "qc_integrity_for_kpi" in qc

    def test_pcml_kpi_inputs_extracted(self, client, auth_headers):
        """기술사업화 KPI 연계 입력값 자동 추출"""
        r = client.post(
            "/ip/pcml",
            json={"tech_id": "PCML-KPI-001", "patent_text": SAMPLE_PATENT_TEXT},
            headers=auth_headers,
        )
        assert r.status_code == 200
        kpi = r.json()["kpi_inputs"]
        assert "ip_strength_score" in kpi
        assert "core_node_count" in kpi
        assert "qc_confidence" in kpi
        assert "release_status" in kpi
        assert 0 <= kpi["ip_strength_score"] <= 100

    def test_pcml_input_mode_claim_only(self, client, auth_headers):
        """input_mode=claim_only 시 폴백 정상 동작"""
        r = client.post(
            "/ip/pcml",
            json={"tech_id": "MINIMAL-001", "input_mode": "claim_only"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["patent_layer"]["input_mode"] == "claim_only"

    def test_pcml_missing_tech_id(self, client, auth_headers):
        """tech_id 누락 시 422"""
        r = client.post("/ip/pcml", json={}, headers=auth_headers)
        assert r.status_code == 422


# ══════════════════════════════════════════════════════════════
# 8. 에러 응답 형식 표준화
# ══════════════════════════════════════════════════════════════

class TestErrorResponseFormat:  # noqa: F811
    def test_404_has_standard_format(self, client, auth_headers):
        r = client.get("/result/nonexistent_tech_9999", headers=auth_headers)
        assert r.status_code == 404
        body = r.json()
        assert "code" in body
        assert "message" in body

    def test_400_stage_out_of_range(self, client, auth_headers):
        r = client.post("/stage/99", json={"tech_id": "T", "input_data": {}}, headers=auth_headers)
        assert r.status_code == 400
        body = r.json()
        assert "code" in body or "detail" in body  # FastAPI 기본 또는 표준 ErrorResponse

    def test_422_missing_required_field(self, client, auth_headers):
        r = client.post("/valuation/dcf", json={}, headers=auth_headers)
        assert r.status_code == 422
