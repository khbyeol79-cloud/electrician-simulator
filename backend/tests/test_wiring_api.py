from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from test_circuit_analysis_api import stage4_paths


CONNECTIONS = [
    {"from": "TB5-01", "to": "MCCB-L1", "wire_color": "brown", "pair_display_color": "#2563eb"},
    {"from": "TB5-02", "to": "MCCB-L2", "wire_color": "black", "pair_display_color": "#f97316"},
    {"from": "TB5-03", "to": "MCCB-L3", "wire_color": "gray", "pair_display_color": "#7c3aed"},
    {"from": "F-2", "to": "X1-6", "wire_color": "yellow", "pair_display_color": "#dc2626"},
    {"from": "X1-1", "to": "MC1-4", "wire_color": "yellow", "pair_display_color": "#0891b2"},
    {"from": "X1-6", "to": "MC1-5", "wire_color": "yellow", "pair_display_color": "#db2777"},
    {"from": "X2-2", "to": "T1-7", "wire_color": "yellow", "pair_display_color": "#ca8a04"},
    {"from": "MC2-12", "to": "TB6-05", "wire_color": "yellow", "pair_display_color": "#4f46e5"},
]


def test_board_is_public_but_answer_is_not(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        response = client.get("/api/problems/training_socket_demo_001/board")
        assert response.status_code == 200
        payload = response.json()
        assert payload["board_id"] == "training_wiring_board_v1"
        assert any(item["item_id"] == "X1" for item in payload["items"])
        assert "wiring_connections" not in response.text
        assert "W-001" not in response.text


def test_wiring_draft_submit_and_progress(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        saved = client.put("/api/problems/training_socket_demo_001/wiring-draft", json={"problem_version": 1, "mode": "summary", "connections": CONNECTIONS[:2]})
        assert saved.status_code == 200
        assert client.get("/api/problems/training_socket_demo_001/wiring-draft").json()["mode"] == "summary"

        result = client.post("/api/problems/training_socket_demo_001/wiring-attempts/submit", json={"problem_version": 1, "connections": CONNECTIONS})
        assert result.status_code == 200
        assert result.json()["overall_correct"] is True
        assert result.json()["correct_count"] == 8
        assert client.get("/api/problems/training_socket_demo_001/wiring-progress").json()["attempt_count"] == 1

        assert client.delete("/api/problems/training_socket_demo_001/wiring-draft").status_code == 204
        assert client.get("/api/problems/training_socket_demo_001/wiring-draft").json() is None


def test_wiring_validation_and_unverified_problem(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        invalid = [{"from": "MISSING", "to": "X1-1", "wire_color": "yellow", "pair_display_color": "blue"}]
        assert client.post("/api/problems/training_socket_demo_001/wiring-attempts/submit", json={"problem_version": 1, "connections": invalid}).status_code == 422
        assert client.post("/api/problems/training_socket_demo_001/wiring-attempts/submit", json={"problem_version": 2, "connections": []}).status_code == 409
        unverified = client.post("/api/problems/practice_001/wiring-attempts/submit", json={"problem_version": 1, "connections": []})
        assert unverified.status_code == 200
        assert unverified.json()["gradable"] is False
