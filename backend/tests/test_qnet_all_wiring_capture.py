from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.paths import build_paths
from app.main import create_app


PROBLEM_IDS = tuple(f"qnet_electrician_practical_{number:03d}" for number in range(1, 19))
PRIVATE_MARKERS = ("expected_nets", "allowed_alternatives", "operation_tests", "user-candidate")
PROJECT_ROOT = Path(__file__).resolve().parents[2]

PDF_PAGE_6_LAYOUTS = {
    "001": (["F", "EOCR", "MCCB", "X", "FR"], ["T", "FLS", "MC1", "MC2"]),
    "002": (["EOCR", "MCCB", "F", "X", "FR"], ["MC1", "MC2", "T", "FLS"]),
    "003": (["MCCB", "EOCR", "F", "X", "FR"], ["T", "FLS", "MC1", "MC2"]),
    "004": (["MCCB", "EOCR", "FR", "X", "F"], ["FLS", "MC1", "MC2", "T"]),
    "005": (["EOCR", "F", "MCCB", "FR", "X"], ["MC1", "MC2", "FLS", "T"]),
    "006": (["EOCR", "MCCB", "F", "X", "FR"], ["FLS", "T", "MC1", "MC2"]),
    "007": (["MCCB", "F", "EOCR", "FR", "X"], ["FLS", "T", "MC1", "MC2"]),
    "008": (["F", "MCCB", "EOCR", "X", "FR"], ["T", "MC1", "MC2", "FLS"]),
    "009": (["MCCB", "EOCR", "F", "FR", "X"], ["T", "MC1", "MC2", "FLS"]),
    "010": (["MCCB", "EOCR", "X2", "X1", "F"], ["T1", "T2", "MC1", "MC2"]),
    "011": (["EOCR", "MCCB", "F", "X2", "X1"], ["MC1", "MC2", "T2", "T1"]),
    "012": (["F", "MCCB", "EOCR", "X1", "X2"], ["T2", "T1", "MC1", "MC2"]),
    "013": (["EOCR", "MCCB", "F", "X1", "X2"], ["T1", "MC1", "MC2", "T2"]),
    "014": (["F", "MCCB", "EOCR", "X2", "X1"], ["T2", "T1", "MC1", "MC2"]),
    "015": (["MCCB", "EOCR", "F", "X2", "X1"], ["T2", "MC1", "MC2", "T1"]),
    "016": (["MCCB", "EOCR", "X1", "X2", "F"], ["T2", "MC1", "MC2", "T1"]),
    "017": (["MCCB", "F", "EOCR", "X1", "X2"], ["T1", "MC1", "MC2", "T2"]),
    "018": (["MCCB", "EOCR", "F", "X1", "X2"], ["T2", "MC1", "MC2", "T1"]),
}


def _app(tmp_path):
    base = build_paths()
    writable = tmp_path / "capture-data"
    paths = replace(
        base, writable_root=writable, database_file=writable / "app.db",
        logs_dir=writable / "logs", log_file=writable / "logs" / "app.log",
    )
    return create_app(Settings(paths=paths))


@pytest.mark.parametrize("problem_id", PROBLEM_IDS)
def test_all_qnet_boards_allow_ungraded_user_capture(tmp_path, problem_id):
    with TestClient(_app(tmp_path)) as client:
        detail = client.get(f"/api/problems/{problem_id}")
        board = client.get(f"/api/problems/{problem_id}/board")
        assert detail.status_code == board.status_code == 200
        assert detail.json()["capabilities"]["wiring_editable"] is True
        assert detail.json()["capabilities"]["wiring_gradable"] is False
        saved = client.put(f"/api/problems/{problem_id}/practice-drafts/main", json={
            "problem_version": detail.json()["version"], "mode": "graphic", "connections": [],
        })
        assert saved.status_code == 200, saved.text
        assert saved.json()["gradable"] is False


@pytest.mark.parametrize("problem_id", PROBLEM_IDS)
def test_all_qnet_boards_preserve_official_fixed_coordinates(tmp_path, problem_id):
    source = json.loads((PROJECT_ROOT / "problems" / problem_id / "board.json").read_text(encoding="utf-8"))
    assert source["layout_mode"] == "fixed"
    with TestClient(_app(tmp_path)) as client:
        response = client.get(f"/api/problems/{problem_id}/board")
        assert response.status_code == 200
        served = response.json()
    assert served["layout_mode"] == "fixed"
    assert [
        (item["item_id"], item["row"], item["x"], item["y"], item["width"], item["height"])
        for item in served["items"]
    ] == [
        (item["item_id"], item["row"], item["x"], item["y"], item["width"], item["height"])
        for item in source["items"]
    ]


@pytest.mark.parametrize("problem_id", PROBLEM_IDS)
def test_qnet_fuses_use_one_four_terminal_body_with_two_independent_channels(problem_id):
    source = json.loads((PROJECT_ROOT / "problems" / problem_id / "board.json").read_text(encoding="utf-8"))
    fuses = [item for item in source["items"] if item["item_id"] == "F"]
    assert len(fuses) == 1
    fuse = fuses[0]
    assert fuse["label"] == "F"
    assert {pin["terminal_id"] for pin in fuse["pins"]} == {"F-1", "F-2", "F-3", "F-4"}
    pins = {pin["terminal_id"]: pin for pin in fuse["pins"]}
    assert pins["F-1"]["x"] == pins["F-2"]["x"] < pins["F-3"]["x"] == pins["F-4"]["x"]
    assert pins["F-1"]["y"] < pins["F-2"]["y"]
    assert pins["F-3"]["y"] < pins["F-4"]["y"]


@pytest.mark.parametrize("number", sorted(PDF_PAGE_6_LAYOUTS))
def test_all_qnet_internal_device_rows_match_pdf_page_6_without_overlap(number):
    board = json.loads((PROJECT_ROOT / "problems" / f"qnet_electrician_practical_{number}" / "board.json").read_text(encoding="utf-8"))
    expected_top, expected_bottom = PDF_PAGE_6_LAYOUTS[number]
    rows = {
        row: sorted((item for item in board["items"] if item["row"] == row), key=lambda item: item["x"])
        for row in (1, 2)
    }
    assert [item["item_id"] for item in rows[1]] == expected_top
    assert [item["item_id"] for item in rows[2]] == expected_bottom
    for items in rows.values():
        assert all(left["x"] + left["width"] < right["x"] for left, right in zip(items, items[1:]))
    gaps = [right['x'] - left['x'] - left['width'] for items in rows.values() for left, right in zip(items, items[1:])]
    assert min(gaps) >= 24
    assert max(gaps) - min(gaps) < .03
    for items in rows.values():
        centers = [item['y'] + item['height'] / 2 for item in items]
        assert max(centers) - min(centers) < .03


@pytest.mark.parametrize("problem_id", PROBLEM_IDS)
def test_all_qnet_board_terminals_and_forbidden_areas_follow_the_rendered_items(problem_id):
    board = json.loads((PROJECT_ROOT / "problems" / problem_id / "board.json").read_text(encoding="utf-8"))
    terminal_ids = [pin["terminal_id"] for item in board["items"] for pin in item["pins"]]
    assert len(terminal_ids) == len(set(terminal_ids))
    areas = {area["area_id"]: area for area in board["forbidden_areas"]}
    assert set(areas) == {f"{item['item_id']}_body" for item in board["items"]}
    for item in board["items"]:
        area = areas[f"{item['item_id']}_body"]
        assert (area["x"], area["y"], area["width"], area["height"]) == (
            item["x"], item["y"], item["width"], item["height"]
        )


@pytest.mark.parametrize(
    ("problem_id", "expected_order"),
    [
        ("qnet_electrician_practical_002", ["EOCR", "MCCB", "F", "X", "FR"]),
        ("qnet_electrician_practical_003", ["MCCB", "EOCR", "F", "X", "FR"]),
    ],
)
def test_qnet_002_003_upper_devices_are_complete_and_do_not_overlap(problem_id, expected_order):
    board = json.loads((PROJECT_ROOT / "problems" / problem_id / "board.json").read_text(encoding="utf-8"))
    upper = sorted((item for item in board["items"] if item["row"] == 1), key=lambda item: item["x"])
    assert [item["item_id"] for item in upper] == expected_order
    assert all(left["x"] + left["width"] < right["x"] for left, right in zip(upper, upper[1:]))
    assert len({pin["terminal_id"] for item in upper for pin in item["pins"]}) == sum(
        len(item["pins"]) for item in upper
    )
    areas = {area["area_id"]: area for area in board["forbidden_areas"]}
    for item in upper:
        area = areas[f"{item['item_id']}_body"]
        assert (area["x"], area["y"], area["width"], area["height"]) == (
            item["x"], item["y"], item["width"], item["height"]
        )


def test_capture_workspaces_warnings_snapshots_and_round_trip(tmp_path):
    problem_id = "qnet_electrician_practical_010"
    headers = {"X-User-Id": "capture_user"}
    with TestClient(_app(tmp_path)) as client:
        created = client.post(f"/api/problems/{problem_id}/practice-workspaces", headers=headers, json={
            "problem_version": 1, "workspace_name": "내 답안 A",
        })
        assert created.status_code == 201
        workspace_id = created.json()["workspace_id"]
        connections = [
            {"from": "F-1", "to": "F-1", "wire_color": "yellow"},
            {"from": "NOT-IN-010", "to": "F-2", "wire_color": "yellow"},
            {"from": "F-1", "to": "F-2", "wire_color": "yellow"},
            {"from": "F-2", "to": "F-1", "wire_color": "yellow"},
            {"from": "F-2", "to": "X1-1", "wire_color": "yellow"},
            {"from": "F-2", "to": "X1-2", "wire_color": "yellow"},
        ]
        saved = client.put(
            f"/api/problems/{problem_id}/practice-drafts/{workspace_id}", headers=headers,
            json={"problem_version": 1, "mode": "graphic", "connections": connections},
        )
        assert saved.status_code == 200
        codes = {item["code"] for item in saved.json()["structural_warnings"]}
        assert {"self_connection", "terminal_outside_problem", "duplicate_connection", "terminal_capacity_exceeded"} <= codes
        snapshot = client.post(
            f"/api/problems/{problem_id}/practice-drafts/{workspace_id}/snapshots",
            headers=headers, json={"label": "첫 버전"},
        )
        assert snapshot.status_code == 201
        exported = client.get(
            f"/api/problems/{problem_id}/practice-drafts/{workspace_id}/export", headers=headers,
        )
        assert exported.status_code == 200
        assert set(exported.json()) == {
            "schema_version", "problem_id", "problem_version", "workspace_id", "workspace_name",
            "snapshot_id", "created_at", "updated_at", "connections", "structural_warnings",
        }
        assert all(marker not in exported.text for marker in PRIVATE_MARKERS)
        imported = client.post(
            f"/api/problems/{problem_id}/practice-imports", headers=headers, json=exported.json(),
        )
        assert imported.status_code == 201, imported.text
        assert imported.json()["workspace_id"] != workspace_id
        assert imported.json()["connections"] == saved.json()["connections"]
        assert client.get(
            f"/api/problems/{problem_id}/practice-drafts/{workspace_id}", headers=headers,
        ).json()["connections"] == saved.json()["connections"]
        assert client.get(
            f"/api/problems/{problem_id}/practice-drafts/{workspace_id}",
            headers={"X-User-Id": "other_user"},
        ).json() is None


def test_problem_and_workspace_isolation(tmp_path):
    headers = {"X-User-Id": "isolated_user"}
    with TestClient(_app(tmp_path)) as client:
        first = client.post("/api/problems/qnet_electrician_practical_001/practice-workspaces", headers=headers, json={
            "problem_version": 1, "workspace_name": "첫째",
        }).json()
        second = client.post("/api/problems/qnet_electrician_practical_001/practice-workspaces", headers=headers, json={
            "problem_version": 1, "workspace_name": "둘째",
        }).json()
        assert first["workspace_id"] != second["workspace_id"]
        assert len(client.get("/api/problems/qnet_electrician_practical_001/practice-workspaces", headers=headers).json()) == 2
        assert client.get("/api/problems/qnet_electrician_practical_002/practice-workspaces", headers=headers).json() == []
