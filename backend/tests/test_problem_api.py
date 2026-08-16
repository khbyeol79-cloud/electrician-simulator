from __future__ import annotations

import shutil

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.paths import AppPaths
from app.main import create_app
from problem_test_utils import PROJECT_ROOT


def api_paths(tmp_path):
    bundle = tmp_path / "bundle"
    shutil.copytree(PROJECT_ROOT / "schemas", bundle / "schemas")
    shutil.copytree(PROJECT_ROOT / "problems" / "practice_001", bundle / "problems" / "practice_001")
    dist = bundle / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html>test</html>", encoding="utf-8")
    return AppPaths(
        project_root=bundle,
        bundle_root=bundle,
        frontend_dist=dist,
        problems_dir=bundle / "problems",
        writable_root=tmp_path / "data",
        database_file=tmp_path / "data" / "test.db",
        logs_dir=tmp_path / "logs",
        log_file=tmp_path / "logs" / "test.log",
    )


def test_problem_api_never_exposes_answers_or_paths(tmp_path):
    settings = Settings(paths=api_paths(tmp_path))
    with TestClient(create_app(settings)) as client:
        listing = client.get("/api/problems")
        assert listing.status_code == 200
        assert listing.json()[0]["problem_id"] == "practice_001"

        detail = client.get("/api/problems/practice_001")
        assert detail.status_code == 200
        text = detail.text
        for forbidden in (
            "socket_pin_answers", "required_connections", "expected_nets",
            "allowed_alternatives", "forbidden_connections", "operation_tests",
            "answer.json", str(tmp_path),
        ):
            assert forbidden not in text

        answer_guess = client.get("/api/problems/practice_001/answer")
        assert answer_guess.status_code == 404


def test_problem_reload_and_missing_problem(tmp_path):
    settings = Settings(paths=api_paths(tmp_path))
    with TestClient(create_app(settings)) as client:
        reload_response = client.post("/api/problems/reload")
        assert reload_response.status_code == 200
        assert reload_response.json() == {"loaded": 1, "excluded": 0, "warnings": 1}
        assert client.get("/api/problems/unknown_001").status_code == 404

