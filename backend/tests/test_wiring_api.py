from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from test_circuit_analysis_api import stage4_paths
from problem_test_utils import PROJECT_ROOT


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
        eocr = next(item for item in payload["items"] if item["item_id"] == "EOCR")
        fuse = next(item for item in payload["items"] if item["item_id"] == "F")
        tb5 = next(item for item in payload["items"] if item["item_id"] == "TB5")
        tb6 = next(item for item in payload["items"] if item["item_id"] == "TB6")
        assert eocr["item_type"] == "socket_12p"
        assert eocr["socket_type_id"] == "socket_12p_base"
        assert [(pin["number"], pin["role_label"]) for pin in eocr["pins"]] == [
            (1, "L1"), (2, "L2"), (3, "L3"), (4, "96"), (5, "98"), (6, "A1"),
            (7, "U"), (8, "V"), (9, "W"), (10, "95"), (11, "97"), (12, "A2"),
        ]
        mc1 = next(item for item in payload["items"] if item["item_id"] == "MC1")
        assert {pin["number"]: pin["role_label"] for pin in mc1["pins"]}[6] == "A1"
        assert {pin["number"]: pin["role_label"] for pin in mc1["pins"]}[12] == "A2"
        assert all(pin["max_connections"] == 2 for item in payload["items"] for pin in item["pins"])
        assert fuse["x"] - (eocr["x"] + eocr["width"]) >= 24
        for item in payload["items"]:
            if item["item_type"] != "terminal_block":
                assert item["x"] >= max(tb5["x"], tb6["x"])
                assert item["x"] + item["width"] <= min(tb5["x"] + tb5["width"], tb6["x"] + tb6["width"])
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
        assert result.json()["result_classification"] == "correct"
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


def test_every_terminal_including_terminal_blocks_allows_at_most_two_connections(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        three_on_socket = [
            {"from": "X1-1", "to": "MC1-4", "wire_color": "yellow"},
            {"from": "X1-1", "to": "MC1-5", "wire_color": "yellow"},
            {"from": "X1-1", "to": "MC1-6", "wire_color": "yellow"},
        ]
        rejected = client.put("/api/problems/training_socket_demo_001/wiring-draft", json={"problem_version": 1, "mode": "graphic", "connections": three_on_socket})
        assert rejected.status_code == 422
        assert "최대 연결 수" in rejected.text

        three_on_terminal_block = [
            {"from": "TB5-01", "to": "MCCB-L1", "wire_color": "brown"},
            {"from": "TB5-01", "to": "EOCR-L1", "wire_color": "brown"},
            {"from": "TB5-01", "to": "F-1", "wire_color": "brown"},
        ]
        rejected_tb = client.put("/api/problems/training_socket_demo_001/wiring-draft", json={"problem_version": 1, "mode": "graphic", "connections": three_on_terminal_block})
        assert rejected_tb.status_code == 422
        assert "최대 연결 수" in rejected_tb.text


def test_alternative_tb_numbers_are_accepted_by_electrical_network(tmp_path):
    alternative = [
        {"from": "EXT01-1", "to": "TB5-11", "wire_color": "yellow"},
        {"from": "TB5-11", "to": "MCCB-L1", "wire_color": "brown"},
        {"from": "EXT02-1", "to": "TB5-12", "wire_color": "yellow"},
        {"from": "TB5-12", "to": "MCCB-L2", "wire_color": "black"},
        {"from": "EXT03-1", "to": "TB5-13", "wire_color": "yellow"},
        {"from": "TB5-13", "to": "MCCB-L3", "wire_color": "gray"},
        {"from": "F-2", "to": "X1-6", "wire_color": "yellow"},
        {"from": "X1-6", "to": "MC1-5", "wire_color": "yellow"},
        {"from": "X1-1", "to": "MC1-4", "wire_color": "yellow"},
        {"from": "X2-2", "to": "T1-7", "wire_color": "yellow"},
        {"from": "EXT04-1", "to": "TB6-10", "wire_color": "yellow"},
        {"from": "TB6-10", "to": "MC2-12", "wire_color": "yellow"},
    ]
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        response = client.post(
            "/api/problems/training_socket_demo_001/wiring-attempts/submit",
            json={"problem_version": 1, "connections": alternative},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["overall_correct"] is True
        assert payload["electrically_equivalent"] is True
        assert payload["used_alternative_tb_numbers"] is True
        assert payload["result_classification"] == "functionally_equivalent"
        assert payload["correct_net_count"] == payload["required_net_count"] == 7
        setup = client.get("/api/problems/training_socket_demo_001/operation-setup").json()
        snapshot_edges = {
            tuple(sorted((item["from"], item["to"])))
            for item in setup["wiring_snapshot"]["connections"]
        }
        assert tuple(sorted(("EXT01-1", "TB5-11"))) in snapshot_edges


def test_lan_users_have_isolated_sqlite_drafts_and_progress(tmp_path):
    user_a = {"X-User-Id": "browser_a"}
    user_b = {"X-User-Id": "browser_b"}
    endpoint = "/api/problems/training_socket_demo_001/wiring-draft"
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        saved = client.put(
            endpoint,
            headers=user_a,
            json={"problem_version": 1, "mode": "graphic", "connections": CONNECTIONS[:1]},
        )
        assert saved.status_code == 200
        assert client.get(endpoint, headers=user_a).json()["connections"] == CONNECTIONS[:1]
        assert client.get(endpoint, headers=user_b).json() is None
        assert client.get(endpoint).json() is None

        submitted = client.post(
            "/api/problems/training_socket_demo_001/wiring-attempts/submit",
            headers=user_a,
            json={"problem_version": 1, "connections": CONNECTIONS},
        )
        assert submitted.status_code == 200
        assert client.get(
            "/api/problems/training_socket_demo_001/wiring-progress", headers=user_a
        ).json()["attempt_count"] == 1
        assert client.get(
            "/api/problems/training_socket_demo_001/wiring-progress", headers=user_b
        ).json()["attempt_count"] == 0


def test_invalid_web_user_id_is_rejected(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        response = client.get(
            "/api/problems/training_socket_demo_001/wiring-draft",
            headers={"X-User-Id": "../other-user"},
        )
        assert response.status_code == 400


def test_working_but_structurally_extra_circuit_is_not_accepted_as_correct(tmp_path):
    answer = json.loads(
        (PROJECT_ROOT / "problems" / "operation_demo_001" / "answer.json").read_text(encoding="utf-8")
    )
    connections = [
        {"from": item["from"], "to": item["to"], "wire_color": item["wire_color"]}
        for item in answer["wiring_connections"]
    ]
    connections.append({"from": "X1-1", "to": "X1-2", "wire_color": "yellow"})
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        response = client.post(
            "/api/problems/operation_demo_001/wiring-attempts/submit",
            json={"problem_version": 1, "connections": connections},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["overall_correct"] is False
        assert payload["operation_requirements_passed"] is True
        assert payload["result_classification"] == "operates_but_incorrect"
        assert "동작하지만" in payload["message"]
