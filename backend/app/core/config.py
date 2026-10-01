from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .paths import AppPaths, build_paths


class Settings(BaseModel):
    app_name: str = "전기기능사 시퀀스 결선 시뮬레이터"
    version: str = "0.13.0"
    app_mode: Literal["desktop", "web"] = "web"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=0, le=65535)
    debug: bool = False
    allow_lan: bool = False
    auth_required: bool = False
    service_managed: bool = False
    registration_open: bool = True
    auth_cookie_secure: bool = False
    auth_idle_seconds: int = Field(default=1800, ge=300, le=36000)
    auth_lifetime_seconds: int = Field(default=36000, ge=1800, le=86400)
    allowed_origins: list[str] = Field(default_factory=list)
    paths: AppPaths = Field(default_factory=build_paths)
    static_dir: Path | None = None

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def restrict_host(self):
        if self.allow_lan:
            self.auth_required = True
        if self.auth_required and self.allowed_origins:
            raise ValueError("계정 모드는 동일 출처만 허용합니다. ALLOWED_ORIGINS를 비우세요.")
        if self.auth_required and self.paths.writable_root.resolve().is_relative_to(self.resolved_static_dir.resolve()):
            raise ValueError("계정 데이터는 공개 정적 웹 폴더(frontend/dist) 안에 저장할 수 없습니다.")
        if self.host == "0.0.0.0" and not self.allow_lan:
            self.host = "127.0.0.1"
        if self.app_mode == "desktop":
            self.host = "127.0.0.1"
        return self

    @property
    def resolved_static_dir(self) -> Path:
        return self.static_dir or self.paths.frontend_dist


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    mode = os.getenv("APP_MODE", "web").lower()
    if mode not in {"desktop", "web"}:
        mode = "web"
    allow_lan = _as_bool(os.getenv("ALLOW_LAN"))
    default_host = "0.0.0.0" if allow_lan and mode == "web" else "127.0.0.1"
    origins = [
        item.strip()
        for item in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if item.strip()
    ]
    return Settings(
        app_mode=mode,
        host=os.getenv("APP_HOST", default_host),
        port=int(os.getenv("APP_PORT", "8000")),
        debug=_as_bool(os.getenv("APP_DEBUG")),
        allow_lan=allow_lan,
        auth_required=_as_bool(os.getenv("AUTH_REQUIRED")),
        registration_open=_as_bool(os.getenv("REGISTRATION_OPEN"), default=True),
        auth_cookie_secure=_as_bool(os.getenv("AUTH_COOKIE_SECURE")),
        auth_idle_seconds=int(os.getenv("AUTH_IDLE_SECONDS", "1800")),
        auth_lifetime_seconds=int(os.getenv("AUTH_LIFETIME_SECONDS", "36000")),
        allowed_origins=origins,
    )
