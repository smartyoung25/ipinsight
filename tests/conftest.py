"""pytest 픽스처 — TestClient + 인증 토큰"""
from __future__ import annotations
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="session")
def auth_token(client):
    """admin/admin1234 로 JWT 발급 (개발 모드에서는 토큰 없이도 동작)."""
    resp = client.post("/auth/token", json={"username": "admin", "password": "admin1234"})
    if resp.status_code == 200:
        return resp.json()["access_token"]
    return ""  # 개발 모드 (JWT_SECRET_KEY 미설정) — 토큰 불필요


@pytest.fixture
def auth_headers(auth_token):
    if auth_token:
        return {"Authorization": f"Bearer {auth_token}"}
    return {}
