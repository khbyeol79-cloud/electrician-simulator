from __future__ import annotations

import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for path in (PROJECT_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.core.config import Settings
from app.core.paths import AppPaths
from desktop.local_server import LocalServer, find_free_port


def test_find_free_port():
    port = find_free_port()
    assert isinstance(port, int)
    assert 0 < port < 65536


def test_local_server_lifecycle(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("desktop", encoding="utf-8")
    problems = tmp_path / "problems"
    problems.mkdir()
    shutil.copytree(PROJECT_ROOT / "schemas", tmp_path / "schemas")
    shutil.copytree(PROJECT_ROOT / "catalog", tmp_path / "catalog")
    paths = AppPaths(
        project_root=tmp_path,
        bundle_root=tmp_path,
        frontend_dist=dist,
        problems_dir=problems,
        catalog_dir=tmp_path / "catalog",
        writable_root=tmp_path / "data",
        database_file=tmp_path / "data" / "test.db",
        logs_dir=tmp_path / "logs",
        log_file=tmp_path / "logs" / "test.log",
    )
    settings = Settings(
        app_mode="desktop",
        host="127.0.0.1",
        port=find_free_port(),
        paths=paths,
        static_dir=dist,
    )
    server = LocalServer(settings)
    try:
        server.start()
        server.wait_until_ready(timeout=5)
        assert server.running is True
    finally:
        server.stop()
    assert server.running is False
