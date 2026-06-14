"""Slack Webhook 알림 서비스 — 오류·경고·일일 요약 발송
SLACK_WEBHOOK_URL 환경변수 미설정 시 조용히 스킵 (no-op).
"""
from __future__ import annotations
import json
import os
import urllib.request
from datetime import datetime, timezone

_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")


def _post(payload: dict) -> bool:
    """Slack incoming webhook POST. 실패해도 예외 미전파."""
    if not _WEBHOOK_URL:
        return False
    try:
        data = json.dumps(payload, ensure_ascii=False).encode()
        req = urllib.request.Request(
            _WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def _now_utc() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def alert_error(stage: str, error: str, tech_id: str = "") -> bool:
    """G-스테이지 실행 오류 알림"""
    return _post({
        "text": "🚨 *IPInsight 오류*",
        "attachments": [{
            "color": "danger",
            "fields": [
                {"title": "스테이지", "value": stage,          "short": True},
                {"title": "기술 ID",  "value": tech_id or "-", "short": True},
                {"title": "오류",     "value": error[:500]},
            ],
            "footer": f"IPInsight · {_now_utc()}",
        }],
    })


def alert_warn(message: str, detail: str = "") -> bool:
    """경고 알림 (폴백 작동, API 한도 근접 등)"""
    return _post({
        "text": f"⚠️ *IPInsight 경고*: {message}",
        "attachments": [{
            "color": "warning",
            "text":  detail[:300],
            "footer": _now_utc(),
        }] if detail else [],
    })


def alert_connector_down(connector: str, error: str) -> bool:
    """커넥터 장애 알림 (EPO·FDA·OWID 등)"""
    return _post({
        "text": f"🔌 *커넥터 장애*: `{connector}`",
        "attachments": [{
            "color": "warning",
            "fields": [
                {"title": "커넥터", "value": connector,       "short": True},
                {"title": "오류",   "value": error[:200],     "short": False},
            ],
            "footer": f"IPInsight · {_now_utc()}",
        }],
    })


def alert_daily_summary(total_requests: int, error_count: int, avg_latency_ms: float) -> bool:
    """일일 운영 요약 알림"""
    color = "good" if error_count == 0 else ("warning" if error_count < 5 else "danger")
    return _post({
        "text": "📊 *IPInsight 일일 요약*",
        "attachments": [{
            "color": color,
            "fields": [
                {"title": "총 요청",   "value": str(total_requests),          "short": True},
                {"title": "오류",      "value": str(error_count),             "short": True},
                {"title": "평균 응답", "value": f"{avg_latency_ms:.0f}ms",    "short": True},
            ],
            "footer": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
        }],
    })
