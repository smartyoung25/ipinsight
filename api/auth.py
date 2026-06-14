"""JWT Bearer 인증 + API Key 게이트
환경변수:
  JWT_SECRET_KEY  — 서명 키 (미설정 시 dev 자동 키 + 경고)
  ADMIN_API_KEY   — 정적 API Key (헤더 Bearer <key>)
  AUTH_DISABLED   — "1" 설정 시 인증 완전 비활성 (로컬 개발용)
"""
from __future__ import annotations
import os, time, secrets, logging
from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

log = logging.getLogger("ipinsight.auth")

_SECRET     = os.environ.get("JWT_SECRET_KEY") or secrets.token_hex(32)
_ALGORITHM  = "HS256"
_EXPIRES    = int(os.environ.get("JWT_EXPIRE_SECONDS", "1800"))   # 기본 30분
_API_KEY    = os.environ.get("ADMIN_API_KEY", "")
_DISABLED   = os.environ.get("AUTH_DISABLED", "").lower() in ("1", "true", "yes")

if not os.environ.get("JWT_SECRET_KEY"):
    log.warning("JWT_SECRET_KEY 미설정 — 재시작마다 토큰 무효화됨 (운영 환경에 설정 필요)")

bearer_scheme = HTTPBearer(auto_error=False)

# ── passlib bcrypt (선택적, 동작 여부 실측 판정) ──────────────
_USE_BCRYPT = False
_pwd_ctx = None
try:
    from passlib.context import CryptContext as _CC
    _pwd_ctx = _CC(schemes=["bcrypt"], deprecated="auto")
    _pwd_ctx.hash("probe")          # 실제 해싱 시도 — 버전 충돌 시 여기서 예외
    _USE_BCRYPT = True
except Exception as _bcrypt_err:
    _pwd_ctx = None
    log.warning(f"bcrypt 비활성 ({_bcrypt_err.__class__.__name__}) — SHA-256 폴백. "
                "pip install --upgrade bcrypt passlib 로 해결")

# ── jose 선택적 사용 ──────────────────────────────────────────
try:
    from jose import jwt as _jose_jwt, JWTError as _JWTError
    _USE_JOSE = True
except ImportError:
    _USE_JOSE = False
    log.warning("python-jose 미설치 — HMAC 폴백 사용 (pip install python-jose[cryptography])")


def create_access_token(sub: str, role: str = "user") -> str:
    """JWT 발급. jose 미설치 시 단순 HMAC 폴백."""
    payload = {
        "sub":  sub,
        "role": role,
        "iat":  int(time.time()),
        "exp":  int(time.time()) + _EXPIRES,
    }
    if _USE_JOSE:
        return _jose_jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)

    import base64, json, hmac, hashlib
    hdr  = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    sig  = base64.urlsafe_b64encode(
        hmac.new(_SECRET.encode(), f"{hdr}.{body}".encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{hdr}.{body}.{sig}"


def _decode_token(token: str) -> dict:
    if _USE_JOSE:
        try:
            return _jose_jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
        except _JWTError as e:
            raise HTTPException(status_code=401, detail=f"토큰 검증 실패: {e}")

    import base64, json, hmac, hashlib
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="잘못된 토큰 형식")
    pad  = 4 - len(parts[1]) % 4
    body = base64.urlsafe_b64decode(parts[1] + "=" * (pad % 4))
    payload = json.loads(body)
    if payload.get("exp", 0) < time.time():
        raise HTTPException(status_code=401, detail="토큰 만료")
    return payload


def require_auth(
    cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    """모든 쓰기 엔드포인트의 인증 의존성.
    AUTH_DISABLED=1 또는 JWT_SECRET_KEY+ADMIN_API_KEY 모두 미설정 시 통과 (dev 모드).
    """
    if _DISABLED:
        return {"sub": "dev", "role": "admin", "mode": "disabled"}

    # 환경변수 미설정 = 개발 모드 (자동 통과)
    if not os.environ.get("JWT_SECRET_KEY") and not _API_KEY:
        return {"sub": "dev", "role": "admin", "mode": "no_auth_env"}

    if not cred:
        raise HTTPException(
            status_code=401,
            detail="인증 필요 — Authorization: Bearer <token> 헤더를 추가하세요. POST /auth/token 으로 발급.",
        )
    token = cred.credentials

    if _API_KEY and token == _API_KEY:
        return {"sub": "api_key_user", "role": "admin", "mode": "api_key"}

    return _decode_token(token)


# ── 사용자 저장소 (파일 기반, 운영 시 DB 교체) ────────────────
import json
from pathlib import Path

_USERS_FILE = Path(__file__).parent / "data" / "users.json"


def _load_users() -> dict:
    if _USERS_FILE.exists():
        return json.loads(_USERS_FILE.read_text(encoding="utf-8"))
    # 기본 admin 계정 (최초 기동 시 자동 생성)
    default = {
        "admin": {"password_hash": _hash_pw("admin1234"), "role": "admin"},
    }
    _USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _USERS_FILE.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")
    log.warning("기본 계정 생성: admin / admin1234 — 운영 환경에서 반드시 변경")
    return default


def _hash_pw(pw: str) -> str:
    """bcrypt 해시 (passlib 설치 시). 미설치 시 SHA-256 + 고정 소금 폴백."""
    if _USE_BCRYPT:
        return _pwd_ctx.hash(pw)
    import hashlib
    salt = os.environ.get("JWT_SECRET_KEY") or "ipinsight-default-salt-v1"
    return hashlib.sha256((pw + salt).encode()).hexdigest()


def _verify_pw(plain: str, stored_hash: str) -> bool:
    """bcrypt verify (타이밍 안전). 폴백 시 상수시간 비교."""
    if _USE_BCRYPT:
        try:
            return _pwd_ctx.verify(plain, stored_hash)
        except Exception:
            # 구형 SHA-256 해시가 저장돼 있을 경우 폴백 재검증
            return _verify_pw_sha256(plain, stored_hash)
    return _verify_pw_sha256(plain, stored_hash)


def _verify_pw_sha256(plain: str, stored_hash: str) -> bool:
    import hashlib, hmac
    salt = os.environ.get("JWT_SECRET_KEY") or "ipinsight-default-salt-v1"
    expected = hashlib.sha256((plain + salt).encode()).hexdigest()
    return hmac.compare_digest(expected, stored_hash)


def _validate_bearer(token: str) -> dict:
    """미들웨어에서 직접 호출하는 토큰 검증 헬퍼."""
    api_key = os.environ.get("ADMIN_API_KEY", "")
    if api_key and token == api_key:
        return {"sub": "api_key_user", "role": "admin"}
    return _decode_token(token)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    users = _load_users()
    user  = users.get(username)
    if not user:
        return None
    if not _verify_pw(password, user["password_hash"]):
        return None
    return {"sub": username, "role": user.get("role", "user")}
