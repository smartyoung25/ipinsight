"""요청 로깅 + 메트릭 + POST 전역 인증 게이트 미들웨어"""
from __future__ import annotations
import json, logging, os, time
from collections import deque
from fastapi import Request
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format='{"t":"%(asctime)s","lvl":"%(levelname)s","msg":%(message)s}',
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("ipinsight")

_m = {
    "n": 0,           # 총 요청수
    "err": 0,         # 4xx/5xx
    "ms_total": 0.0,  # 누적 응답시간
    "recent": deque(maxlen=200),
}


async def logging_middleware(request: Request, call_next):
    t0 = time.time()
    response = await call_next(request)
    ms = round((time.time() - t0) * 1000, 1)

    _m["n"]        += 1
    _m["ms_total"] += ms
    if response.status_code >= 400:
        _m["err"] += 1

    entry = {
        "path":   request.url.path,
        "method": request.method,
        "status": response.status_code,
        "ms":     ms,
        "t":      time.strftime("%H:%M:%S"),
    }
    _m["recent"].append(entry)
    log.info(json.dumps(entry, ensure_ascii=False))
    return response


def get_metrics() -> dict:
    n = max(_m["n"], 1)
    return {
        "requests":    _m["n"],
        "errors":      _m["err"],
        "error_rate":  round(_m["err"] / n * 100, 2),
        "avg_ms":      round(_m["ms_total"] / n, 1),
        "recent_10":   list(_m["recent"])[-10:],
    }


# ── POST 전역 인증 게이트 ──────────────────────────────────────
# 공개 경로: 인증 없이 접근 가능
_PUBLIC_PATHS = frozenset([
    "/auth/token",
    "/health",
    "/stages",
    "/demo/sample-input",
    "/docs",
    "/openapi.json",
    "/redoc",
])


async def post_auth_gate(request: Request, call_next):
    """모든 POST 요청에 Bearer 인증 강제.
    JWT_SECRET_KEY 또는 ADMIN_API_KEY 미설정 시 개발 모드(자동 통과).
    """
    if request.method != "POST" or request.url.path in _PUBLIC_PATHS:
        return await call_next(request)

    # 개발 모드: 인증 환경변수 모두 미설정 → 자동 통과
    if (
        not os.environ.get("JWT_SECRET_KEY")
        and not os.environ.get("ADMIN_API_KEY")
        and os.environ.get("AUTH_DISABLED", "").lower() not in ("1", "true")
    ):
        return await call_next(request)

    # AUTH_DISABLED=1 → 무조건 통과
    if os.environ.get("AUTH_DISABLED", "").lower() in ("1", "true"):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={
                "code": 401,
                "message": "인증 필요",
                "detail": "Authorization: Bearer <token> 헤더를 추가하세요. POST /auth/token 으로 발급.",
            },
        )

    token = auth_header[7:]
    try:
        from api.auth import _validate_bearer
        _validate_bearer(token)
    except Exception as e:
        return JSONResponse(
            status_code=401,
            content={"code": 401, "message": "토큰 검증 실패", "detail": str(e)},
        )

    return await call_next(request)
