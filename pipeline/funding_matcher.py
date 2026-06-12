"""단계별 최적 정부지원 프로그램 자동 매칭"""
from __future__ import annotations
import json
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


def match_funding(trl: int, country: str = "", sector: str = "", stage_id: str = "") -> list[dict]:
    """
    TRL·국가·산업분야·단계를 기반으로 최적 정부지원 프로그램 추천.

    반환: [{program, country, type, funding, apply_stage, notes, match_score}]
    """
    kb_path = KNOWLEDGE_DIR / "country_programs.json"
    if not kb_path.exists():
        return []

    programs = json.loads(kb_path.read_text(encoding="utf-8")).get("programs", [])
    results = []

    for prog in programs:
        score = 0
        # TRL 범위 매칭 (50점)
        trl_range = prog.get("trl_range", [0, 10])
        if trl_range[0] <= trl <= trl_range[1]:
            score += 50
        elif abs(trl - trl_range[0]) <= 1 or abs(trl - trl_range[1]) <= 1:
            score += 25  # 인접 TRL
        # 국가 매칭 (30점)
        if country and prog.get("country", "").upper() == country.upper():
            score += 30
        elif not country:
            score += 15  # 국가 미지정 시 부분 점수
        # 단계 매칭 (20점)
        if stage_id and stage_id in prog.get("apply_stage", []):
            score += 20

        if score >= 25:
            funding_info = {}
            for key in ["funding_usd", "funding_krw", "funding_eur", "funding_jpy"]:
                if prog.get(key):
                    funding_info = prog[key]
                    break

            results.append({
                "program": prog["name"],
                "country": prog["country"],
                "type": prog["type"],
                "funding": funding_info,
                "equity_free": prog.get("equity_free", True),
                "apply_stage": prog.get("apply_stage", []),
                "notes": prog.get("notes", ""),
                "url": prog.get("url", ""),
                "match_score": score,
            })

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:8]


def recommend_funding_sequence(trl_current: int, trl_target: int, country: str = "") -> list[dict]:
    """TRL 현재→목표 경로에서 단계별 최적 자금조달 시퀀스 반환"""
    sequence = []
    for trl in range(trl_current, min(trl_target + 1, 10)):
        matched = match_funding(trl=trl, country=country)
        if matched:
            sequence.append({
                "trl": trl,
                "recommended_programs": matched[:2],
                "estimated_funding": matched[0]["funding"] if matched else {},
            })
    return sequence
