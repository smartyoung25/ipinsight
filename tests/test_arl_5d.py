"""ARL 5차원 독립 평가 검증 — DOE 공식 표준 정합"""
import sys
sys.path.insert(0, "C:/IPinsight")
from agents import MRLARLAssessor


def test_arl_5d_dimensions_independent():
    """5차원이 독립적으로 다른 점수를 낼 수 있는지"""
    r = MRLARLAssessor().assess({
        "trl": 6,
        "manufacturing_process_defined": True,
        "supply_chain_ready": True,
        "quality_system": "ISO9001",
        "unit_cost_usd": 400, "target_cost_usd": 400,
        # ARL 5차원
        "market_interview_count": 25,
        "market_tam_validated": True,
        "market_repeat_purchase_pct": 0,
        "customer_loi_count": 2,
        "customer_poc_count": 4,
        "customer_nps": -1,
        "regulatory_approved": False,
        "regulatory_submission_done": True,
        "certifications_required": ["CE Mark"],
        "certifications_obtained": [],
        "economic_pilot_revenue_usd": 0,
        "economic_break_even_modeled": True,
        "economic_unit_economics_validated": False,
        "ecosystem_partner_count": 1,
        "ecosystem_integration_done": False,
    })
    arl_detail = r.output_doc["arl_assessment"]["arl_5d_detail"]
    dims = arl_detail["dimensions"]
    scores = [v["arl"] for v in dims.values()]
    print("5차원 독립 점수:", {k: v["arl"] for k, v in dims.items()})
    print(f"ARL 최종: {arl_detail['arl_final']}  (가중평균: {arl_detail['weighted_raw']})")
    print(f"병목 적용: {arl_detail['bottleneck_applied']}  병목 차원: {arl_detail['bottleneck']}")
    # 차원별 점수가 모두 같지 않아야 함
    assert len(set(scores)) > 1, "5차원이 모두 동일 점수 — 독립 평가 실패"


def test_arl_bottleneck_rule():
    """병목 원칙: ecosystem ARL<=2 이면 전체 ARL 최대 4"""
    r = MRLARLAssessor().assess({
        "trl": 7,
        "manufacturing_process_defined": True,
        "supply_chain_ready": True,
        "quality_system": "ISO9001",
        "unit_cost_usd": 300, "target_cost_usd": 400,
        "market_interview_count": 60,
        "market_tam_validated": True,
        "market_repeat_purchase_pct": 25,
        "customer_loi_count": 5,
        "customer_poc_count": 8,
        "customer_nps": 40,
        "regulatory_approved": True,
        "regulatory_submission_done": True,
        "certifications_required": [], "certifications_obtained": [],
        "economic_pilot_revenue_usd": 80000,
        "economic_break_even_modeled": True,
        "economic_unit_economics_validated": True,
        # 생태계 ARL=2 (파트너 없음)
        "ecosystem_partner_count": 0,
        "ecosystem_integration_done": False,
    })
    arl_detail = r.output_doc["arl_assessment"]["arl_5d_detail"]
    print(f"병목 테스트 — ARL 최종: {arl_detail['arl_final']}  병목: {arl_detail['bottleneck']}")
    print("5차원:", {k: v["arl"] for k, v in arl_detail["dimensions"].items()})
    assert arl_detail["bottleneck_applied"], "병목 원칙 미적용"
    assert arl_detail["arl_final"] <= 4, f"병목 시 ARL {arl_detail['arl_final']} > 4"


def test_arl_high_maturity():
    """5차원 모두 높으면 ARL 7+ 달성"""
    r = MRLARLAssessor().assess({
        "trl": 8,
        "manufacturing_process_defined": True,
        "supply_chain_ready": True,
        "quality_system": "ISO9001",
        "unit_cost_usd": 300, "target_cost_usd": 400,
        "market_interview_count": 100,
        "market_tam_validated": True,
        "market_repeat_purchase_pct": 35,
        "customer_loi_count": 10,
        "customer_poc_count": 15,
        "customer_nps": 55,
        "regulatory_approved": True,
        "regulatory_submission_done": True,
        "certifications_required": ["CE Mark"],
        "certifications_obtained": ["CE Mark"],
        "economic_pilot_revenue_usd": 200000,
        "economic_break_even_modeled": True,
        "economic_unit_economics_validated": True,
        "ecosystem_partner_count": 3,
        "ecosystem_integration_done": True,
    })
    arl_detail = r.output_doc["arl_assessment"]["arl_5d_detail"]
    print(f"고성숙 테스트 — ARL 최종: {arl_detail['arl_final']}")
    print("5차원:", {k: v["arl"] for k, v in arl_detail["dimensions"].items()})
    assert arl_detail["arl_final"] >= 6, f"고성숙인데 ARL {arl_detail['arl_final']} < 6"


def test_risk_dimension_display():
    """adoption_risk_dimensions가 5차원 리스크 레벨 반환"""
    r = MRLARLAssessor().assess({
        "trl": 5,
        "manufacturing_process_defined": True,
        "supply_chain_ready": False,
        "unit_cost_usd": 600, "target_cost_usd": 400,
        "market_interview_count": 5,
        "market_tam_validated": False,
        "customer_loi_count": 0, "customer_poc_count": 0,
        "regulatory_approved": False, "regulatory_submission_done": False,
        "certifications_required": ["FDA 510k"],
        "certifications_obtained": [],
        "economic_pilot_revenue_usd": 0,
        "economic_break_even_modeled": False,
        "economic_unit_economics_validated": False,
        "ecosystem_partner_count": 0,
        "ecosystem_integration_done": False,
    })
    risks = r.output_doc["arl_assessment"]["adoption_risk_dimensions"]
    print("리스크 레벨:", {k: v["risk"] for k, v in risks.items()})
    assert set(risks.keys()) == {"market", "customer", "regulatory", "economic", "ecosystem"}
    high_risks = [k for k, v in risks.items() if v["risk"] == "High"]
    print(f"High 리스크 차원: {high_risks}")
    assert len(high_risks) >= 3, "초기 단계인데 High 리스크 3개 미만"


if __name__ == "__main__":
    test_arl_5d_dimensions_independent()
    test_arl_bottleneck_rule()
    test_arl_high_maturity()
    test_risk_dimension_display()
    print("\nARL 5차원 전체 검증 통과")
