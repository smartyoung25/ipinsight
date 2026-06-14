"""인증 모듈 단위 테스트"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import pytest
from api.auth import (
    create_access_token,
    _decode_token,
    _hash_pw,
    _verify_pw,
    _validate_bearer,
    authenticate_user,
    _USE_BCRYPT,
)
from fastapi import HTTPException


class TestPasswordHashing:
    def test_hash_returns_string(self):
        h = _hash_pw("password123")
        assert isinstance(h, str)
        assert len(h) > 20

    def test_verify_correct_password(self):
        h = _hash_pw("mypassword")
        assert _verify_pw("mypassword", h) is True

    def test_verify_wrong_password(self):
        h = _hash_pw("mypassword")
        assert _verify_pw("wrongpassword", h) is False

    def test_different_passwords_different_hashes(self):
        h1 = _hash_pw("pass1")
        h2 = _hash_pw("pass2")
        assert h1 != h2

    def test_bcrypt_flag_reflects_availability(self):
        assert isinstance(_USE_BCRYPT, bool)

    def test_hash_is_deterministic_sha256_mode(self):
        """SHA-256 모드에서는 동일 비밀번호 → 동일 해시."""
        if not _USE_BCRYPT:
            h1 = _hash_pw("test123")
            h2 = _hash_pw("test123")
            assert h1 == h2


class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token("user_001")
        payload = _decode_token(token)
        assert payload["sub"] == "user_001"

    def test_token_has_exp(self):
        token = create_access_token("user_002")
        payload = _decode_token(token)
        assert "exp" in payload
        assert payload["exp"] > time.time()

    def test_token_has_role(self):
        token = create_access_token("user_003", role="admin")
        payload = _decode_token(token)
        assert payload["role"] == "admin"

    def test_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            _decode_token("invalid.token.string")
        assert exc_info.value.status_code == 401

    def test_validate_bearer_valid_token(self):
        token = create_access_token("bearer_test")
        result = _validate_bearer(token)
        assert result["sub"] == "bearer_test"

    def test_validate_bearer_invalid_raises(self):
        with pytest.raises(HTTPException):
            _validate_bearer("garbage_token_xxx")


class TestAuthenticateUser:
    def test_valid_credentials(self):
        user = authenticate_user("admin", "admin1234")
        assert user is not None
        assert user["sub"] == "admin"
        assert user["role"] == "admin"

    def test_wrong_password(self):
        user = authenticate_user("admin", "wrongpass")
        assert user is None

    def test_unknown_user(self):
        user = authenticate_user("nouser123", "anypassword")
        assert user is None
