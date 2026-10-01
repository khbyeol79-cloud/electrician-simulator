from __future__ import annotations

import hmac
from urllib.parse import urlsplit
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from .auth import COOKIE_NAME

PUBLIC_API = {"/api/health", "/api/app-info", "/api/auth/me", "/api/auth/login", "/api/auth/register"}


async def authentication_boundary(request, call_next):
    settings = request.app.state.settings
    if not settings.auth_required or not request.url.path.startswith("/api/"):
        return await call_next(request)
    path = request.url.path
    request.state.account = await run_in_threadpool(
        request.app.state.auth_store.authenticate, request.cookies.get(COOKIE_NAME))
    account = request.state.account
    if path not in PUBLIC_API and account is None:
        return JSONResponse({"detail": "로그인이 필요합니다. 저장 상태를 확인하고 다시 로그인하세요."}, status_code=401,
                            headers={"Cache-Control": "no-store"})
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        # Custom header + strict same-origin policy also prevents login CSRF.
        origin = request.headers.get("origin")
        if origin and (urlsplit(origin).netloc != request.url.netloc or urlsplit(origin).scheme != request.url.scheme):
            return JSONResponse({"detail": "다른 사이트의 요청은 허용하지 않습니다."}, status_code=403)
        if request.headers.get("X-Requested-With") != "ElectricianSimulator":
            return JSONResponse({"detail": "요청 출처를 확인할 수 없습니다."}, status_code=403)
        if path not in {"/api/auth/login", "/api/auth/register"}:
            if not account or not hmac.compare_digest(request.headers.get("X-CSRF-Token", "").encode(), account["csrf"].encode()):
                return JSONResponse({"detail": "로그인 상태가 변경됐습니다. 새로고침 후 다시 확인하세요."}, status_code=403)
    # Old tabs cannot read/write through a different account's new cookie.
    claimed = request.headers.get("X-Session-User")
    if claimed and account and claimed != account["user_id"]:
        return JSONResponse({"detail": "다른 탭에서 사용자가 변경됐습니다. 새로고침하세요."}, status_code=401)
    # Repository reload is server administration, not a student's capability.
    if path.endswith("/reload") and request.method == "POST":
        return JSONResponse({"detail": "기관 모드에서는 서버 관리자가 재시작하여 갱신합니다."}, status_code=403)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
