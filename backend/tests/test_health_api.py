from __future__ import annotations

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.paths import AppPaths
from app.main import create_app


def make_paths(tmp_path):
    static_dir = tmp_path / "dist"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html>test</html>", encoding="utf-8")
    problems = tmp_path / "problems"
    problems.mkdir()
    project_root = Path(__file__).resolve().parents[2]
    shutil.copytree(project_root / "schemas", tmp_path / "schemas")
    shutil.copytree(project_root / "catalog", tmp_path / "catalog")
    return AppPaths(
        project_root=tmp_path,
        bundle_root=tmp_path,
        frontend_dist=static_dir,
        problems_dir=problems,
        catalog_dir=tmp_path / "catalog",
        writable_root=tmp_path / "data",
        database_file=tmp_path / "data" / "test.db",
        logs_dir=tmp_path / "logs",
        log_file=tmp_path / "logs" / "test.log",
    )


def test_health_and_app_info(tmp_path):
    settings = Settings(paths=make_paths(tmp_path), static_dir=tmp_path / "dist")
    with TestClient(create_app(settings)) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        assert health.json()["app_name"] == "전기기능사 시퀀스 결선 시뮬레이터"

        info = client.get("/api/app-info")
        assert info.status_code == 200
        assert info.json()["database_ready"] is True
        assert info.json()["problems_path_ready"] is True


def test_unknown_api_path_returns_404(tmp_path):
    settings = Settings(paths=make_paths(tmp_path), static_dir=tmp_path / "dist")
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/does-not-exist")
        assert response.status_code == 404
