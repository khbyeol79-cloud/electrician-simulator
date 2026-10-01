from __future__ import annotations

import unicodedata
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.core.auth import COOKIE_NAME, MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH
from app.core.service_admin import registration_open

router = APIRouter(prefix="/api/auth", tags=["account"])


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(pattern=r"^[A-Za-z0-9_]{4,24}$")
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH, repr=False)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value):
        return value.lower()


class Register(Login):
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH, repr=False)
    nickname: str = Field(min_length=2, max_length=20)

    @field_validator("nickname")
    @classmethod
    def normalize_nickname(cls, value):
        value = unicodedata.normalize("NFKC", value).strip()
        if not 2 <= len(value) <= 20 or any(unicodedata.category(c).startswith("C") for c in value):
            raise ValueError("닉네임은 2~20자의 표시 가능한 문자로 입력하세요.")
        return value


def _store(request):
    if not request.app.state.settings.auth_required:
        raise HTTPException(404, "계정 서비스가 활성화되지 않았습니다.")
    return request.app.state.auth_store


def _limit(request, username):
    store = _store(request)
    peer = request.client.host if request.client else "unknown"
    store.rate_limit("ip:" + peer, 120)
    store.rate_limit("login:" + username, 15)


def _session(request, response, account):
    token, csrf = _store(request).create_session(account["user_id"], request.cookies.get(COOKIE_NAME))
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="strict", path="/",
                        secure=request.app.state.settings.auth_cookie_secure)
    response.headers["Cache-Control"] = "no-store"
    return {"required": True, "user": account, "csrf_token": csrf,
            "is_admin": _store(request).is_admin(account["user_id"]),
            "registration_open": registration_open(request)}


@router.get("/me")
def me(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    settings = request.app.state.settings
    account = getattr(request.state, "account", None)
    return {"required": settings.auth_required,
            "user": {k: account[k] for k in ("user_id", "username", "nickname")} if account else None,
            "csrf_token": account["csrf"] if account else None,
            "is_admin": bool(account and request.app.state.auth_store.is_admin(account["user_id"])),
            "registration_open": registration_open(request)}


@router.post("/register", status_code=201)
def register(payload: Register, request: Request, response: Response):
    _limit(request, payload.username)
    if not registration_open(request):
        raise HTTPException(403, "현재 신규 회원가입이 닫혀 있습니다. 관리자에게 문의하세요.")
    account = _store(request).register(payload.username, payload.nickname, payload.password)
    return _session(request, response, account)


@router.post("/login")
def login(payload: Login, request: Request, response: Response):
    _limit(request, payload.username)
    return _session(request, response, _store(request).login(payload.username, payload.password))


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response):
    _store(request).logout(request.cookies.get(COOKIE_NAME))
    response.delete_cookie(COOKIE_NAME, path="/", secure=request.app.state.settings.auth_cookie_secure,
                           httponly=True, samesite="strict")
