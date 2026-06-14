"""야간 Bulk 사전 적재 스케줄러
실행: python scripts/scheduled_refresh.py [--target patent|paper|market|all] [--dry-run]
  --dry-run: 실제 API 호출 없이 계획만 출력
cron 예시 (Windows Task Scheduler or cron):
  매일 02:00  → --target patent
  매일 03:00  → --target paper
  매주 일 01:00 → --target market,esg
  매월 01일   → --target regulatory
"""
from __future__ import annotations
import sys
import json
import time
import argparse
import hashlib
from pathlib import Path

# ─── 경로 설정 ────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
CACHE_DIR = ROOT / ".rag_cache"
CACHE_DIR.mkdir(exist_ok=True)
LOG_FILE  = ROOT / "logs" / "refresh.jsonl"
LOG_FILE.parent.mkdir(exist_ok=True)

# ─── 사전 적재 작업 목록 ──────────────────────────────────
# 각 작업은 (커넥터, 메서드, 인수) 튜플의 리스트
REFRESH_JOBS: dict[str, list[dict]] = {
    "patent": [
        {"connector": "PatentConnector", "method": "search_by_cpc",
         "kwargs": {"cpc_code": "A01G", "limit": 10}, "label": "AgriTech CPC"},
        {"connector": "PatentConnector", "method": "search_by_cpc",
         "kwargs": {"cpc_code": "Y02E", "limit": 10}, "label": "CleanEnergy CPC"},
        {"connector": "PatentConnector", "method": "search_by_cpc",
         "kwargs": {"cpc_code": "A61K", "limit": 10}, "label": "Pharma CPC"},
    ],
    "paper": [
        {"connector": "PaperConnector", "method": "search_openalex",
         "kwargs": {"query": "smart farm IoT", "limit": 20}, "label": "AgriTech 논문"},
        {"connector": "PaperConnector", "method": "search_openalex",
         "kwargs": {"query": "carbon capture technology", "limit": 20}, "label": "CleanTech 논문"},
        {"connector": "PaperConnector", "method": "search_openalex",
         "kwargs": {"query": "precision medicine biomarker", "limit": 20}, "label": "Bio 논문"},
    ],
    "market": [
        {"connector": "MarketConnector", "method": "gdp_indicators",
         "kwargs": {"countries": ["KR", "US", "DE", "JP", "CN", "IN"],
                    "indicators": ["NY.GDP.MKTP.CD", "GB.XPD.RSDV.GD.ZS"]},
         "label": "주요6국 GDP·R&D"},
        {"connector": "MarketConnector", "method": "tam_estimate",
         "kwargs": {"sector": "agritech",      "countries": ["KR", "US", "JP", "IN", "VN"]},
         "label": "AgriTech TAM"},
        {"connector": "MarketConnector", "method": "tam_estimate",
         "kwargs": {"sector": "software_saas", "countries": ["KR", "US", "JP", "IN"]},
         "label": "SaaS TAM"},
        {"connector": "MarketConnector", "method": "tam_estimate",
         "kwargs": {"sector": "energy",        "countries": ["KR", "US", "DE", "CN", "IN"]},
         "label": "에너지 TAM"},
    ],
    "esg": [
        {"connector": "ESGConnector", "method": "emissions_by_sector",
         "kwargs": {"sector": "agriculture", "countries": ["KOR", "USA", "CHN", "IND"]},
         "label": "농업 탄소 배출"},
        {"connector": "ESGConnector", "method": "emissions_by_sector",
         "kwargs": {"sector": "power",       "countries": ["KOR", "USA", "DEU", "JPN"]},
         "label": "전력 탄소 배출"},
        {"connector": "ESGConnector", "method": "owid_energy_trend",
         "kwargs": {"country_code": "KOR", "dataset": "share-of-electricity-low-carbon"},
         "label": "한국 저탄소 전력 추이"},
    ],
    "clinical": [
        {"connector": "ClinicalConnector", "method": "search_trials",
         "kwargs": {"query": "smart farming precision agriculture", "limit": 10},
         "label": "AgriTech 임상·규제"},
        {"connector": "ClinicalConnector", "method": "search_trials",
         "kwargs": {"query": "wearable medical device sensor", "limit": 10},
         "label": "의료기기 임상"},
    ],
    "regulatory": [
        # 규제는 정적 지식 기반 — 캐시 무효화 없이 월별 파일 업데이트
        # 이 job은 knowledge/ 파일 freshness 만 체크
        {"connector": "_static_check", "method": "knowledge_freshness",
         "kwargs": {"files": ["global_markets.json", "country_programs.json"]},
         "label": "정적 지식 파일 최신성 확인"},
    ],
}


def _log(entry: dict) -> None:
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _cache_key(connector: str, method: str, kwargs: dict) -> str:
    raw = f"{connector}:{method}:{json.dumps(kwargs, sort_keys=True)}"
    return hashlib.md5(raw.encode()).hexdigest()


def _is_stale(cache_file: Path, ttl_hours: int) -> bool:
    if not cache_file.exists():
        return True
    age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
    return age_hours > ttl_hours


def run_job(job: dict, dry_run: bool = False) -> dict:
    """단일 사전 적재 작업 실행"""
    conn_name = job["connector"]
    method    = job["method"]
    kwargs    = job["kwargs"]
    label     = job["label"]

    start_ts = time.time()

    if conn_name == "_static_check":
        knowledge_dir = ROOT / "knowledge"
        statuses = []
        for fname in kwargs["files"]:
            fpath = knowledge_dir / fname
            age_h = (time.time() - fpath.stat().st_mtime) / 3600 if fpath.exists() else 9999
            statuses.append({"file": fname, "age_hours": round(age_h, 1),
                              "fresh": age_h < 720})
        return {"label": label, "status": "checked", "details": statuses,
                "elapsed_s": round(time.time() - start_ts, 2)}

    if dry_run:
        return {"label": label, "status": "dry_run_skipped",
                "connector": conn_name, "method": method, "elapsed_s": 0.0}

    try:
        # 커넥터 동적 임포트
        if conn_name == "PatentConnector":
            from pipeline.code_linker import PatentConnector
            obj = PatentConnector()
        elif conn_name == "PaperConnector":
            from pipeline.connectors.paper_connector import PaperConnector
            obj = PaperConnector()
        elif conn_name == "MarketConnector":
            from pipeline.connectors.market_connector import MarketConnector
            obj = MarketConnector()
        elif conn_name == "ESGConnector":
            from pipeline.connectors.esg_connector import ESGConnector
            obj = ESGConnector()
        elif conn_name == "ClinicalConnector":
            from pipeline.connectors.clinical_connector import ClinicalConnector
            obj = ClinicalConnector()
        else:
            return {"label": label, "status": "unknown_connector", "elapsed_s": 0.0}

        result = getattr(obj, method)(**kwargs)
        elapsed = round(time.time() - start_ts, 2)
        return {"label": label, "status": "ok", "elapsed_s": elapsed,
                "result_keys": list(result.keys()) if isinstance(result, dict) else "list"}
    except Exception as e:
        return {"label": label, "status": "error",
                "error": str(e)[:120], "elapsed_s": round(time.time() - start_ts, 2)}


def run_target(target: str, dry_run: bool = False) -> None:
    targets = [t.strip() for t in target.split(",")]
    if "all" in targets:
        targets = list(REFRESH_JOBS.keys())

    total_ok = total_err = 0
    ts_start = time.time()

    for t in targets:
        jobs = REFRESH_JOBS.get(t, [])
        if not jobs:
            print(f"[WARN] 알 수 없는 타겟: {t}")
            continue
        print(f"\n{'='*50}")
        print(f"▶ {t.upper()} 적재 ({len(jobs)}개 작업)")
        print(f"{'='*50}")
        for job in jobs:
            result = run_job(job, dry_run=dry_run)
            status_icon = {"ok": "✅", "error": "❌", "dry_run_skipped": "⬜", "checked": "🔍"}.get(result["status"], "❓")
            print(f"  {status_icon} [{result['elapsed_s']}s] {result['label']}: {result['status']}")
            if result["status"] == "error":
                print(f"     └ {result.get('error', '')}")
                total_err += 1
            else:
                total_ok += 1
            _log({"ts": time.time(), "target": t, **result})

    total = round(time.time() - ts_start, 1)
    print(f"\n{'─'*50}")
    print(f"완료: {total_ok}개 성공 | {total_err}개 실패 | 총 {total}초")
    _log({"ts": time.time(), "summary": True, "ok": total_ok,
          "err": total_err, "elapsed_s": total})


def print_plan() -> None:
    """사전 적재 계획 출력 (--plan 옵션)"""
    print("\n📅 Bulk 사전 적재 계획")
    print("─" * 60)
    from pipeline.query_router import BULK_SCHEDULE, CACHE_TTL
    rows = [
        ("커넥터", "TTL(h)", "스케줄", "작업 수"),
        ("─"*12, "─"*6, "─"*20, "─"*8),
    ]
    for conn, sched in BULK_SCHEDULE.items():
        rows.append((conn, str(CACHE_TTL.get(conn, "?")), sched,
                     str(len(REFRESH_JOBS.get(conn, [])))))
    for row in rows:
        print(f"  {row[0]:<14}{row[1]:<8}{row[2]:<22}{row[3]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IPInsight Bulk 사전 적재")
    parser.add_argument("--target",  default="all",
                        help="patent|paper|market|esg|clinical|regulatory|all (콤마 구분)")
    parser.add_argument("--dry-run", action="store_true", help="API 호출 없이 계획만 출력")
    parser.add_argument("--plan",    action="store_true", help="전체 스케줄 계획 출력")
    args = parser.parse_args()

    if args.plan:
        print_plan()
    else:
        mode = "[DRY-RUN] " if args.dry_run else ""
        print(f"\n🚀 {mode}IPInsight Bulk 적재 시작 — 타겟: {args.target}")
        run_target(args.target, dry_run=args.dry_run)
