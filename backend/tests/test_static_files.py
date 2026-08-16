from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from test_health_api import make_paths


def test_spa_fallback_and_static_asset(tmp_path):
    paths = make_paths(tmp_path)
    assets = paths.frontend_dist / "assets"
    assets.mkdir()
    (assets / "sample.js").write_text("console.log('ok')", encoding="utf-8")
    settings = Settings(paths=paths, static_dir=paths.frontend_dist)

    with TestClient(create_app(settings)) as client:
        assert client.get("/circuit").text == "<html>test</html>"
        assert "console.log" in client.get("/assets/sample.js").text

