from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .paths import AppPaths, build_paths


class Settings(BaseModel):
    app_name: str = "전기기능사 시퀀스 결선 시뮬레이터"
    version: str = "0.1.0"
    app_mode: Literal["desktop", "web"] = "web"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=0, le=65535)
    debug: bool = False
    allow_lan: bool = False
    allowed_origins: list[str] = Field(default_factory=list)
    paths: AppPaths = Field(default_factory=build_paths)
    static_dir: Path | None = None

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def restrict_host(self):
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
        allowed_origins=origins,
    )
