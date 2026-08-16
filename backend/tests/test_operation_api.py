from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from test_circuit_analysis_api import stage4_paths
from test_wiring_api import CONNECTIONS


def test_operation_setup_exposes_public_fixed_layout_without_answers(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        response = client.get("/api/problems/training_socket_demo_001/operation-setup")
        assert response.status_code == 200
        payload = response.json()
        placements = payload["device_layout"]["fixed_placements"]
        assert len(placements) == 6
        assert {item["socket_id"] for item in placements} == {"X1", "X2", "T1", "T2", "MC1", "MC2"}
        assert payload["operation_ready"] is False
        assert payload["wiring_exists"] is False
        for forbidden in ("wiring_connections", "mounting_answer", "operation_tests", "answer.json"):
            assert forbidden not in response.text


def test_correct_wiring_makes_operation_ready_and_preserves_draft(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        saved = client.put(
            "/api/problems/training_socket_demo_001/wiring-draft",
            json={"problem_version": 1, "mode": "graphic", "connections": CONNECTIONS},
        )
        assert saved.status_code == 200
        submitted = client.post(
            "/api/problems/training_socket_demo_001/wiring-attempts/submit",
            json={"problem_version": 1, "connections": CONNECTIONS},
        )
        assert submitted.status_code == 200
        assert submitted.json()["overall_correct"] is True

        setup = client.get("/api/problems/training_socket_demo_001/operation-setup").json()
        assert setup["operation_ready"] is True
        assert setup["preview_allowed"] is False
        assert setup["wiring_exists"] is True
        assert len(setup["wiring_draft"]["connections"]) == len(CONNECTIONS)
        assert setup["wiring_submission"]["last_gradable"] is True
        assert setup["wiring_submission"]["last_overall_correct"] is True


def test_unverified_problem_allows_preview_without_fake_success(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        result = client.post(
            "/api/problems/practice_001/wiring-attempts/submit",
            json={"problem_version": 1, "connections": []},
        )
        assert result.status_code == 200
        assert result.json()["gradable"] is False

        setup = client.get("/api/problems/practice_001/operation-setup").json()
        assert setup["operation_ready"] is False
        assert setup["preview_allowed"] is True
        assert setup["wiring_submission"]["last_gradable"] is False
        assert setup["wiring_submission"]["last_overall_correct"] is None
        assert setup["device_layout"]["fixed_placements"][0]["socket_id"] == "X3"


def test_legacy_mounting_rows_do_not_block_operation_setup(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        with client.app.state.database.connect() as connection:
            connection.execute(
                "INSERT INTO mounting_drafts(problem_id, problem_version, placements_json) VALUES (?, ?, ?)",
                ("training_socket_demo_001", 1, "[]"),
            )
        response = client.get("/api/problems/training_socket_demo_001/operation-setup")
        assert response.status_code == 200
        assert response.json()["device_layout"] is not None
        assert client.get("/api/problems/missing/operation-setup").status_code == 404
