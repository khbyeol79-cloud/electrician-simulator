from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from test_circuit_analysis_api import stage4_paths


CORRECT_PLACEMENTS = [
    {"mount_device_id": "DEVICE-X1", "socket_id": "X1"},
    {"mount_device_id": "DEVICE-X2", "socket_id": "X2"},
    {"mount_device_id": "DEVICE-T1", "socket_id": "T1"},
    {"mount_device_id": "DEVICE-T2", "socket_id": "T2"},
    {"mount_device_id": "DEVICE-MC1", "socket_id": "MC1"},
    {"mount_device_id": "DEVICE-MC2", "socket_id": "MC2"},
]


def test_mounting_definition_is_public_but_answer_is_not(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        response = client.get("/api/problems/training_socket_demo_001/mounting")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["available_devices"]) == 6
        assert any(item["socket_id"] == "T1" for item in payload["mount_targets"])
        assert "mounting_answer" not in response.text
        assert '"DEVICE-T1","socket_id":"T1"' not in response.text.replace(" ", "")


def test_mounting_draft_submit_and_progress(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        saved = client.put(
            "/api/problems/training_socket_demo_001/mounting-draft",
            json={"problem_version": 1, "placements": CORRECT_PLACEMENTS[:2]},
        )
        assert saved.status_code == 200
        assert len(client.get("/api/problems/training_socket_demo_001/mounting-draft").json()["placements"]) == 2

        result = client.post(
            "/api/problems/training_socket_demo_001/mounting-attempts/submit",
            json={"problem_version": 1, "placements": CORRECT_PLACEMENTS},
        )
        assert result.status_code == 200
        assert result.json()["overall_correct"] is True
        assert result.json()["correct_count"] == 6
        assert "expected_socket_id" not in result.text
        assert client.get("/api/problems/training_socket_demo_001/mounting-progress").json()["attempt_count"] == 1

        assert client.delete("/api/problems/training_socket_demo_001/mounting-draft").status_code == 204
        assert client.get("/api/problems/training_socket_demo_001/mounting-draft").json() is None


def test_mounting_wrong_missing_and_unverified_results(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        swapped = [
            {"mount_device_id": "DEVICE-X1", "socket_id": "X2"},
            {"mount_device_id": "DEVICE-X2", "socket_id": "X1"},
            *CORRECT_PLACEMENTS[2:5],
        ]
        result = client.post(
            "/api/problems/training_socket_demo_001/mounting-attempts/submit",
            json={"problem_version": 1, "placements": swapped},
        )
        assert result.status_code == 200
        assert result.json()["overall_correct"] is False
        assert result.json()["correct_count"] == 3
        assert set(result.json()["missing_device_ids"]) == {"DEVICE-MC2"}
        assert {item["mount_device_id"] for item in result.json()["wrong_placements"]} == {"DEVICE-X1", "DEVICE-X2"}

        unverified = client.post(
            "/api/problems/practice_001/mounting-attempts/submit",
            json={"problem_version": 1, "placements": [{"mount_device_id": "DEVICE-X3", "socket_id": "X3"}]},
        )
        assert unverified.status_code == 200
        assert unverified.json()["gradable"] is False
        assert unverified.json()["overall_correct"] is None


def test_mounting_validation_errors(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        cases = [
            ({"problem_version": 2, "placements": []}, 409),
            ({"problem_version": 1, "placements": [{"mount_device_id": "MISSING", "socket_id": "X1"}]}, 422),
            ({"problem_version": 1, "placements": [{"mount_device_id": "DEVICE-T1", "socket_id": "MC1"}]}, 422),
            ({"problem_version": 1, "placements": [{"mount_device_id": "DEVICE-X1", "socket_id": "T1"}]}, 422),
            ({"problem_version": 1, "placements": [{"mount_device_id": "DEVICE-X1", "socket_id": "X1"}, {"mount_device_id": "DEVICE-X1", "socket_id": "X2"}]}, 422),
        ]
        for payload, status in cases:
            response = client.post("/api/problems/training_socket_demo_001/mounting-attempts/submit", json=payload)
            assert response.status_code == status
        assert client.get("/api/problems/missing/mounting").status_code == 404
        assert client.get("/api/problems/missing/mounting-progress").status_code == 404
