"""결제 라우터 단위 테스트 — Toss API mock, DB in-memory"""
import sys
import sqlite3
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

sys.path.insert(0, "C:/IPinsight")


# ── 헬퍼 픽스처 ───────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    """payments.db / credits.db를 임시 경로로 교체."""
    monkeypatch.setattr(
        "api.routers.payments.DB_PATH",
        tmp_path / "payments.db",
    )
    # credits.db도 tmp_path 하위로
    monkeypatch.setattr(
        "api.routers.payments.Path",
        lambda *a: tmp_path / Path(*a).name if "credits" in str(Path(*a)) else Path(*a),
    )
    yield


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr("api.routers.payments.DB_PATH", tmp_path / "payments.db")
    from api.routers.payments import _get_db
    return _get_db


# ── Initiate ──────────────────────────────────────────────────────────

def test_initiate_lite(tmp_path, monkeypatch):
    monkeypatch.setattr("api.routers.payments.DB_PATH", tmp_path / "payments.db")
    from api.routers.payments import initiate, InitiateRequest
    req = InitiateRequest(tech_id="T001", report_id="R1_investment", tier="LITE")
    resp = initiate(req, _={})
    assert resp.amount == 100_000
    assert resp.order_id.startswith("IPG-")


def test_initiate_full(tmp_path, monkeypatch):
    monkeypatch.setattr("api.routers.payments.DB_PATH", tmp_path / "payments.db")
    from api.routers.payments import initiate, InitiateRequest
    req = InitiateRequest(tech_id="T001", report_id="R1_investment", tier="FULL")
    resp = initiate(req, _={})
    assert resp.amount == 300_000


def test_initiate_free_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr("api.routers.payments.DB_PATH", tmp_path / "payments.db")
    from api.routers.payments import initiate, InitiateRequest
    from fastapi import HTTPException
    req = InitiateRequest(tech_id="T001", report_id="R1_investment", tier="FREE")
    with pytest.raises(HTTPException) as exc:
        initiate(req, _={})
    assert exc.value.status_code == 400


def test_initiate_idempotent(tmp_path, monkeypatch):
    """같은 주문 PENDING 중 재요청 시 기존 order_id 반환."""
    monkeypatch.setattr("api.routers.payments.DB_PATH", tmp_path / "payments.db")
    from api.routers.payments import initiate, InitiateRequest
    req = InitiateRequest(tech_id="T001", report_id="R1_investment", tier="LITE")
    r1 = initiate(req, _={})
    r2 = initiate(req, _={})
    assert r1.order_id == r2.order_id


# ── Confirm ───────────────────────────────────────────────────────────

def test_confirm_no_toss_key(tmp_path, monkeypatch):
    """TOSS_SECRET_KEY 없을 때 개발모드로 PAID 처리."""
    monkeypatch.setattr("api.routers.payments.DB_PATH", tmp_path / "payments.db")
    monkeypatch.setattr("api.routers.payments.TOSS_SECRET_KEY", "")
    monkeypatch.setattr("api.routers.payments._grant_credit", lambda *a: None)

    from api.routers.payments import initiate, confirm, InitiateRequest, ConfirmRequest
    order = initiate(InitiateRequest(tech_id="T001", report_id="R1", tier="LITE"), _={})
    result = confirm(ConfirmRequest(
        payment_key="test_key", order_id=order.order_id, amount=100_000
    ), _={})
    assert result["status"] == "paid"
    assert result["credit_granted"] is True


def test_confirm_amount_mismatch(tmp_path, monkeypatch):
    """금액 위변조 시 400 반환."""
    monkeypatch.setattr("api.routers.payments.DB_PATH", tmp_path / "payments.db")
    monkeypatch.setattr("api.routers.payments.TOSS_SECRET_KEY", "")
    from api.routers.payments import initiate, confirm, InitiateRequest, ConfirmRequest
    from fastapi import HTTPException
    order = initiate(InitiateRequest(tech_id="T001", report_id="R1", tier="LITE"), _={})
    with pytest.raises(HTTPException) as exc:
        confirm(ConfirmRequest(
            payment_key="key", order_id=order.order_id, amount=1  # 조작된 금액
        ), _={})
    assert exc.value.status_code == 400


def test_confirm_reentrant(tmp_path, monkeypatch):
    """PAID 상태 재진입 시 크레딧 재지급 후 already_paid 반환."""
    monkeypatch.setattr("api.routers.payments.DB_PATH", tmp_path / "payments.db")
    monkeypatch.setattr("api.routers.payments.TOSS_SECRET_KEY", "")
    monkeypatch.setattr("api.routers.payments._grant_credit", lambda *a: None)

    from api.routers.payments import initiate, confirm, InitiateRequest, ConfirmRequest
    order = initiate(InitiateRequest(tech_id="T001", report_id="R1", tier="LITE"), _={})
    req = ConfirmRequest(payment_key="key", order_id=order.order_id, amount=100_000)
    confirm(req, _={})
    result = confirm(req, _={})  # 재진입
    assert result["status"] == "already_paid"


# ── Refund ────────────────────────────────────────────────────────────

def test_refund_success(tmp_path, monkeypatch):
    monkeypatch.setattr("api.routers.payments.DB_PATH", tmp_path / "payments.db")
    monkeypatch.setattr("api.routers.payments.TOSS_SECRET_KEY", "")
    monkeypatch.setattr("api.routers.payments._grant_credit", lambda *a: None)
    monkeypatch.setattr("api.routers.payments._revoke_credit", lambda *a: None)
    monkeypatch.setattr("api.routers.payments._is_report_generated", lambda *a: False)

    from api.routers.payments import initiate, confirm, refund, InitiateRequest, ConfirmRequest, RefundRequest
    order = initiate(InitiateRequest(tech_id="T001", report_id="R1", tier="LITE"), _={})
    confirm(ConfirmRequest(payment_key="key", order_id=order.order_id, amount=100_000), _={})
    result = refund(RefundRequest(order_id=order.order_id, cancel_reason="테스트"), _={})
    assert result["status"] == "refunded"


def test_refund_blocked_report_generated(tmp_path, monkeypatch):
    """보고서가 이미 생성된 경우 환불 차단."""
    monkeypatch.setattr("api.routers.payments.DB_PATH", tmp_path / "payments.db")
    monkeypatch.setattr("api.routers.payments.TOSS_SECRET_KEY", "")
    monkeypatch.setattr("api.routers.payments._grant_credit", lambda *a: None)
    monkeypatch.setattr("api.routers.payments._is_report_generated", lambda *a: True)

    from api.routers.payments import initiate, confirm, refund, InitiateRequest, ConfirmRequest, RefundRequest
    from fastapi import HTTPException
    order = initiate(InitiateRequest(tech_id="T001", report_id="R1", tier="LITE"), _={})
    confirm(ConfirmRequest(payment_key="key", order_id=order.order_id, amount=100_000), _={})
    with pytest.raises(HTTPException) as exc:
        refund(RefundRequest(order_id=order.order_id), _={})
    assert exc.value.status_code == 400
    assert "보고서" in exc.value.detail


def test_refund_pending_order_rejected(tmp_path, monkeypatch):
    """PENDING(미결제) 주문 환불 요청 차단."""
    monkeypatch.setattr("api.routers.payments.DB_PATH", tmp_path / "payments.db")
    from api.routers.payments import initiate, refund, InitiateRequest, RefundRequest
    from fastapi import HTTPException
    order = initiate(InitiateRequest(tech_id="T001", report_id="R1", tier="LITE"), _={})
    with pytest.raises(HTTPException) as exc:
        refund(RefundRequest(order_id=order.order_id), _={})
    assert exc.value.status_code == 409
