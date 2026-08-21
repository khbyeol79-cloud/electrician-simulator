from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from test_circuit_analysis_api import stage4_paths
from test_operation_simulation import demo_connections


def test_free_circuit_workspace_uses_common_engine_without_answer_data(tmp_path):
    headers = {"X-User-Id": "free_user"}
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        package = client.app.state.problem_repository._get_package_internal("operation_demo_001")
        payload = {
            "name": "자기유지 자유회로",
            "circuit": package.problem.circuit.model_dump(mode="json"),
            "operation": package.problem.operation.model_dump(by_alias=True, mode="json"),
            "connections": demo_connections(),
        }
        saved = client.put("/api/free-circuits/self_hold", headers=headers, json=payload)
        assert saved.status_code == 200
        assert saved.json()["workspace_id"] == "self_hold"
        assert client.get(
            "/api/free-circuits/self_hold", headers={"X-User-Id": "other_user"}
        ).status_code == 404

        created = client.post("/api/free-circuits/self_hold/sessions", headers=headers)
        assert created.status_code == 201
        assert created.json()["problem_id"] == "free:self_hold"
        session_id = created.json()["session_id"]
        client.post(
            f"/api/operation-sessions/{session_id}/actions",
            headers=headers,
            json={"action": "set_power", "value": True},
        )
        started = client.post(
            f"/api/operation-sessions/{session_id}/actions",
            headers=headers,
            json={"action": "press_control", "control_id": "PB1"},
        )
        assert started.status_code == 200
        assert started.json()["coils"]["MC1-COIL"] is True
        released = client.post(
            f"/api/operation-sessions/{session_id}/actions",
            headers=headers,
            json={"action": "release_control", "control_id": "PB1"},
        )
        assert released.json()["coils"]["MC1-COIL"] is True


def test_free_circuit_workspace_rejects_invalid_id(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        response = client.get("/api/free-circuits/not%20valid")
        assert response.status_code in {404, 422}
