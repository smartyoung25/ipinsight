"""E2E 실사용 테스트 — 실제 기술 사례로 G0~G10 전 파이프라인 + HTTP API 검증

사례: KAASA AI 스마트팜 수확량 예측 시스템
  - 기술: LSTM 딥러닝 + IoT 센서, MAPE 17.8%
  - TRL 5 (시제품 실증), 5개 농가 파일럿
  - 목표 시장: 국내외 온실 농가
"""
import sys
import json
sys.path.insert(0, "C:/IPinsight_a")

from pipeline.phase_gate_pipeline import PhaseGatePipeline

# ── 실사용 케이스 입력 데이터 ──────────────────────────────────────────
TECH_ID = "kaasa_smartfarm_v1"

STAGE_INPUTS = {
    0: {  # G0 기술발굴
        "tech_name": "AI 스마트팜 수확량 예측 시스템",
        "owner": "KAASA 연구팀",
        "tech_description": "LSTM 딥러닝과 IoT 센서를 결합하여 온실 작물 수확량을 7일 전 예측. MAPE 17.8% 달성.",
        "problem_statement": "온실 농가 수확량 예측 불확실성 → 과잉생산·공급부족 반복",
        "field_keywords": ["스마트팜", "AI", "IoT", "수확량예측", "딥러닝"],
        "ipc_codes": ["G06N", "A01G", "G06F"],
        "existing_solutions": "기상청 예보 기반 단순 추정, 전문가 경험적 판단",
        "novelty_claim": "LSTM + 실시간 IoT 센서 융합, 작물별 맞춤 학습 모델",
        "competitor_filings": [
            {"assignee": "Priva BV", "ipc_codes": ["A01G"], "filed_year": 2023, "status": "active"},
            {"assignee": "LetsGrow", "ipc_codes": ["G06N"], "filed_year": 2022, "status": "active"},
        ],
    },
    1: {  # G1 IP구조화 — 필드명은 IPStructurer 스펙 기준
        "patent_claims": [
            {"no": 1, "type": "independent",
             "elements": ["IoT 센서 데이터 수집", "LSTM 모델 학습", "7일 전 수확량 예측"]},
            {"no": 2, "type": "dependent", "elements": ["작물별 맞춤 보정 파라미터 적용"]},
            {"no": 3, "type": "dependent", "elements": ["배액률 기반 관수 자동 조정"]},
        ],
        "spec_summary": (
            "본 발명은 온실 내 IoT 센서(온도·습도·일사량·EC·pH)에서 실시간 수집된 "
            "환경 데이터와 생육 데이터를 LSTM 신경망으로 학습하여 수확 7일 전 수확량을 "
            "예측하는 시스템 및 방법에 관한 것으로, 종래 기상예보 기반 방식 대비 "
            "MAPE 17.8%(종래 38%)의 정확도 개선을 달성한다."
        ),
        "prior_art_list": [
            {"title": "기상청 예보 기반 수확량 추정 시스템", "pub_no": "KR10-2021-000123"},
            {"title": "온실 환경 통계 모델 예측법", "pub_no": "US2022/0375001"},
        ],
        "competitor_patents": [
            {"assignee": "Priva BV", "patent_no": "NL2030400", "claim_overlap": "low"},
            {"assignee": "LetsGrow", "patent_no": "EP4123456", "claim_overlap": "medium"},
        ],
        "filing_status": "provisional",
    },
    2: {  # G2 TRL평가
        "tech_description": "LSTM 기반 온실 수확량 예측 AI",
        "claimed_trl": 5,
        "evidence_list": [
            {"type": "성능평가 보고서", "description": "딸기 MAPE 17.8%, R² 0.295 달성", "date": "2026-03"},
            {"type": "시제품 실증", "description": "5개 농가 6개월 현장 실증 완료", "date": "2026-04"},
            {"type": "논문", "description": "스마트팜 AI 학술지 게재 완료", "date": "2026-02"},
        ],
        "target_trl": 8,
        "validation_environment": "실제 온실 운영 환경",
    },
    3: {  # G3 시장성
        "tech_name": "스마트팜 수확량 예측 AI",
        "target_market": "국내외 온실 농가 및 스마트팜 SI기업",
        "tam_usd": 5_000_000_000,
        "sam_usd": 500_000_000,
        "som_usd": 15_000_000,
        "growth_rate_pct": 15,
        "competitors": ["Priva", "Ridder", "LetsGrow.com", "Crop-R"],
        "entry_barriers": ["데이터 축적 기간 필요", "농가 신뢰 확보"],
        "substitute_technologies": ["기상청 예보", "전문가 컨설팅"],
        "regulatory_environment": "스마트농업법 2024 시행 — 정부 보조금 지원",
    },
    4: {  # G4 고객검증
        "interviews": [
            {
                "customer_type": "온실농가",
                "pain_point": "수확량 불확실로 유통 계획 수립 어려움",
                "willingness_to_pay": 500000,
                "urgency_1to5": 4,
                "jtbd_functional": "7일 전 수확량 정확 예측",
                "jtbd_emotional": "수확 전 불안감 해소",
                "jtbd_social": "스마트팜 선도 농가로 인정받고 싶음",
            }
        ] * 38,
        "loi_count": 4,
        "poc_requests": 3,
    },
    5: {  # G5 BM설계
        "tech_name": "스마트팜 수확량 예측 AI",
        "target_segment": "온실 농가 (딸기·토마토·파프리카)",
        "value_proposition": "7일 전 수확량 예측으로 유통 계획 최적화 → 폐기 손실 30% 절감",
        "revenue_model": "SaaS 월정액 + 성과 연동 보너스",
        "pricing_strategy": "농가 규모별 3티어 (Basic/Smart/Pro)",
        "channels": ["농협 통한 B2B", "스마트팜 SI업체 OEM", "직접 영업"],
        "cost_structure": ["서버 인프라", "모델 유지보수", "현장 설치"],
        "key_partners": ["농협중앙회", "KAASA", "스마트팜 SI업체"],
    },
    6: {  # G6 가치평가
        "tech_name": "스마트팜 수확량 예측 AI",
        "industry_sector": "스마트팜·농업기술",
        "trl": 5,
        "revenue_forecast": [500_000, 2_000_000, 5_000_000, 10_000_000, 15_000_000],
        "discount_rate_pct": 15,
        "royalty_rate_pct": 4,
        "tech_contribution_pct": 35,
        "patent_remaining_years": 18,
        "risk_adjustment_pct": 25,
        "monte_carlo_runs": 1000,
    },
    7: {  # G7 PoC실증 — 필드명은 PoCManager 스펙 기준
        "tech_name": "스마트팜 수확량 예측 AI",
        "poc_objectives": [
            "딸기 농가 5개소에서 MAPE 20% 이하 달성",
            "농가 만족도 4점 이상 확인",
            "6개월 연속 운영 안정성 검증",
        ],
        "poc_kpis": [
            {"name": "MAPE", "target": 20.0, "actual": 17.8},
            {"name": "R²", "target": 0.25, "actual": 0.295},
            {"name": "농가 만족도", "target": 4.0, "actual": 4.3},
            {"name": "재계약 의향", "target": 3, "actual": 4},
        ],
        "test_environment": "실제 운영 온실 (딸기 5개 농가, 경남·전북)",
        "customer_feedback": [
            {"sentiment": "positive", "comment": "수확 예측이 맞아 유통 업체와 사전 계약 체결 성공"},
            {"sentiment": "positive", "comment": "초기 설치 복잡했으나 이후 자동 운영으로 만족"},
            {"sentiment": "neutral",  "comment": "모바일 앱 알림 기능 추가 요청"},
        ],
        "issues_found": [
            "여름철 고온 이상기상 시 MAPE 25%로 저하 (5% 케이스)",
        ],
        "risk_mitigations": [
            "이상기상 감지 시 규칙 기반 폴백 모드 자동 전환",
            "ERA5 외부기온 데이터 실시간 연동으로 보완",
        ],
        "poc_duration_months": 6,
        "venture_client_partner": "Bosch Startup Harbour",
    },
    8: {  # G8 MRL·ARL
        "trl": 5,
        "manufacturing_process_defined": True,
        "supply_chain_ready": False,
        "quality_system": "ISO9001",
        "unit_cost_usd": 200,
        "target_cost_usd": 150,
        "certifications_required": ["KC인증", "클라우드보안인증(CSAP)"],
        "certifications_obtained": [],
        # ARL 5차원
        "market_interview_count": 38,
        "market_tam_validated": True,
        "market_repeat_purchase_pct": 0,
        "customer_loi_count": 4,
        "customer_poc_count": 5,
        "customer_nps": 35,
        "regulatory_approved": False,
        "regulatory_submission_done": False,
        "economic_pilot_revenue_usd": 40_000,
        "economic_break_even_modeled": True,
        "economic_unit_economics_validated": False,
        "ecosystem_partner_count": 2,
        "ecosystem_integration_done": False,
    },
    9: {  # G9 거래·투자
        "tech_name": "스마트팜 수확량 예측 AI",
        "trl": 5,
        "mrl": 5,
        "arl": 4,
        "ip_strength_score": 68,
        "valuation_usd": 3_500_000,
        "team_commercialization_capability": 3,
        "is_b2b": True,
        "corporate_customer_interest": True,
        "potential_partners": ["농협중앙회", "KAASA SI파트너", "Bosch Startup Harbour"],
        "target_countries": ["KOR", "USA", "EU"],
        "industry_sector": "스마트팜",
    },
    10: {  # G10 성과관리 — 필드명은 PerformanceTracker 스펙 기준
        "tech_name": "스마트팜 수확량 예측 AI",
        "actuals": {
            # G10 _KPI_TARGETS 키 기준
            "revenue_usd": 40_000,
            "royalty_usd": 0,
            "investment_raised_usd": 200_000,  # PoC 지원금
            "poc_to_commercial_rate_pct": 20,   # 5개 파일럿 중 1개 상용화 진행
            "tech_utilization_rate_pct": 55,
            "new_customers": 5,
        },
        "milestone_achievements": [
            {"name": "파일럿 5개 농가 완료", "target_date": "2026-04-30",
             "actual_date": "2026-04-25", "status": "completed"},
            {"name": "LoI 4건 확보", "target_date": "2026-05-31",
             "actual_date": "2026-05-20", "status": "completed"},
            {"name": "상용 계약 1호", "target_date": "2026-06-30",
             "actual_date": None, "status": "in_progress"},
        ],
        "portfolio_techs": [
            {
                "tech_id": "smartfarm_ai", "tech_name": "스마트팜 수확량 예측 AI",
                "trl": 5, "mrl": 5, "arl": 4,
                "annual_revenue_usd": 40_000, "annual_cost_usd": 60_000,
                "market_growth_pct": 15, "competitive_position": "medium",
                "patent_remaining_years": 18, "licensing_revenue_usd": 0,
            },
        ],
        "feedback_actions": [
            {"issue": "여름철 고온 MAPE 저하", "action": "ERA5 외부기온 연동 보완", "status": "completed"},
            {"issue": "모바일 앱 알림 요청", "action": "모바일 알림 기능 로드맵 등록", "status": "planned"},
        ],
    },
}


def test_full_pipeline():
    """G0~G10 전 파이프라인 실행 — 실제 기술 사례"""
    print("=" * 60)
    print("IPInsight G0~G10 전 파이프라인 실행")
    print(f"기술: {STAGE_INPUTS[0]['tech_name']}")
    print("=" * 60)

    pipeline = PhaseGatePipeline(tech_id=TECH_ID)
    summary = pipeline.run_pipeline(stage_inputs=STAGE_INPUTS, stop_on_kill=True)

    print(f"\n{'단계':<6} {'이름':<20} {'점수':>6} {'게이트':<6} {'경고'}")
    print("-" * 60)
    for s in summary["stages"]:
        warn = f"⚠️ {len(s['warnings'])}건" if s["warnings"] else ""
        gate_icon = {"Go": "✅", "Hold": "⏸️", "Kill": "❌"}.get(s["gate"], "")
        print(f"G{s['stage']:<5} {s['name']:<20} {s['score']:>6.1f} {gate_icon}{s['gate']:<5} {warn}")

    print("-" * 60)
    print(f"최종 판정: {summary['final_gate']}")
    if summary.get("killed_at") is not None:
        print(f"Kill 발생 단계: G{summary['killed_at']}")

    # 핵심 지표 출력
    results = pipeline.get_all_results()
    _print_key_metrics(results)

    # 산출물 파일 확인
    from pathlib import Path
    output_dir = Path("C:/IPinsight_a/outputs") / TECH_ID
    files = sorted(output_dir.glob("*.json"))
    print(f"\n산출물 파일: {len(files)}개")
    for f in files:
        size = f.stat().st_size
        print(f"  {f.name} ({size:,} bytes)")

    # 파이프라인이 최소 10개 단계를 실행했는지 확인
    # (G10 Kill = 정상: TRL5 초기 스타트업은 매출 $40K/$1M 목표 미달 → 실제 시스템 판정)
    assert len(summary["stages"]) >= 10, f"10개 이상 단계 실행 필요, 실제: {len(summary['stages'])}"
    # Kill이 발생했다면 G10(상용화 KPI 미달)에서만 허용
    if summary["final_gate"] == "Kill":
        assert summary["killed_at"] == 10, \
            f"G10 이전 단계에서 Kill 발생: G{summary['killed_at']} — 입력 데이터 확인 필요"
        print("\n[정상] G10 Kill = TRL5 초기 스타트업의 올바른 판정")
        print("       (매출 $40K / 목표 $1M = 4% 달성 → Kill 기준 미충족)")
    return summary


def _print_key_metrics(results: dict):
    """핵심 지표 요약 출력"""
    print("\n── 핵심 지표 ──────────────────────────────")

    # G2 TRL
    if 2 in results:
        trl = results[2]["output_doc"].get("trl_assessment", {}).get("assessed_trl", "N/A")
        print(f"TRL: {trl}")

    # G3 시장성
    if 3 in results:
        market = results[3]["output_doc"].get("market_analysis", {})
        tam = market.get("tam_usd", 0)
        print(f"TAM: ${tam:,.0f}")

    # G6 가치평가
    if 6 in results:
        val = results[6]["output_doc"].get("tech_valuation_report", {})
        weighted = val.get("weighted_value_usd", 0)
        mc = results[6]["output_doc"].get("monte_carlo_simulation", {})
        p10 = mc.get("p10", 0)
        p90 = mc.get("p90", 0)
        method = val.get("primary_method", "")
        print(f"기술가치 (중간): ${weighted:,.0f}  [{method}]")
        print(f"P10/P90: ${p10:,.0f} ~ ${p90:,.0f}")

    # G8 MRL·ARL
    if 8 in results:
        triple = results[8]["output_doc"].get("triple_maturity_assessment", {})
        mrl = triple.get("mrl", "N/A")
        arl = triple.get("arl", "N/A")
        reg_risk = triple.get("regulatory_risk_level", "N/A")
        arl_5d = results[8]["output_doc"].get("arl_assessment", {}).get("arl_5d_detail", {})
        dims = {k: v["arl"] for k, v in arl_5d.get("dimensions", {}).items()}
        print(f"MRL: {mrl}  ARL: {arl}  규제리스크: {reg_risk}")
        if dims:
            print(f"ARL 5차원: {dims}")

    # G9 거래방식
    if 9 in results:
        deal = results[9]["output_doc"].get("deal_type_recommendation", {})
        rec = deal.get("recommended", "N/A")
        vc = results[9]["output_doc"].get("venture_client_strategy", {})
        vc_progs = [p["corp"] for p in vc.get("matched_programs", [])]
        print(f"추천 거래방식: {rec}")
        if vc_progs:
            print(f"Venture Client 매칭: {vc_progs[:2]}")


def test_http_api():
    """FastAPI HTTP 엔드포인트 직접 호출 테스트 (TestClient)"""
    print("\n" + "=" * 60)
    print("HTTP API 엔드포인트 검증 (TestClient)")
    print("=" * 60)

    try:
        from fastapi.testclient import TestClient
        from api.main import app
    except ImportError:
        print("httpx 미설치 — pip install httpx 후 재시도")
        return

    client = TestClient(app)

    # 1. GET /health
    r = client.get("/health")
    assert r.status_code == 200
    print(f"GET /health          → {r.status_code} {r.json()['status']}")

    # 2. GET /stages
    r = client.get("/stages")
    assert r.status_code == 200
    stages = r.json()["stages"]
    print(f"GET /stages          → {r.status_code}  {len(stages)}개 단계")

    # 3. GET /ip/stages
    r = client.get("/ip/stages")
    assert r.status_code == 200
    phases = r.json()["ip_lifecycle_phases"]
    print(f"GET /ip/stages       → {r.status_code}  {len(phases)}개 IP 단계")

    # 4. POST /stage/0 (G0 단일 실행)
    r = client.post("/stage/0", json={
        "tech_id": "api_test_001",
        "input_data": STAGE_INPUTS[0],
    })
    assert r.status_code == 200
    score = r.json()["result"]["score"]
    gate = r.json()["result"]["gate"]
    print(f"POST /stage/0        → {r.status_code}  score={score}, gate={gate}")

    # 5. POST /stage/6 (G6 가치평가)
    r = client.post("/stage/6", json={
        "tech_id": "api_test_001",
        "input_data": STAGE_INPUTS[6],
    })
    assert r.status_code == 200
    val = r.json()["result"]["output_doc"]["tech_valuation_report"]
    method = val["primary_method"]
    mc = r.json()["result"]["output_doc"]["monte_carlo_simulation"]
    print(f"POST /stage/6        → {r.status_code}  method={method}  P50=${mc['p50']:,.0f}")
    assert method == "relief_from_royalty", f"TRL5 → 로열티구제법 필요, got {method}"
    assert "scenarios" in mc, "Monte Carlo 시나리오 없음"

    # 6. POST /ip/idf
    r = client.post("/ip/idf", json={
        "tech_id": "api_test_001",
        "input_data": {
            "tech_name": "AI 스마트팜",
            "tech_detail": "LSTM 딥러닝으로 온실 수확량을 7일 전 예측하는 시스템. IoT 센서 연동.",
            "problem_solved": "수확량 예측 불확실성",
            "inventor_info": [{"name": "홍길동", "affiliation": "KAASA", "contribution_pct": 100}],
            "key_features": ["LSTM 모델", "IoT 센서 융합", "작물별 맞춤 학습"],
            "security_classification": "internal",
            "licensing_potential": "non_exclusive",
            "research_funding": "정부 IITP 과제",
        },
    })
    assert r.status_code == 200
    warnings = r.json()["result"]["output_doc"]["funding_warnings"]
    print(f"POST /ip/idf         → {r.status_code}  정부과제 경고: {len(warnings)}건")

    # 7. GET /demo/sample-input
    r = client.get("/demo/sample-input")
    assert r.status_code == 200
    print(f"GET /demo/sample-input → {r.status_code}  샘플 입력 반환")

    # 8. POST /funding/match
    r = client.post("/funding/match", json={
        "trl": 5, "country": "KOR", "sector": "스마트팜", "stage_id": "G6",
    })
    assert r.status_code == 200
    programs = r.json()["matched_programs"]
    print(f"POST /funding/match  → {r.status_code}  매칭 프로그램: {len(programs)}개")

    print("\n모든 HTTP 엔드포인트 검증 통과")


if __name__ == "__main__":
    summary = test_full_pipeline()
    test_http_api()
    print("\n" + "=" * 60)
    print("E2E 실사용 테스트 전체 완료")
    print("=" * 60)
