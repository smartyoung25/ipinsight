"""보고서 데이터 파이프라인

분석(G-Stage) 결과 → StoreA/B 자동 구성 → 보고서 생성 → SQLite 영속화

파이프라인 흐름:
  입력(특허/기술 텍스트)
    → [Step1] PCML 분석 → StoreA
    → [Step2] SCR 스크리닝 → StoreB
    → [Step3] 보고서 타입 선택
    → [Step4] LLM 보고서 생성
    → [Step5] SQLite 저장 + 다운로드 URL
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

# DB 경로
_DB_PATH = Path(__file__).parent.parent / "data" / "reports.db"
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


# ── SQLite 초기화 ────────────────────────────────────────────────

def _init_db():
    with sqlite3.connect(_DB_PATH) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS reports (
                id          TEXT PRIMARY KEY,
                tech_id     TEXT NOT NULL,
                report_id   TEXT NOT NULL,
                tier        TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'pending',
                content_md  TEXT,
                key_findings TEXT,
                structured_data TEXT,
                pcml_score  REAL,
                scr_score   REAL,
                created_at  INTEGER NOT NULL,
                updated_at  INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id          TEXT PRIMARY KEY,
                tech_id     TEXT NOT NULL,
                tech_name   TEXT,
                input_text  TEXT,
                trl         INTEGER,
                store_a     TEXT,
                store_b     TEXT,
                reports_generated TEXT,
                status      TEXT NOT NULL DEFAULT 'running',
                created_at  INTEGER NOT NULL,
                finished_at INTEGER
            );

            CREATE INDEX IF NOT EXISTS idx_reports_tech
                ON reports(tech_id, report_id);
            CREATE INDEX IF NOT EXISTS idx_runs_tech
                ON pipeline_runs(tech_id);
        """)

_init_db()


@contextmanager
def _db():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ── StoreA/B 자동 구성 ──────────────────────────────────────────

def build_store_a_from_pcml(pcml_result: dict) -> dict:
    """PCML 분석 결과 → StoreA (보고서 입력 형식)"""
    return {
        "release_status":    pcml_result.get("release_status", "internal_only"),
        "pcml_score":        pcml_result.get("score", 0),
        "claim_count":       pcml_result.get("claim_count", 0),
        "independent_claims": pcml_result.get("independent_claims", []),
        "components":        pcml_result.get("components", []),
        "ipc_codes":         pcml_result.get("ipc_codes", []),
        "novelty":           pcml_result.get("novelty", {}),
        "inventive_step":    pcml_result.get("inventive_step", {}),
        "claim_quality":     pcml_result.get("claim_quality", {}),
        "prosecution_risk":  pcml_result.get("prosecution_risk", "medium"),
        "strengths":         pcml_result.get("strengths", []),
        "weaknesses":        pcml_result.get("weaknesses", []),
        "_version":          int(time.time()),
    }


def build_store_b_from_scr(scr_result: dict) -> dict:
    """SCR 스크리닝 결과 → StoreB"""
    return {
        "gate":              scr_result.get("gate", "Hold"),
        "scr_score":         scr_result.get("score", 0),
        "market_fit":        scr_result.get("market_fit", {}),
        "white_space":       scr_result.get("whiteSpace", []),
        "competitor_landscape": scr_result.get("competitorLandscape", {}),
        "technology_readiness": scr_result.get("technologyReadiness", {}),
        "commercialization_path": scr_result.get("commercializationPath", []),
        "risk_factors":      scr_result.get("riskFactors", []),
        "recommended_stages": scr_result.get("recommendedStages", []),
        "_version":          int(time.time()),
    }


def build_store_d_from_context(tech_name: str, trl: int, extra: dict | None = None) -> dict:
    """사용자 컨텍스트 → StoreD"""
    d = {
        "tech_name": tech_name,
        "trl":       trl,
        "tam_usd":   extra.get("tam_usd", 0) if extra else 0,
        "sam_usd":   extra.get("sam_usd", 0) if extra else 0,
        "som_usd":   extra.get("som_usd", 0) if extra else 0,
        "target_market": extra.get("target_market", "") if extra else "",
        "sector":    extra.get("sector", "") if extra else "",
    }
    return d


# ── 보고서 타입별 메타 ───────────────────────────────────────────

REPORT_META: dict[str, dict] = {
    "R1_investment":   {"label": "R1 투자·인수 심사", "icon": "💰", "tier": 1},
    "R2_enforcement":  {"label": "R2 권리행사·분쟁 전략", "icon": "⚖️", "tier": 1},
    "R3_commercialize":{"label": "R3 사업화·R&D 실행", "icon": "🚀", "tier": 1},
    "R4_portfolio":    {"label": "R4 포트폴리오·제출", "icon": "📋", "tier": 1},
    "R5_valuation":    {"label": "R5 기술가치평가", "icon": "📊", "tier": 2},
    "R6_ir":           {"label": "R6 투자자 IR 브리프", "icon": "📈", "tier": 2},
    "R7_license":      {"label": "R7 라이선스·기술이전", "icon": "🤝", "tier": 2},
    "R8_gov_ir":       {"label": "R8 정부지원·IR 제출", "icon": "🏛️", "tier": 3},
    "R9_sps":          {"label": "R9 선행기술조사(SPS)", "icon": "🔍", "tier": 1},
}


def recommend_reports(store_a: dict, store_b: dict, trl: int) -> list[dict]:
    """StoreA/B 분석 결과 기반 보고서 우선순위 추천"""
    recs = []

    pcml_score = store_a.get("pcml_score", 0)
    scr_score  = store_b.get("scr_score",  0)
    gate       = store_b.get("gate", "Hold")
    white_spaces = store_b.get("white_space", [])

    # R1: PCML 점수 높을 때
    if pcml_score >= 60:
        recs.append({"id": "R1_investment", "priority": "🔴 필수",
                     "reason": f"PCML 점수 {pcml_score:.0f} — 투자 심사 보고서 적합"})
    # R9: 선행기술조사 항상 권장
    recs.append({"id": "R9_sps", "priority": "🔴 필수",
                 "reason": "신규성·진보성 검토 — 모든 IP 전략의 기반"})
    # R3: SCR Go일 때
    if gate == "Go":
        recs.append({"id": "R3_commercialize", "priority": "🟠 권장",
                     "reason": f"SCR {gate} — 사업화 실행 단계 진입 가능"})
    # R5: TRL 높을 때
    if trl >= 5:
        recs.append({"id": "R5_valuation", "priority": "🟠 권장",
                     "reason": f"TRL {trl} — 기술가치평가 신뢰도 확보 가능"})
    # R2: 경쟁사 많을 때
    competitors = store_b.get("competitor_landscape", {}).get("majorPlayers", [])
    if len(competitors) >= 2:
        recs.append({"id": "R2_enforcement", "priority": "🟠 권장",
                     "reason": f"경쟁사 {len(competitors)}곳 감지 — 분쟁 전략 필요"})
    # R6: 화이트스페이스 있을 때
    if white_spaces:
        recs.append({"id": "R6_ir", "priority": "🟡 선택",
                     "reason": f"화이트스페이스 {len(white_spaces)}건 — IR 브리프 연동 가능"})
    # R4, R7, R8 기본 추가
    for rid, reason in [
        ("R4_portfolio", "포트폴리오 정리 및 대외 제출용"),
        ("R7_license",   "기술이전·라이선스 협상 준비"),
        ("R8_gov_ir",    "정부지원 과제 및 IR 제출용"),
    ]:
        if not any(r["id"] == rid for r in recs):
            recs.append({"id": rid, "priority": "🟡 선택", "reason": reason})

    # 메타 병합
    result = []
    for r in recs[:6]:
        meta = REPORT_META.get(r["id"], {})
        result.append({**r, **meta})
    return result


# ── LLM 보고서 생성 ─────────────────────────────────────────────

def _build_prompt(report_id: str, tier: str, store_a: dict, store_b: dict, store_d: dict,
                  compacted_deps: dict | None = None) -> str:
    from api.routers.reports import _REPORT_ROLES, _REPORT_DESCRIPTIONS
    role = _REPORT_ROLES.get(report_id, "IPInsight 보고서 분석가")
    desc = _REPORT_DESCRIPTIONS.get(report_id, "")
    tier_txt = {"FULL": "FULL (전체)", "LITE": "LITE (요약)", "FREE": "FREE (핵심만)"}.get(tier, tier)
    dep_block = ""
    if compacted_deps:
        dep_block = f"\n[의존 보고서 요약 (참고용)]\n{json.dumps(compacted_deps, ensure_ascii=False, indent=2)}\n"
    return f"""[ROLE] {role}

[보고서] {REPORT_META.get(report_id, {}).get('label', report_id)} — {tier_txt}

[설명]
{desc}

[PCML 분석 결과 (StoreA)]
{json.dumps(store_a, ensure_ascii=False, indent=2)}

[SCR 스크리닝 결과 (StoreB)]
{json.dumps(store_b, ensure_ascii=False, indent=2)}

[사용자 컨텍스트 (StoreD)]
{json.dumps(store_d, ensure_ascii=False, indent=2)}
{dep_block}
[출력 형식] JSON:
{{
  "reportId": "string",
  "keyFindings": ["string x3"],
  "sections": ["string"],
  "content": "string (마크다운)",
  "structuredData": {{}}
}}

[절대 금지] 원문에 없는 수치 생성 / 근거 없는 결론 / N/A 대신 숫자 꾸미기
"""


# ── StoreA 강제 인계 (hallucination 방지) ────────────────────────────
# JS ip-insight 의 enrichR{N}FromStoreA 패턴 이식.
# LLM이 빈 배열을 내거나 임의 해석해도 PCML 결과로 덮어쓴다.

def _enrich_from_store_a(report_id: str, result: dict, store_a: dict) -> dict:
    """LLM 출력의 청구항/구성요소 필드를 StoreA PCML 값으로 강제 덮어쓰기."""
    claims = store_a.get("independent_claims") or []
    components = store_a.get("components") or []
    ipc_codes = store_a.get("ipc_codes") or []

    sd = result.setdefault("structuredData", {})

    # 모든 보고서: patentBasicInfo, 핵심 청구항, 구성요소 맵 보장
    sd["patentBasicInfo"] = {
        "ipcCodes":    ipc_codes,
        "pcmlScore":   store_a.get("pcml_score", 0),
        "releaseStatus": store_a.get("release_status", "internal_only"),
    }
    # 청구항·구성요소: LLM 출력이 빈 리스트면 StoreA 값으로 교체
    if not sd.get("claims"):
        sd["claims"] = claims
    if not sd.get("components"):
        sd["components"] = components

    # R5: 가치평가 필드가 비면 TRL·PCML 점수 기반 최소 블록 주입
    if report_id == "R5_valuation":
        trl = (result.get("structuredData") or {}).get("trl") or 0
        if not sd.get("valuationBlock"):
            sd["valuationBlock"] = {
                "trl": trl,
                "pcml_score": store_a.get("pcml_score", 0),
                "note": "LLM 미산출 — PCML 점수 기준 최소값",
            }

    # R6: R5 의존 재무 블록 보장
    if report_id == "R6_ir" and not sd.get("r5Summary"):
        sd["r5Summary"] = {"note": "R5 미생성 또는 비어있음 — R5 먼저 생성 권장"}

    # R7: R5·R2 keyFindings 헤더 주입
    if report_id == "R7_license":
        strengths = store_a.get("strengths") or []
        if strengths and not sd.get("pcmlStrengths"):
            sd["pcmlStrengths"] = strengths[:3]

    return result


# ── 보고서 수치 일관성 교차검증 ─────────────────────────────────────────

def _validate_numeric_consistency(report_id: str, result: dict, store_a: dict) -> list[str]:
    """보고서 수치와 PCML StoreA 값의 일관성을 검사하고 경고 목록 반환."""
    warnings: list[str] = []
    sd = result.get("structuredData") or {}
    pbi = sd.get("patentBasicInfo") or {}

    # PQE ↔ PCML 점수: ±10점 허용
    pqe = sd.get("pqeScore") or sd.get("gate", {}).get("score") if isinstance(sd.get("gate"), dict) else None
    pcml = pbi.get("pcmlScore") or store_a.get("pcml_score")
    if pqe is not None and pcml is not None:
        try:
            diff = abs(float(pqe) - float(pcml))
            if diff > 10:
                warnings.append(f"[수치불일치] PQE점수({pqe}) ↔ PCML점수({pcml}) 차이 {diff:.1f}점 초과")
        except (TypeError, ValueError):
            pass

    # 청구항 수 일치 여부
    report_claims = sd.get("claims") or []
    store_claims = store_a.get("independent_claims") or []
    if report_claims and store_claims and len(report_claims) != len(store_claims):
        warnings.append(
            f"[청구항수 불일치] 보고서={len(report_claims)}건, PCML={len(store_claims)}건"
        )

    # 구성요소 수: 보고서가 StoreA보다 현저히 많으면 환각 의심
    report_comps = sd.get("components") or []
    store_comps = store_a.get("components") or []
    if store_comps and len(report_comps) > len(store_comps) * 2:
        warnings.append(
            f"[구성요소 과다] 보고서={len(report_comps)}건 vs PCML={len(store_comps)}건 — 환각 가능성"
        )

    return warnings


# ── 의존 보고서 컴팩션 (token 절감) ──────────────────────────────────
# JS ip-insight 의 compactDependencies 패턴 이식.
# Tier-2/3 보고서 생성 시 선행 보고서 전체를 넘기지 않고 핵심만 축약.

def _compact_dep_reports(dep_reports: dict) -> dict:
    """의존 보고서 → keyFindings + 핵심 structuredData 블록만 추출."""
    compacted: dict = {}
    for rid, content in (dep_reports or {}).items():
        if not isinstance(content, dict):
            continue
        compacted[rid] = {
            "keyFindings": (content.get("keyFindings") or [])[:5],
            "valuationBlock": (content.get("structuredData") or {}).get("valuationBlock"),
            "gate": (content.get("structuredData") or {}).get("gate"),
            "pcmlScore": (content.get("structuredData") or {}).get("patentBasicInfo", {}).get("pcmlScore"),
        }
        # None 필드 제거 (Firestore 패턴과 동일 — undefined 없애기)
        compacted[rid] = {k: v for k, v in compacted[rid].items() if v is not None}
    return compacted


def generate_report_content(
    report_id: str,
    tech_id: str,
    tier: str,
    store_a: dict,
    store_b: dict,
    store_d: dict,
    dep_reports: dict | None = None,
) -> dict:
    """LLM 또는 폴백으로 보고서 콘텐츠 생성"""
    import logging
    log = logging.getLogger(__name__)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    groq_key = os.environ.get("GROQ_API_KEY", "")

    result = {}
    compacted_deps = _compact_dep_reports(dep_reports)

    # Anthropic 우선 시도 (크레딧 오류 시 즉시 Groq로 넘어감)
    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            # LITE는 haiku(빠름/저렴), FULL은 sonnet
            model = "claude-haiku-4-5-20251001" if tier in ("FREE","LITE") else "claude-sonnet-4-6"
            prompt = _build_prompt(report_id, tier, store_a, store_b, store_d, compacted_deps)
            msg = client.messages.create(
                model=model, max_tokens=6000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            m = re.search(r"```(?:json)?\s*(\{[\s\S]+?\})\s*```", raw)
            if not m:
                m = re.search(r"\{[\s\S]+\}", raw)
            if m:
                json_str = m.group(1) if m.lastindex else m.group()
                result = json.loads(json_str)
                result["_llm"] = f"anthropic/{model}"
        except Exception as e:
            err_str = str(e)
            if any(w in err_str.lower() for w in ["credit","billing","balance","529","overloaded"]):
                log.info("Anthropic 크레딧/과부하 — Groq로 전환: %s", err_str[:100])
            else:
                log.warning("Anthropic 오류: %s", err_str[:200])

    # Groq 폴백
    if not result and groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            prompt = _build_prompt(report_id, tier, store_a, store_b, store_d, compacted_deps)
            # LITE/FREE는 작은 모델(토큰 절약), FULL은 70b
            model = "llama-3.1-8b-instant" if tier in ("FREE","LITE") else "llama-3.3-70b-versatile"
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0,
                seed=42,
            )
            raw = resp.choices[0].message.content.strip()
            m = re.search(r"```(?:json)?\s*(\{[\s\S]+?\})\s*```", raw)
            if not m:
                m = re.search(r"\{[\s\S]+\}", raw)
            if m:
                json_str = m.group(1) if m.lastindex else m.group()
                result = json.loads(json_str)
                result["_llm"] = f"groq/{model}"
            else:
                log.warning("Groq 응답 JSON 파싱 실패: %s", raw[:200])
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate" in err_str.lower():
                import time
                log.warning("Groq 429 — 지수 백오프 재시도 (최대 2회): %s", err_str[:100])
                for delay in (10, 30):
                    try:
                        time.sleep(delay)
                        resp = client.chat.completions.create(
                            model=model,
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=4000,
                            temperature=0,
                            seed=42,
                        )
                        raw = resp.choices[0].message.content.strip()
                        m = re.search(r"```(?:json)?\s*(\{[\s\S]+?\})\s*```", raw)
                        if not m:
                            m = re.search(r"\{[\s\S]+\}", raw)
                        if m:
                            json_str = m.group(1) if m.lastindex else m.group()
                            result = json.loads(json_str)
                            result["_llm"] = f"groq/{model}"
                        break
                    except Exception as retry_e:
                        log.warning("Groq 재시도(%ds) 실패: %s", delay, retry_e)
            else:
                log.error("Groq 오류: %s", err_str[:300])

    if not result:
        meta = REPORT_META.get(report_id, {})
        result = {
            "reportId": f"IAH-{tech_id}-{report_id}",
            "keyFindings": ["LLM 일시 불가 — Anthropic 크레딧 부족 또는 Groq 일일 한도 초과. 잠시 후 재시도."],
            "sections": ["입력 요약", "기본 진단"],
            "content": (
                f"# {meta.get('label', report_id)}\n\n"
                f"**기술 ID**: {tech_id}  \n"
                f"**PCML 점수**: {store_a.get('pcml_score', 'N/A')}  \n"
                f"**SCR 점수**: {store_b.get('scr_score', 'N/A')}  \n"
                f"**Gate**: {store_b.get('gate', 'N/A')}  \n\n"
                f"> ⚠️ LLM 일시 불가: Anthropic 크레딧 부족 또는 Groq 일일 토큰 한도(100k) 초과.\n"
                f"> Groq는 매일 00:00 UTC 리셋됩니다. Anthropic은 Plans & Billing에서 크레딧 충전 필요.\n"
            ),
            "structuredData": {},
            "_fallback": True,
        }

    # StoreA 강제 인계 — LLM 출력의 청구항/구성요소 필드를 PCML 결과로 덮어쓰기
    result = _enrich_from_store_a(report_id, result, store_a)

    # 수치 일관성 교차검증 — 경고를 보고서에 포함
    consistency_warnings = _validate_numeric_consistency(report_id, result, store_a)
    if consistency_warnings:
        import logging
        logging.getLogger(__name__).warning("수치 불일치 감지 [%s]: %s", report_id, consistency_warnings)
        result.setdefault("_warnings", []).extend(consistency_warnings)

    return result


# ── SQLite 저장/조회 ─────────────────────────────────────────────

def save_report(
    tech_id: str, report_id: str, tier: str,
    content: dict, pcml_score: float = 0, scr_score: float = 0,
) -> str:
    rid = str(uuid.uuid4())
    now = int(time.time())
    with _db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO reports
              (id, tech_id, report_id, tier, status, content_md, key_findings,
               structured_data, pcml_score, scr_score, created_at, updated_at)
            VALUES (?,?,?,?,'completed',?,?,?,?,?,?,?)
        """, (
            rid, tech_id, report_id, tier,
            content.get("content", ""),
            json.dumps(content.get("keyFindings", []), ensure_ascii=False),
            json.dumps(content.get("structuredData", {}), ensure_ascii=False),
            pcml_score, scr_score, now, now,
        ))
    return rid


def list_reports(tech_id: str | None = None) -> list[dict]:
    with _db() as conn:
        if tech_id:
            rows = conn.execute(
                "SELECT * FROM reports WHERE tech_id=? ORDER BY created_at DESC", (tech_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM reports ORDER BY created_at DESC LIMIT 100"
            ).fetchall()
    return [dict(r) for r in rows]


def get_report_by_db_id(rid: str) -> dict | None:
    with _db() as conn:
        row = conn.execute("SELECT * FROM reports WHERE id=?", (rid,)).fetchone()
    return dict(row) if row else None


def get_latest_report(tech_id: str, report_id: str) -> dict | None:
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM reports WHERE tech_id=? AND report_id=? ORDER BY created_at DESC LIMIT 1",
            (tech_id, report_id),
        ).fetchone()
    return dict(row) if row else None


# ── 파이프라인 실행 기록 ─────────────────────────────────────────

def save_pipeline_run(
    tech_id: str, tech_name: str, input_text: str, trl: int,
    store_a: dict, store_b: dict, reports: list[str],
) -> str:
    run_id = str(uuid.uuid4())
    now = int(time.time())
    with _db() as conn:
        conn.execute("""
            INSERT INTO pipeline_runs
              (id, tech_id, tech_name, input_text, trl, store_a, store_b,
               reports_generated, status, created_at, finished_at)
            VALUES (?,?,?,?,?,?,?,?,'completed',?,?)
        """, (
            run_id, tech_id, tech_name, input_text, trl,
            json.dumps(store_a, ensure_ascii=False),
            json.dumps(store_b, ensure_ascii=False),
            json.dumps(reports, ensure_ascii=False),
            now, now,
        ))
    return run_id


def list_pipeline_runs(tech_id: str | None = None) -> list[dict]:
    with _db() as conn:
        if tech_id:
            rows = conn.execute(
                "SELECT * FROM pipeline_runs WHERE tech_id=? ORDER BY created_at DESC LIMIT 50",
                (tech_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM pipeline_runs ORDER BY created_at DESC LIMIT 50"
            ).fetchall()
    return [dict(r) for r in rows]
