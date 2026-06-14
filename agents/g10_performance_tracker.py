"""G10 성과관리·환류 — Horizon Europe + ISO 혁신관리 + 실시간 KPI 피드 + SQLite 영속화"""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from .base_agent import BaseAgent, StageResult

# SQLite KPI 스토어 — 재시작 후에도 KPI 이력 유지
_KPI_DB_PATH = Path(__file__).parent.parent / "data" / "kpi_store.db"
_KPI_DB_PATH.parent.mkdir(exist_ok=True)


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_KPI_DB_PATH), check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kpi_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tech_id     TEXT NOT NULL,
            kpi_key     TEXT NOT NULL,
            value       REAL NOT NULL,
            recorded_at TEXT NOT NULL,
            source      TEXT DEFAULT 'manual',
            note        TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kpi_tech ON kpi_events(tech_id, kpi_key)")
    conn.commit()
    return conn


def record_kpi_event(tech_id: str, kpi_key: str, value: float,
                     source: str = "manual", note: str = "") -> int:
    """KPI 이벤트 단건 기록 → row_id 반환"""
    conn = _get_db()
    cur = conn.execute(
        "INSERT INTO kpi_events (tech_id, kpi_key, value, recorded_at, source, note) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (tech_id, kpi_key, value, datetime.utcnow().isoformat(), source, note),
    )
    conn.commit()
    return cur.lastrowid


def get_kpi_feed(tech_id: str, limit: int = 50) -> list[dict]:
    """tech_id의 최근 KPI 이벤트 목록 (최신순)"""
    conn = _get_db()
    rows = conn.execute(
        "SELECT id, kpi_key, value, recorded_at, source, note "
        "FROM kpi_events WHERE tech_id=? ORDER BY id DESC LIMIT ?",
        (tech_id, limit),
    ).fetchall()
    return [
        {"id": r[0], "kpi_key": r[1], "value": r[2],
         "recorded_at": r[3], "source": r[4], "note": r[5]}
        for r in rows
    ]


def get_latest_kpis(tech_id: str) -> dict[str, float]:
    """tech_id의 KPI별 최신 값 딕셔너리"""
    conn = _get_db()
    rows = conn.execute(
        "SELECT kpi_key, value FROM kpi_events WHERE tech_id=? "
        "AND id IN (SELECT MAX(id) FROM kpi_events WHERE tech_id=? GROUP BY kpi_key)",
        (tech_id, tech_id),
    ).fetchall()
    return {r[0]: r[1] for r in rows}


class PerformanceTracker(BaseAgent):
    stage_id = "G10"
    stage_name = "성과관리·환류"

    _KPI_TARGETS = {
        "revenue_usd": {"target": 1_000_000, "weight": 25},
        "royalty_usd": {"target": 100_000, "weight": 20},
        "investment_raised_usd": {"target": 500_000, "weight": 20},
        "poc_to_commercial_rate_pct": {"target": 30, "weight": 15},
        "tech_utilization_rate_pct": {"target": 70, "weight": 10},
        "new_customers": {"target": 10, "weight": 10},
    }

    def assess(self, input_data: dict) -> StageResult:
        """
        input_data: tech_id (str), tech_name, actuals (dict matching _KPI_TARGETS keys),
                    milestone_achievements (list of {name, target_date, actual_date, status}),
                    portfolio_techs (list), feedback_actions (list),
                    use_kpi_store (bool): True이면 SQLite KPI 스토어의 최신값으로 actuals 보강
        """
        tech_id = input_data.get("tech_id", "")

        # SQLite KPI 스토어 자동 보강
        if input_data.get("use_kpi_store") and tech_id:
            stored = get_latest_kpis(tech_id)
            if stored:
                merged = dict(stored)
                merged.update(input_data.get("actuals", {}))  # 입력값 우선
                input_data = dict(input_data)
                input_data["actuals"] = merged
                input_data["_kpi_store_used"] = True
                input_data["_kpi_store_keys"] = list(stored.keys())

        score = self._score(input_data)
        gate = self._gate_from_score(score)
        output_doc = self._build_output(input_data, score)

        # 평가 완료 후 actuals를 KPI 스토어에 자동 기록
        if tech_id:
            for kpi, val in input_data.get("actuals", {}).items():
                try:
                    record_kpi_event(tech_id, kpi, float(val), source="assess")
                except Exception:
                    pass

        return StageResult(
            stage=self.stage_id, score=score, gate=gate,
            output_doc=output_doc,
            next_actions=self._next_actions(gate, input_data),
        )

    def _score(self, d: dict) -> float:
        actuals = d.get("actuals", {})
        score = 0.0
        for kpi, meta in self._KPI_TARGETS.items():
            actual = actuals.get(kpi, 0)
            target = meta["target"]
            weight = meta["weight"]
            achievement = min(actual / max(target, 0.001), 1.5)  # 150% 이상은 상한
            score += weight * achievement
        return round(min(score, 100), 1)

    def _build_output(self, d: dict, score: float) -> dict:
        actuals = d.get("actuals", {})
        kpi_dashboard = []
        for kpi, meta in self._KPI_TARGETS.items():
            actual = actuals.get(kpi, 0)
            target = meta["target"]
            achievement = round(actual / max(target, 0.001) * 100, 1)
            kpi_dashboard.append({
                "kpi": kpi,
                "target": target,
                "actual": actual,
                "achievement_pct": achievement,
                "status": "달성" if achievement >= 100 else "진행중" if achievement >= 50 else "미달",
                "weight": meta["weight"],
            })

        milestones = d.get("milestone_achievements", [])
        on_time = sum(1 for m in milestones if m.get("status") == "completed")

        llm_result = self._llm(
            f"KPI 현황: {kpi_dashboard}\n"
            f"마일스톤: {milestones}\n"
            f"포트폴리오: {d.get('portfolio_techs', [])}\n\n"
            "성과환류 분석과 다음 사이클 전략을 JSON으로:\n"
            '{"performance_diagnosis":"","portfolio_optimization":[],'
            '"next_cycle_focus":[],"discontinue_recommendation":[]}',
            system="기술사업화 성과관리 전문가. JSON만 반환."
        )
        try:
            import json
            analysis = json.loads(llm_result)
        except Exception:
            analysis = {"performance_diagnosis": llm_result}

        return {
            "kpi_dashboard": {
                "as_of": datetime.now().strftime("%Y-%m-%d"),
                "tech_name": d.get("tech_name", ""),
                "overall_score": score,
                "kpis": kpi_dashboard,
                "summary": f"KPI {sum(1 for k in kpi_dashboard if k['status']=='달성')}/{len(kpi_dashboard)}개 달성",
            },
            "milestone_report": {
                "total": len(milestones),
                "on_time": on_time,
                "on_time_rate_pct": round(on_time / max(len(milestones), 1) * 100, 1),
                "milestones": milestones,
            },
            "portfolio_evaluation": {
                "portfolio_techs": d.get("portfolio_techs", []),
                "analysis": analysis.get("portfolio_optimization", []),
                "discontinue_recommendation": analysis.get("discontinue_recommendation", []),
            },
            "feedback_loop": {
                "feedback_actions": d.get("feedback_actions", []),
                "next_cycle_focus": analysis.get("next_cycle_focus", []),
                "retrain_trigger": score < 50,
                "reinvestment_recommendation": score >= 70,
            },
            "performance_diagnosis": analysis.get("performance_diagnosis", ""),
        }

    def _next_actions(self, gate: str, d: dict) -> list[str]:
        if gate == "Go":
            return [
                "스케일업 전략 실행: 추가 시장·고객 확장",
                "성공 레퍼런스 기반 PR·마케팅 강화",
                "후속 기술 사업화 시작 (G0 재진입)",
            ]
        if gate == "Hold":
            return [
                "미달 KPI 개선 계획 수립 (90일 스프린트)",
                "GTM 전략 재검토",
                "핵심 파트너십 강화",
            ]
        return [
            "사업화 종료 또는 전략적 Pivot",
            "잔여 IP 라이선싱 또는 포트폴리오 매각 검토",
        ]
