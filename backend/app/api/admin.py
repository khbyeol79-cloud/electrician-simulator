from __future__ import annotations

import shutil
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator
from app.core.auth import MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH

from app.core.service_admin import NetworkOptions, lan_addresses, registration_open


def require_admin(request: Request):
    settings = request.app.state.settings
    account = getattr(request.state, "account", None)
    if not settings.auth_required:
        raise HTTPException(404, "계정 서비스에서만 서버 관리를 사용할 수 있습니다.")
    if account is None or not request.app.state.auth_store.is_admin(account["user_id"]):
        raise HTTPException(403, "서버 관리자만 사용할 수 있습니다.")
    return account


router = APIRouter(prefix="/api/admin", tags=["administration"], dependencies=[Depends(require_admin)])


class RegistrationOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: StrictBool


class PasswordReset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    admin_password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH, repr=False)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH, repr=False)
    confirmation: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH, repr=False)

    @model_validator(mode="after")
    def matching(self):
        if self.new_password != self.confirmation:
            raise ValueError("비밀번호 확인이 일치하지 않습니다.")
        return self


@router.get("/status")
def status(request: Request):
    settings, store = request.app.state.settings, request.app.state.auth_store
    root = settings.paths.writable_root
    disk = shutil.disk_usage(root)
    accounts = store.managed_accounts()
    network = {"host": settings.host, "port": settings.port}
    # Raw uvicorn CLI options can differ from application Settings. Show the
    # accepted connection's actual local socket, not an invented bind address.
    socket_address = request.scope.get("server")
    if not settings.service_managed:
        network = {"host": socket_address[0], "port": socket_address[1]} if socket_address else None
    saved = store.service_option("network")
    return {
        "version": settings.version,
        "uptime_seconds": int(time.monotonic() - request.app.state.started_monotonic),
        "database_ready": request.app.state.database_ready,
        "service_managed": settings.service_managed,
        "current_network": network,
        "saved_network": saved,
        "restart_required": saved is not None and (not settings.service_managed or saved != network),
        "lan_addresses": lan_addresses(),
        "registration_open": registration_open(request),
        "account_count": len(accounts),
        "active_sessions": sum(a["active_sessions"] for a in accounts),
        "data_directory": str(root),
        "disk_free_bytes": disk.free, "disk_total_bytes": disk.total,
        "secure_cookie": settings.auth_cookie_secure,
        "audit": store.audit_events(),
    }


@router.get("/accounts")
def accounts(request: Request):
    return request.app.state.auth_store.managed_accounts()


@router.put("/registration")
def update_registration(payload: RegistrationOptions, request: Request):
    request.app.state.auth_store.save_service_option("registration_open", payload.enabled, request.state.account["username"])
    return {"registration_open": registration_open(request)}


@router.put("/network")
def update_network(payload: NetworkOptions, request: Request):
    if not request.app.state.settings.service_managed:
        raise HTTPException(409, "scripts/run_service.py로 실행해야 주소·포트 설정을 저장할 수 있습니다.")
    request.app.state.auth_store.save_service_option("network", payload.model_dump(), request.state.account["username"])
    return {"saved_network": payload.model_dump(), "applies_after_restart": True}


@router.post("/accounts/{user_id}/logout")
def logout_account(user_id: str, request: Request):
    if user_id == request.state.account["user_id"]:
        raise HTTPException(400, "본인 계정은 상단 사용자 메뉴에서 로그아웃하세요.")
    request.app.state.auth_store.revoke_user_sessions(user_id, request.state.account["username"])
    return {"logged_out": True}


@router.post("/accounts/{user_id}/reset-password")
def reset_password(user_id: str, payload: PasswordReset, request: Request):
    actor = request.state.account["user_id"]
    request.app.state.auth_store.admin_reset_password(user_id, payload.new_password, actor, payload.admin_password)
    return {"reset": True, "reauthenticate": user_id == actor}
