from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from .api.auth import router as auth_router
from .api.admin import router as admin_router
from .core.auth import AuthStore, MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH
from .core.auth_middleware import authentication_boundary

from .api.health import router as health_router
from .api.catalog import router as catalog_router
from .api.circuit_analysis import router as circuit_analysis_router
from .api.problems import router as problems_router
from .api.wiring import router as wiring_router
from .api.mounting import router as mounting_router
from .api.operation import router as operation_router, session_router as operation_session_router
from .api.free_circuit import router as free_circuit_router
from .core.config import Settings, load_settings
from .core.exceptions import unhandled_exception_handler
from .core.logging_config import configure_logging
from .core.user_context import UserDatabasePool
from .database import SQLiteDatabase
from .repositories import AnswerRepository, ProblemRepository
from .simulation import OperationSessionManager


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or load_settings()
    logger = configure_logging(app_settings.paths, app_settings.debug)
    database = SQLiteDatabase(app_settings.paths.database_file)
    auth_store = AuthStore(app_settings.paths.writable_root / "accounts.db",
                           idle_seconds=app_settings.auth_idle_seconds,
                           lifetime_seconds=app_settings.auth_lifetime_seconds) if app_settings.auth_required else None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("애플리케이션 시작 | mode=%s", app_settings.app_mode)
        app_settings.paths.ensure_writable_directories()
        if auth_store is not None:
            auth_store.initialize()
        try:
            database.initialize()
            app.state.database_ready = database.is_ready()
        except Exception:
            app.state.database_ready = False
            logger.exception("데이터베이스 초기화 실패")
        try:
            repository = ProblemRepository(
                app_settings.paths.problems_dir,
                app_settings.paths.bundle_root / "schemas",
                app_settings.paths.catalog_dir,
            )
            statistics = repository.reload()
            app.state.problem_repository = repository
            app.state.answer_repository = AnswerRepository(repository)
            logger.info(
                "문제 저장소 준비 | loaded=%s excluded=%s warnings=%s",
                statistics.loaded,
                statistics.excluded,
                statistics.warnings,
            )
        except Exception:
            app.state.problem_repository = None
            app.state.answer_repository = None
            logger.exception("문제 저장소 초기화 실패")
        yield
        logger.info("애플리케이션 종료")

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.version,
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.state.auth_store = auth_store
    app.state.started_monotonic = time.monotonic()
    app.middleware("http")(authentication_boundary)

    @app.exception_handler(RequestValidationError)
    async def safe_validation_error(request, exc):
        if request.url.path.startswith("/api/admin/") and request.url.path.endswith("/reset-password"):
            return JSONResponse({"detail": f"관리자 비밀번호와 새 비밀번호({MIN_PASSWORD_LENGTH}~{MAX_PASSWORD_LENGTH}자), 비밀번호 확인을 확인하세요."}, status_code=422)
        if request.url.path.startswith("/api/auth/"):
            # Never echo rejected passwords in validation errors.
            return JSONResponse({"detail": f"입력 형식을 확인하세요. 아이디 4~24자(영문·숫자·_), 가입 비밀번호 {MIN_PASSWORD_LENGTH}~{MAX_PASSWORD_LENGTH}자, 닉네임 2~20자입니다."}, status_code=422)
        return await request_validation_exception_handler(request, exc)
    app.state.database = database
    app.state.user_databases = UserDatabasePool(database)
    app.state.database_ready = False
    app.state.problem_repository = None
    app.state.answer_repository = None
    app.state.operation_sessions = OperationSessionManager()
    app.add_exception_handler(Exception, unhandled_exception_handler)

    if app_settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=app_settings.allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Content-Type", "Authorization", "X-User-Id"],
        )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(catalog_router)
    app.include_router(circuit_analysis_router)
    app.include_router(problems_router)
    app.include_router(wiring_router)
    app.include_router(mounting_router)
    app.include_router(operation_router)
    app.include_router(operation_session_router)
    app.include_router(free_circuit_router)
    static_root = app_settings.resolved_static_dir.resolve()

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str, request: Request):
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API 경로를 찾을 수 없습니다.")
        if not static_root.is_dir():
            raise HTTPException(
                status_code=503,
                detail="프런트엔드 빌드 파일이 없습니다. npm run build를 실행해 주세요.",
            )

        requested_file = (static_root / full_path).resolve()
        try:
            requested_file.relative_to(static_root)
        except ValueError:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

        if full_path and requested_file.is_file():
            return FileResponse(requested_file)
        index_file = static_root / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)
        raise HTTPException(status_code=503, detail="index.html을 찾을 수 없습니다.")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    current_settings = load_settings()
    logging.getLogger("electrician_simulator").info(
        "웹 서버 실행 | host=%s port=%s", current_settings.host, current_settings.port
    )
    uvicorn.run(
        "app.main:app",
        host=current_settings.host,
        port=current_settings.port,
        reload=current_settings.debug,
    )
