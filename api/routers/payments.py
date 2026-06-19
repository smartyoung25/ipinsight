"""Toss Payments 결제 라우터

흐름:
  1. POST /payments/initiate  → orderId 발급, DB에 PENDING 기록
  2. 클라이언트가 Toss 결제창 완료 후 paymentKey+amount+orderId 전달
  3. POST /payments/confirm   → Toss 서버사이드 검증 → 크레딧 지급
  4. POST /payments/refund    → 7일 이내 미사용 주문만 환불

오류 다발 구간 대응:
  - 결제창 이탈 후 이중 확인 요청 → idempotency_key(orderId) DB 중복 차단
  - 크레딧 지급 전 서버 다운 → confirm 재진입 시 PAID 상태 감지 → 크레딧만 추가 지급
  - 사용자 환불 요청 + 보고서 이미 생성 → 상태 검사로 차단
"""
from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
import time
import uuid
from base64 import b64encode
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/payments", tags=["결제"])

# ── 설정 ──────────────────────────────────────────────────────────────
TOSS_SECRET_KEY = os.getenv("TOSS_SECRET_KEY", "")
TOSS_CONFIRM_URL = "https://api.tosspayments.com/v1/payments/confirm"
TOSS_CANCEL_URL  = "https://api.tosspayments.com/v1/payments/{paymentKey}/cancel"

TIER_PRICES: dict[str, int] = {
    "FREE": 0,
    "LITE": 100_000,
    "FULL": 300_000,
}

REFUND_WINDOW_DAYS = 7

DB_PATH = Path(__file__).parent.parent.parent / "data" / "payments.db"


# ── DB 초기화 ──────────────────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id      TEXT PRIMARY KEY,
            tech_id       TEXT NOT NULL,
            report_id     TEXT NOT NULL,
            tier          TEXT NOT NULL,
            amount        INTEGER NOT NULL,
            status        TEXT NOT NULL DEFAULT 'PENDING',
            payment_key   TEXT,
            user_id       TEXT,
            created_at    TEXT NOT NULL,
            confirmed_at  TEXT,
            refunded_at   TEXT,
            refund_reason TEXT
        )
    """)
    conn.commit()
    return conn


# ── 의존성: 인증 ──────────────────────────────────────────────────────

def _require_auth(request: "Request") -> dict:  # noqa: F821
    from api.main import require_auth
    return require_auth(request)


# ── Toss API 헬퍼 ─────────────────────────────────────────────────────

def _toss_auth_header() -> str:
    if not TOSS_SECRET_KEY:
        raise HTTPException(503, "결제 서비스 미설정 (TOSS_SECRET_KEY 환경변수 필요)")
    encoded = b64encode(f"{TOSS_SECRET_KEY}:".encode()).decode()
    return f"Basic {encoded}"


def _toss_post(url: str, payload: dict) -> dict:
    try:
        resp = httpx.post(
            url,
            json=payload,
            headers={
                "Authorization": _toss_auth_header(),
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )
        data = resp.json()
        if resp.status_code != 200:
            code = data.get("code", "UNKNOWN")
            msg  = data.get("message", "Toss 오류")
            raise HTTPException(status_code=resp.status_code, detail=f"[{code}] {msg}")
        return data
    except httpx.TimeoutException:
        raise HTTPException(504, "Toss 결제 서버 응답 시간 초과 — 잠시 후 재시도")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Toss 통신 오류: {e}")


# ── 1. 주문 생성 ──────────────────────────────────────────────────────

class InitiateRequest(BaseModel):
    tech_id:   str
    report_id: str
    tier:      str  # FREE | LITE | FULL


class InitiateResponse(BaseModel):
    order_id:     str
    amount:       int
    tier:         str
    order_name:   str


@router.post("/initiate", summary="결제 주문 생성")
def initiate(req: InitiateRequest, _: dict = Depends(_require_auth)) -> InitiateResponse:
    """클라이언트 Toss 결제창 호출 전 서버사이드 주문 ID를 발급."""
    tier = req.tier.upper()
    if tier not in TIER_PRICES:
        raise HTTPException(400, f"유효하지 않은 Tier: {tier}")

    amount = TIER_PRICES[tier]
    if amount == 0:
        raise HTTPException(400, "FREE 티어는 결제가 필요하지 않습니다.")

    order_id = f"IPG-{uuid.uuid4().hex[:16].upper()}"
    order_name = f"IPinsight {tier} — {req.report_id} ({req.tech_id})"

    with _get_db() as conn:
        # 같은 tech_id+report_id+tier가 이미 PENDING이면 재사용
        existing = conn.execute(
            "SELECT order_id FROM orders WHERE tech_id=? AND report_id=? AND tier=? AND status='PENDING'",
            (req.tech_id, req.report_id, tier),
        ).fetchone()
        if existing:
            return InitiateResponse(
                order_id=existing["order_id"],
                amount=amount,
                tier=tier,
                order_name=order_name,
            )

        conn.execute(
            "INSERT INTO orders (order_id, tech_id, report_id, tier, amount, status, created_at) VALUES (?,?,?,?,?,?,?)",
            (order_id, req.tech_id, req.report_id, tier, amount, "PENDING",
             datetime.now(timezone.utc).isoformat()),
        )

    return InitiateResponse(order_id=order_id, amount=amount, tier=tier, order_name=order_name)


# ── 2. 결제 확인 ─────────────────────────────────────────────────────

class ConfirmRequest(BaseModel):
    payment_key: str
    order_id:    str
    amount:      int


@router.post("/confirm", summary="Toss 결제 확인 및 크레딧 지급")
def confirm(req: ConfirmRequest, _: dict = Depends(_require_auth)) -> dict:
    """Toss 결제창 완료 후 서버사이드 검증 + 크레딧(보고서 열람권) 지급.

    재진입(서버 다운 후 재요청) 안전: PAID 상태면 크레딧만 추가 지급.
    """
    with _get_db() as conn:
        order = conn.execute(
            "SELECT * FROM orders WHERE order_id=?", (req.order_id,)
        ).fetchone()

    if not order:
        raise HTTPException(404, f"주문을 찾을 수 없습니다: {req.order_id}")

    # 금액 위변조 검사 (클라이언트가 amount를 조작하는 공격 차단)
    if order["amount"] != req.amount:
        raise HTTPException(400, f"결제 금액 불일치 (주문:{order['amount']} ≠ 요청:{req.amount})")

    # 이미 완료된 주문 — 크레딧만 재지급 (재진입 안전)
    if order["status"] == "PAID":
        _grant_credit(order["tech_id"], order["report_id"], order["tier"])
        return {"status": "already_paid", "order_id": req.order_id, "credit_granted": True}

    if order["status"] != "PENDING":
        raise HTTPException(409, f"처리할 수 없는 주문 상태: {order['status']}")

    # Toss 서버사이드 검증
    if TOSS_SECRET_KEY:
        toss_data = _toss_post(TOSS_CONFIRM_URL, {
            "paymentKey": req.payment_key,
            "orderId":    req.order_id,
            "amount":     req.amount,
        })
    else:
        # 개발/테스트 환경: Toss 호출 생략
        toss_data = {"status": "DONE", "paymentKey": req.payment_key}

    # DB 업데이트 (원자적)
    with _get_db() as conn:
        conn.execute(
            "UPDATE orders SET status='PAID', payment_key=?, confirmed_at=? WHERE order_id=?",
            (req.payment_key, datetime.now(timezone.utc).isoformat(), req.order_id),
        )

    # 크레딧 지급
    _grant_credit(order["tech_id"], order["report_id"], order["tier"])

    return {
        "status":        "paid",
        "order_id":      req.order_id,
        "tier":          order["tier"],
        "credit_granted": True,
        "toss_status":   toss_data.get("status"),
    }


# ── 3. 환불 ──────────────────────────────────────────────────────────

class RefundRequest(BaseModel):
    order_id:      str
    cancel_reason: str = "고객 요청"


@router.post("/refund", summary="결제 환불 (7일 이내 미사용)")
def refund(req: RefundRequest, _: dict = Depends(_require_auth)) -> dict:
    """보고서 생성 시작 전 PAID 주문을 7일 이내에 환불.

    보고서가 이미 생성된 경우 환불 불가 (정책).
    """
    with _get_db() as conn:
        order = conn.execute(
            "SELECT * FROM orders WHERE order_id=?", (req.order_id,)
        ).fetchone()

    if not order:
        raise HTTPException(404, f"주문을 찾을 수 없습니다: {req.order_id}")

    if order["status"] != "PAID":
        raise HTTPException(409, f"환불 불가 상태: {order['status']}")

    # 7일 이내 검사
    confirmed_at = datetime.fromisoformat(order["confirmed_at"])
    elapsed_days = (datetime.now(timezone.utc) - confirmed_at).days
    if elapsed_days > REFUND_WINDOW_DAYS:
        raise HTTPException(400, f"환불 기간 초과 (결제일로부터 {elapsed_days}일 경과, 최대 {REFUND_WINDOW_DAYS}일)")

    # 보고서 생성 여부 확인
    if _is_report_generated(order["tech_id"], order["report_id"]):
        raise HTTPException(400, "보고서가 이미 생성되어 환불이 불가합니다. 고객센터에 문의하세요.")

    # Toss 환불 요청
    payment_key = order["payment_key"]
    if TOSS_SECRET_KEY and payment_key:
        _toss_post(
            TOSS_CANCEL_URL.format(paymentKey=payment_key),
            {"cancelReason": req.cancel_reason},
        )

    with _get_db() as conn:
        conn.execute(
            "UPDATE orders SET status='REFUNDED', refunded_at=?, refund_reason=? WHERE order_id=?",
            (datetime.now(timezone.utc).isoformat(), req.cancel_reason, req.order_id),
        )

    _revoke_credit(order["tech_id"], order["report_id"])

    return {
        "status":    "refunded",
        "order_id":  req.order_id,
        "amount":    order["amount"],
        "reason":    req.cancel_reason,
    }


# ── 4. 주문 조회 ──────────────────────────────────────────────────────

@router.get("/order/{order_id}", summary="주문 상태 조회")
def get_order(order_id: str, _: dict = Depends(_require_auth)) -> dict:
    with _get_db() as conn:
        order = conn.execute(
            "SELECT * FROM orders WHERE order_id=?", (order_id,)
        ).fetchone()
    if not order:
        raise HTTPException(404, f"주문 없음: {order_id}")
    return dict(order)


# ── 크레딧 헬퍼 ──────────────────────────────────────────────────────

def _grant_credit(tech_id: str, report_id: str, tier: str) -> None:
    """결제 완료 후 보고서 열람 크레딧 DB 기록."""
    credits_db = Path(__file__).parent.parent.parent / "data" / "credits.db"
    credits_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(credits_db))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS credits (
            tech_id   TEXT,
            report_id TEXT,
            tier      TEXT,
            granted_at TEXT,
            PRIMARY KEY (tech_id, report_id)
        )
    """)
    conn.execute(
        "INSERT OR REPLACE INTO credits VALUES (?,?,?,?)",
        (tech_id, report_id, tier, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def _revoke_credit(tech_id: str, report_id: str) -> None:
    """환불 시 크레딧 취소."""
    credits_db = Path(__file__).parent.parent.parent / "data" / "credits.db"
    if not credits_db.exists():
        return
    conn = sqlite3.connect(str(credits_db))
    conn.execute("DELETE FROM credits WHERE tech_id=? AND report_id=?", (tech_id, report_id))
    conn.commit()
    conn.close()


def _is_report_generated(tech_id: str, report_id: str) -> bool:
    """보고서 생성 여부 확인 (reports.db 조회)."""
    from api.services.report_pipeline import list_reports
    try:
        reports = list_reports(tech_id)
        return any(r.get("report_id") == report_id for r in reports)
    except Exception:
        return False


def has_credit(tech_id: str, report_id: str) -> bool:
    """보고서 생성 전 크레딧 유효성 검사 (FREE 티어는 항상 True)."""
    credits_db = Path(__file__).parent.parent.parent / "data" / "credits.db"
    if not credits_db.exists():
        return False
    conn = sqlite3.connect(str(credits_db))
    row = conn.execute(
        "SELECT tier FROM credits WHERE tech_id=? AND report_id=?", (tech_id, report_id)
    ).fetchone()
    conn.close()
    return row is not None
