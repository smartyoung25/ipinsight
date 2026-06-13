"""IP 기술사업화 종합 리포트 빌더 — 파이프라인 결과 → 투자자용 요약"""
from __future__ import annotations
from typing import Any

# 단계별 표시 이름
_STAGE_LABELS = {
    "0":  ("G0",  "기술발굴·등록"),
    "1":  ("G1",  "IP 구조화"),
    "2":  ("G2",  "TRL 평가"),
    "3":  ("G3",  "시장성 분석"),
    "4":  ("G4",  "고객 발굴"),
    "5":  ("G5",  "비즈니스모델"),
    "6":  ("G6",  "기술가치평가"),
    "7":  ("G7",  "PoC 실증"),
    "8":  ("G8",  "MRL·ARL 평가"),
    "9":  ("G9",  "거래구조 설계"),
    "10": ("G10", "성과 관리"),
}

_GATE_EMOJI = {"Go": "✅", "Hold": "⚠️", "Kill": "🚫"}
_GATE_KO    = {"Go": "진행", "Hold": "보류", "Kill": "중단"}


def build_report(tech_id: str, all_results: dict[str, Any]) -> dict:
    """all_results: {stage_key: {gate, score, output_doc, next_actions, warnings}}"""

    all_results = {str(k): v for k, v in all_results.items()}
    stages_run = sorted(all_results.keys(), key=lambda x: int(x) if x.isdigit() else 99)
    scorecard  = _build_scorecard(stages_run, all_results)
    summary    = _build_executive_summary(tech_id, scorecard, all_results)
    maturity   = _build_maturity_profile(all_results)
    valuation  = _extract_valuation(all_results)
    deal       = _extract_deal(all_results)
    actions    = _consolidate_actions(all_results)
    bottleneck = _find_bottleneck(scorecard)

    return {
        "report_meta": {
            "tech_id": tech_id,
            "stages_evaluated": len(stages_run),
            "report_type": "IP 기술사업화 종합진단 리포트",
            "standard": "WIPO Lab-to-Market · TRL/MRL/ARL · IP Lifecycle",
        },
        "executive_summary":   summary,
        "scorecard":           scorecard,
        "maturity_profile":    maturity,
        "valuation_snapshot":  valuation,
        "deal_structure":      deal,
        "bottleneck_analysis": bottleneck,
        "priority_actions":    actions[:5],
    }


def _build_scorecard(stages_run: list, results: dict) -> list[dict]:
    rows = []
    for sk in stages_run:
        r    = results[sk]
        gate = r.get("gate", "N/A")
        score = r.get("score", 0)
        label_pair = _STAGE_LABELS.get(sk, (f"G{sk}", ""))
        rows.append({
            "stage_num":  sk,
            "stage_id":   label_pair[0],
            "stage_name": label_pair[1],
            "score":      round(score, 1),
            "gate":       gate,
            "gate_ko":    _GATE_KO.get(gate, gate),
            "gate_icon":  _GATE_EMOJI.get(gate, ""),
            "warnings":   len(r.get("warnings", [])),
        })
    return rows


def _build_executive_summary(tech_id: str, scorecard: list, results: dict) -> dict:
    total    = len(scorecard)
    go_cnt   = sum(1 for r in scorecard if r["gate"] == "Go")
    hold_cnt = sum(1 for r in scorecard if r["gate"] == "Hold")
    kill_cnt = sum(1 for r in scorecard if r["gate"] == "Kill")
    avg_score = round(sum(r["score"] for r in scorecard) / max(total, 1), 1)

    if kill_cnt > 0:
        overall = "Kill"
        verdict = f"Kill 단계 {kill_cnt}개 존재 — 근본 이슈 해소 후 재진입 필요"
    elif hold_cnt > total * 0.4:
        overall = "Hold"
        verdict = f"Hold 단계 {hold_cnt}개 — 주요 보완 후 투자·사업화 진행 가능"
    else:
        overall = "Go"
        verdict = f"전 {total}개 단계 중 {go_cnt}개 통과 — 사업화 진행 권고"

    return {
        "tech_id":     tech_id,
        "overall_gate": overall,
        "overall_icon": _GATE_EMOJI.get(overall, ""),
        "verdict":     verdict,
        "avg_score":   avg_score,
        "stage_counts": {"go": go_cnt, "hold": hold_cnt, "kill": kill_cnt, "total": total},
    }


def _build_maturity_profile(results: dict) -> dict:
    """TRL·MRL·ARL 3축 성숙도 추출"""
    profile: dict = {}

    # TRL — G2
    if "2" in results:
        doc = results["2"].get("output_doc", {})
        trl_data = doc.get("trl_assessment", {})
        profile["trl"] = {
            "current": trl_data.get("current_trl", "N/A"),
            "target":  trl_data.get("target_trl", "N/A"),
            "name":    trl_data.get("trl_name", ""),
            "gap":     trl_data.get("trl_gap", "N/A"),
        }

    # MRL / ARL — G8
    if "8" in results:
        doc = results["8"].get("output_doc", {})
        mrl = doc.get("mrl_assessment", {})
        arl = doc.get("arl_assessment", {})
        profile["mrl"] = {
            "level": mrl.get("mrl_level", mrl.get("mrl_score", "N/A")),
            "name":  mrl.get("mrl_name", ""),
        }
        arl5d = arl.get("arl_5d_detail", {})
        dims = {}
        for k, v in arl5d.items():
            if isinstance(v, dict):
                dims[k] = v.get("score", v.get("arl_score", "N/A"))
            else:
                dims[k] = v
        profile["arl"] = {
            "level":      arl.get("arl_level", arl.get("overall_arl", "N/A")),
            "name":       arl.get("arl_name", ""),
            "bottleneck": arl.get("bottleneck_dimension", ""),
            "dimensions": dims,
        }

    # G6 TRL 보조 (G2 없을 때 폴백)
    if "trl" not in profile and "6" in results:
        doc = results["6"].get("output_doc", {})
        val = doc.get("tech_valuation_report", {})
        profile["trl"] = {"current": val.get("trl_at_valuation", "N/A"), "target": "N/A", "label": ""}

    return profile


def _extract_valuation(results: dict) -> dict:
    if "6" not in results:
        return {}
    doc = results["6"].get("output_doc", {})
    rep = doc.get("tech_valuation_report", {})
    mc  = doc.get("monte_carlo_simulation", {})
    return {
        "weighted_value_usd":    rep.get("weighted_value_usd", 0),
        "primary_method":        rep.get("primary_method", ""),
        "methodology":           rep.get("methodology", ""),
        "p10_usd":               mc.get("p10", 0),
        "p50_usd":               mc.get("p50", 0),
        "p90_usd":               mc.get("p90", 0),
        "risk_adjusted_usd":     doc.get("risk_adjusted_value", {}).get("risk_adjusted_usd", 0),
    }


def _extract_deal(results: dict) -> dict:
    if "9" not in results:
        return {}
    doc = results["9"].get("output_doc", {})
    rec = doc.get("deal_type_recommendation", {})
    vc  = doc.get("venture_client_strategy", {})
    return {
        "recommended_deal":    rec.get("recommended", ""),
        "rationale":           rec.get("rationale", ""),
        "timeline_months":     rec.get("timeline_months", ""),
        "venture_client":      vc.get("applicable", False),
        "vc_matched_programs": [p["corp"] for p in vc.get("matched_programs", [])],
    }


def _find_bottleneck(scorecard: list) -> dict:
    if not scorecard:
        return {}
    lowest = min(scorecard, key=lambda r: r["score"])
    kills  = [r for r in scorecard if r["gate"] == "Kill"]
    return {
        "lowest_score_stage": {
            "stage_id":   lowest["stage_id"],
            "stage_name": lowest["stage_name"],
            "score":      lowest["score"],
            "gate":       lowest["gate"],
        },
        "kill_stages": [
            {"stage_id": r["stage_id"], "stage_name": r["stage_name"], "score": r["score"]}
            for r in kills
        ],
        "recommendation": (
            f"{kills[0]['stage_name']} 단계가 Kill — 이 병목을 먼저 해소해야 후속 투자 의미 있음"
            if kills else
            f"{lowest['stage_name']} 단계(최저 {lowest['score']}점)가 취약 — 우선 보강 권고"
        ),
    }


def _consolidate_actions(results: dict) -> list[str]:
    """전 단계 next_actions 통합 — Kill 단계 우선, 중복 제거"""
    kill_actions, other_actions = [], []
    for r in results.values():
        gate    = r.get("gate", "")
        actions = r.get("next_actions", [])
        if gate == "Kill":
            kill_actions.extend(actions)
        elif gate == "Hold":
            other_actions.extend(actions[:2])
        else:
            other_actions.extend(actions[:1])

    seen, merged = set(), []
    for a in kill_actions + other_actions:
        if a not in seen:
            seen.add(a)
            merged.append(a)
    return merged
