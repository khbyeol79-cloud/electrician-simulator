from __future__ import annotations

import json
import shutil

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from problem_test_utils import PROJECT_ROOT
from test_circuit_analysis_api import stage4_paths


PROBLEM_IDS = (
    "qnet_electrician_practical_008",
    "qnet_electrician_practical_018",
)
PRIVATE_MARKERS = ("user-candidate", "expected_nets", "allowed_alternatives", "operation_tests")


def _paths(tmp_path):
    paths = stage4_paths(tmp_path)
    for problem_id in PROBLEM_IDS:
        shutil.copytree(
            PROJECT_ROOT / "problems" / problem_id,
            paths.problems_dir / problem_id,
        )
    return paths


@pytest.mark.parametrize("problem_id", PROBLEM_IDS)
def test_public_problem_is_ungraded_functional_practice(problem_id):
    package = PROJECT_ROOT / "problems" / problem_id
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    problem = json.loads((package / "problem.json").read_text(encoding="utf-8"))
    board = json.loads((package / "board.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "draft"
    assert manifest["capabilities"] == {
        "board_visible": True,
        "wiring_editable": True,
        "wiring_gradable": False,
        "operation_previewable": True,
        "operation_gradable": False,
    }
    assert problem["circuit"]["definition_status"] == "functional"
    assert problem["operation"]["simulation_status"] == "functional"
    assert problem["operation"]["requirements"]
    fuse = next(item for item in board["items"] if item["item_id"] == "F")
    assert {pin["terminal_id"] for pin in fuse["pins"]} == {
        "F-1", "F-2", "F-3", "F-4",
    }
    public = json.dumps(problem, ensure_ascii=False)
    assert all(marker not in public for marker in PRIVATE_MARKERS)


@pytest.mark.parametrize("problem_id", PROBLEM_IDS)
def test_empty_user_draft_can_open_isolated_practice_session(tmp_path, problem_id):
    with TestClient(create_app(Settings(paths=_paths(tmp_path)))) as client:
        saved = client.put(
            f"/api/problems/{problem_id}/practice-drafts/main",
            json={"problem_version": 1, "mode": "graphic", "connections": []},
        )
        assert saved.status_code == 200
        created = client.post(
            f"/api/problems/{problem_id}/practice-sessions",
            json={"problem_version": 1, "workspace_id": "main"},
        )
        assert created.status_code == 201, created.text
        state = created.json()
        assert state["session_type"] == "practice_preview_session"
        assert state["gradable"] is False
        assert state["workspace_id"] == "main"
        assert all(marker not in created.text for marker in PRIVATE_MARKERS)


def test_q008_exposes_controls_without_private_wiring(tmp_path):
    with TestClient(create_app(Settings(paths=_paths(tmp_path)))) as client:
        detail = client.get("/api/problems/qnet_electrician_practical_008")
        setup = client.get("/api/problems/qnet_electrician_practical_008/operation-setup")
        assert detail.status_code == setup.status_code == 200
        assert {item["requirement_id"] for item in setup.json()["behavior_requirements"]} >= {
            "P8_AUTO_01", "P8_MANUAL_01", "P8_EOCR_01"
        }
        text = detail.text + setup.text
        assert all(marker not in text for marker in PRIVATE_MARKERS)


@pytest.mark.parametrize(
    ("problem_id", "expected_count"),
    (("qnet_electrician_practical_008", 7), ("qnet_electrician_practical_018", 8)),
)
def test_public_requirements_have_explicit_ui_scenarios(problem_id, expected_count):
    problem = json.loads(
        (PROJECT_ROOT / "problems" / problem_id / "problem.json").read_text(
            encoding="utf-8"
        )
    )
    requirements = problem["operation"]["requirements"]
    assert len({item["scenario_id"] for item in requirements}) == expected_count
    assert all(item["scenario_label"] for item in requirements)
