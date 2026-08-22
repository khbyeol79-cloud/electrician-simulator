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
    shutil.copytree(PROJECT_ROOT / "catalog", bundle / "catalog")
    shutil.copytree(PROJECT_ROOT / "problems" / "practice_001", bundle / "problems" / "practice_001")
    dist = bundle / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html>test</html>", encoding="utf-8")
    return AppPaths(
        project_root=bundle,
        bundle_root=bundle,
        frontend_dist=dist,
        problems_dir=bundle / "problems",
        catalog_dir=bundle / "catalog",
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

        sockets = client.get("/api/catalog/socket-types")
        assert sockets.status_code == 200
        assert sockets.json()[0]["rows"][0]["pins"] == [6, 5, 4, 3]
        assert sockets.json()[1]["rows"][1]["pins"] == [7, 8, 9, 10, 11, 12]

        devices = client.get("/api/catalog/device-types")
        assert devices.status_code == 200
        assert "contacts" not in devices.text
        assert "coil" not in devices.text

        behaviors = client.get("/api/catalog/device-behaviors")
        assert behaviors.status_code == 200
        assert len(behaviors.json()) == 16
        assert "expected_nets" not in behaviors.text
        assert "wiring_connections" not in behaviors.text
        assert "TB5-" not in behaviors.text
        assert "TB6-" not in behaviors.text

        relay = client.get(
            "/api/catalog/device-behaviors/auxiliary_relay_8p_training_partial"
        )
        assert relay.status_code == 200
        assert relay.json()["device_type_id"] == "auxiliary_relay_8p"
        assert client.get("/api/catalog/device-behaviors/missing_model").status_code == 404

        circuit_summary = client.get("/api/problems/practice_001/circuit-summary")
        assert circuit_summary.status_code == 200
        assert circuit_summary.json()["reference_integrity"] == "valid"
        assert circuit_summary.json()["definition_status"] == "structure_only"
        for forbidden in ("socket_pin_answers", "required_connections", "expected_nets"):
            assert forbidden not in circuit_summary.text


def test_problem_reload_and_missing_problem(tmp_path):
    settings = Settings(paths=api_paths(tmp_path))
    with TestClient(create_app(settings)) as client:
        reload_response = client.post("/api/problems/reload")
        assert reload_response.status_code == 200
        assert reload_response.json() == {"loaded": 1, "excluded": 0, "warnings": 1}
        assert client.get("/api/problems/unknown_001").status_code == 404
        assert client.get("/api/problems/unknown_001/circuit-summary").status_code == 404
