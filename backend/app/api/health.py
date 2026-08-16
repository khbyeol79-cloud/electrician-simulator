from __future__ import annotations

from fastapi import APIRouter, Request


router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health(request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "version": settings.version,
    }


@router.get("/app-info")
def app_info(request: Request) -> dict[str, str | bool]:
    settings = request.app.state.settings
    return {
        "app_name": settings.app_name,
        "version": settings.version,
        "mode": settings.app_mode,
        "database_ready": bool(request.app.state.database_ready),
        "problems_path_ready": settings.paths.problems_dir.is_dir(),
    }

