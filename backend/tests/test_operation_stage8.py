from __future__ import annotations

import json
import shutil

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from problem_test_utils import PROJECT_ROOT
from test_circuit_analysis_api import stage4_paths


PROBLEM_ID = "forward_reverse_interlock_demo_001"


def stage8_paths(tmp_path):
    paths = stage4_paths(tmp_path)
    for problem_id in ("forward_reverse_interlock_demo_001", "eocr_sequence_demo_001"):
        shutil.copytree(PROJECT_ROOT / "problems" / problem_id, paths.problems_dir / problem_id)
    return paths


def answer_connections(problem_id: str) -> list[dict]:
    payload = json.loads((PROJECT_ROOT / "problems" / problem_id / "answer.json").read_text(encoding="utf-8"))
    return [{"from": item["from"], "to": item["to"], "wire_color": item["wire_color"]} for item in payload["wiring_connections"]]


def accepted_session(client: TestClient, problem_id: str = PROBLEM_ID) -> str:
    submitted = client.post(
        f"/api/problems/{problem_id}/wiring-attempts/submit",
        json={"problem_version": 1, "connections": answer_connections(problem_id)},
    )
    assert submitted.status_code == 200 and submitted.json()["overall_correct"] is True
    created = client.post(
        f"/api/problems/{problem_id}/operation-sessions",
        json={"problem_version": 1, "wiring_attempt_id": submitted.json()["attempt_id"]},
    )
    assert created.status_code == 201
    return created.json()["session_id"]


def action(client: TestClient, session_id: str, payload: dict) -> dict:
    response = client.post(f"/api/operation-sessions/{session_id}/actions", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_forward_reverse_self_hold_and_electrical_interlock(tmp_path):
    with TestClient(create_app(Settings(paths=stage8_paths(tmp_path)))) as client:
        session_id = accepted_session(client)
        action(client, session_id, {"action": "set_power", "value": True})
        forward = action(client, session_id, {"action": "press_control", "control_id": "PB1"})
        assert forward["coils"]["MC1-COIL"] is True
        assert forward["motors"]["M1"] == "forward"
        held = action(client, session_id, {"action": "release_control", "control_id": "PB1"})
        assert held["coils"]["MC1-COIL"] is True

        blocked = action(client, session_id, {"action": "press_control", "control_id": "PB2"})
        assert blocked["coils"]["MC1-COIL"] is True
        assert blocked["coils"]["MC2-COIL"] is False
        assert blocked["motors"]["M1"] == "forward"
        assert any(item["status"] == "blocking" for item in blocked["interlocks"].values())
        assert any("인터록에 의해 차단" in item for item in blocked["events"])
        progress = client.get(f"/api/problems/{PROBLEM_ID}/operation-progress").json()
        assert progress["interlock_seen"] is True

        action(client, session_id, {"action": "release_control", "control_id": "PB2"})
        stopped = action(client, session_id, {"action": "press_control", "control_id": "PB0"})
        assert stopped["coils"]["MC1-COIL"] is False
        assert stopped["motors"]["M1"] == "stopped"
        action(client, session_id, {"action": "release_control", "control_id": "PB0"})
        reverse = action(client, session_id, {"action": "press_control", "control_id": "PB2"})
        assert reverse["coils"]["MC2-COIL"] is True
        assert reverse["motors"]["M1"] == "reverse"


def test_eocr_trip_manual_reset_and_restart_required(tmp_path):
    with TestClient(create_app(Settings(paths=stage8_paths(tmp_path)))) as client:
        session_id = accepted_session(client)
        action(client, session_id, {"action": "set_power", "value": True})
        action(client, session_id, {"action": "press_control", "control_id": "PB1"})
        action(client, session_id, {"action": "release_control", "control_id": "PB1"})
        tripped = action(client, session_id, {"action": "trigger_fault", "target_id": "EOCR", "fault_type": "overload"})
        assert tripped["protections"]["EOCR"]["status"] == "reset_required"
        assert tripped["coils"]["MC1-COIL"] is False
        assert tripped["motors"]["M1"] == "protection_trip"

        blocked = action(client, session_id, {"action": "press_control", "control_id": "PB1"})
        assert blocked["coils"]["MC1-COIL"] is False
        action(client, session_id, {"action": "release_control", "control_id": "PB1"})
        reset = action(client, session_id, {"action": "reset_fault", "target_id": "EOCR"})
        assert reset["protections"]["EOCR"]["status"] == "normal"
        assert reset["coils"]["MC1-COIL"] is False
        restarted = action(client, session_id, {"action": "press_control", "control_id": "PB1"})
        assert restarted["motors"]["M1"] == "forward"

        denied = client.post(
            f"/api/operation-sessions/{session_id}/actions",
            json={"action": "trigger_fault", "target_id": "MISSING", "fault_type": "overload"},
        )
        assert denied.status_code == 422


def test_automatic_check_is_isolated_and_progress_flags_are_saved(tmp_path):
    with TestClient(create_app(Settings(paths=stage8_paths(tmp_path)))) as client:
        session_id = accepted_session(client)
        action(client, session_id, {"action": "set_power", "value": True})
        action(client, session_id, {"action": "press_control", "control_id": "PB2"})
        action(client, session_id, {"action": "release_control", "control_id": "PB2"})
        before = client.get(f"/api/operation-sessions/{session_id}").json()
        checked = client.post(f"/api/operation-sessions/{session_id}/run-check")
        after = client.get(f"/api/operation-sessions/{session_id}").json()
        assert checked.status_code == 200 and checked.json()["overall_passed"] is True
        assert before == after
        assert "steps" not in checked.text and "expect" not in checked.text
        progress = client.get(f"/api/problems/{PROBLEM_ID}/operation-progress").json()
        assert progress["manual_run_count"] == 1
        assert progress["reverse_seen"] is True
        assert progress["interlock_seen"] is False
        assert progress["last_overall_passed"] is True


def test_phase_loss_and_private_operation_tests_are_not_public(tmp_path):
    paths = stage8_paths(tmp_path)
    with TestClient(create_app(Settings(paths=paths))) as client:
        setup = client.get(f"/api/problems/{PROBLEM_ID}/operation-setup")
        assert setup.status_code == 200
        assert "operation_tests" not in setup.text and "expected" not in setup.text

        connections = [item for item in answer_connections(PROBLEM_ID) if {item["from"], item["to"]} != {"MCCB-T3", "EOCR-W"}]
        package = client.app.state.problem_repository._get_package_internal(PROBLEM_ID)
        from app.domain import OperationAction, WiringConnection
        from app.simulation import OperationEngine
        engine = OperationEngine(
            session_id="phase-loss", problem_id=PROBLEM_ID, wiring_attempt_id=1,
            circuit=package.problem.circuit, definition=package.problem.operation,
            connections=[WiringConnection.model_validate(item) for item in connections],
        )
        engine.apply(OperationAction(action="set_power", value=True))
        state = engine.apply(OperationAction(action="press_control", control_id="PB1"))
        assert state.motors["M1"] == "phase_loss"
