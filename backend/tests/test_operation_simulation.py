from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.domain import OperationAction, WiringConnection
from app.repositories.problem_repository import ProblemRepository
from app.simulation import OperationEngine
from problem_test_utils import PROJECT_ROOT
from test_circuit_analysis_api import stage4_paths


def demo_connections():
    answer = json.loads((PROJECT_ROOT / "problems" / "operation_demo_001" / "answer.json").read_text(encoding="utf-8"))
    return [
        {"from": item["from"], "to": item["to"], "wire_color": item["wire_color"], "pair_display_color": "blue"}
        for item in answer["wiring_connections"]
    ]


def accepted_client(tmp_path):
    client = TestClient(create_app(Settings(paths=stage4_paths(tmp_path))))
    client.__enter__()
    result = client.post(
        "/api/problems/operation_demo_001/wiring-attempts/submit",
        json={"problem_version": 1, "connections": demo_connections()},
    )
    assert result.status_code == 200 and result.json()["overall_correct"] is True
    return client, result.json()["attempt_id"]


def test_setup_and_session_require_functional_problem_and_accepted_snapshot(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        setup = client.get("/api/problems/operation_demo_001/operation-setup").json()
        assert setup["operation_ready"] is False
        assert setup["wiring_source"] == "none"
        denied = client.post("/api/problems/operation_demo_001/operation-sessions", json={"problem_version": 1})
        assert denied.status_code == 409
        assert "정상 결선" in denied.text
        assert client.post("/api/problems/missing/operation-sessions", json={"problem_version": 1}).status_code == 404
        assert client.post("/api/problems/operation_demo_001/operation-sessions", json={"problem_version": 2}).status_code == 409


def test_session_power_self_hold_timer_indicator_motor_and_stop(tmp_path):
    client, attempt_id = accepted_client(tmp_path)
    try:
        setup = client.get("/api/problems/operation_demo_001/operation-setup").json()
        assert setup["operation_ready"] is True
        assert setup["wiring_source"] == "accepted_submission"
        assert setup["wiring_snapshot"]["attempt_id"] == attempt_id
        assert "operation_tests" not in json.dumps(setup)

        created = client.post(
            "/api/problems/operation_demo_001/operation-sessions",
            json={"problem_version": 1, "wiring_attempt_id": attempt_id},
        )
        assert created.status_code == 201
        session_id = created.json()["session_id"]

        power = client.post(f"/api/operation-sessions/{session_id}/actions", json={"action": "set_power", "value": True}).json()
        assert power["powered"] is True and not any(power["coils"].values())
        started = client.post(f"/api/operation-sessions/{session_id}/actions", json={"action": "press_control", "control_id": "PB1"}).json()
        assert started["coils"]["MC1-COIL"] is True
        assert started["timers"]["T1"]["status"] == "timing"
        assert started["motors"]["M1"] == "forward"
        released = client.post(f"/api/operation-sessions/{session_id}/actions", json={"action": "release_control", "control_id": "PB1"}).json()
        assert released["coils"]["MC1-COIL"] is True
        completed = client.post(f"/api/operation-sessions/{session_id}/actions", json={"action": "advance_time", "milliseconds": 1000}).json()
        assert completed["timers"]["T1"]["status"] == "completed"
        assert completed["indicators"]["GL"] == "on"
        stopped = client.post(f"/api/operation-sessions/{session_id}/actions", json={"action": "press_control", "control_id": "PB0"}).json()
        assert stopped["coils"]["MC1-COIL"] is False
        assert stopped["timers"]["T1"]["status"] == "stopped"
        assert stopped["indicators"]["GL"] == "off"
        assert stopped["motors"]["M1"] == "stopped"
    finally:
        client.__exit__(None, None, None)


def test_automatic_check_is_isolated_and_progress_is_saved(tmp_path):
    client, attempt_id = accepted_client(tmp_path)
    try:
        session = client.post("/api/problems/operation_demo_001/operation-sessions", json={"problem_version": 1, "wiring_attempt_id": attempt_id}).json()
        session_id = session["session_id"]
        client.post(f"/api/operation-sessions/{session_id}/actions", json={"action": "set_power", "value": True})
        before = client.get(f"/api/operation-sessions/{session_id}").json()
        checked = client.post(f"/api/operation-sessions/{session_id}/run-check").json()
        after = client.get(f"/api/operation-sessions/{session_id}").json()
        assert checked["overall_passed"] is True
        assert checked["passed_count"] == checked["total_count"] == 2
        assert before == after
        assert "expect" not in json.dumps(checked) and "steps" not in json.dumps(checked)
        progress = client.get("/api/problems/operation_demo_001/operation-progress").json()
        assert progress["attempt_count"] == 1 and progress["last_overall_passed"] is True
        reset = client.post(f"/api/operation-sessions/{session_id}/reset").json()
        assert reset["powered"] is False and reset["elapsed_ms"] == 0
        assert client.delete(f"/api/operation-sessions/{session_id}").status_code == 204
        assert client.get(f"/api/operation-sessions/{session_id}").status_code == 404
    finally:
        client.__exit__(None, None, None)


def test_engine_detects_direct_short_phase_loss_and_deterministic_time():
    repository = ProblemRepository(PROJECT_ROOT / "problems", PROJECT_ROOT / "schemas", PROJECT_ROOT / "catalog")
    repository.reload()
    package = repository._get_package_internal("operation_demo_001")
    assert package and package.problem.operation
    wiring = [WiringConnection.model_validate(item) for item in demo_connections()]

    shorted = OperationEngine(
        session_id="short", problem_id=package.manifest.problem_id, wiring_attempt_id=1,
        circuit=package.problem.circuit, definition=package.problem.operation,
        connections=wiring + [WiringConnection.model_validate({"from": "TB5-04", "to": "TB6-01"})],
    )
    state = shorted.apply(OperationAction(action="set_power", value=True))
    assert state.power_state == "tripped"
    assert any(item.code == "direct_short" for item in state.faults)

    missing_phase = [item for item in wiring if set(item.key) != {"MCCB-T3", "EOCR-L3"}]
    engine = OperationEngine(
        session_id="phase", problem_id=package.manifest.problem_id, wiring_attempt_id=2,
        circuit=package.problem.circuit, definition=package.problem.operation, connections=missing_phase,
    )
    engine.apply(OperationAction(action="set_power", value=True))
    engine.apply(OperationAction(action="press_control", control_id="PB1"))
    engine.apply(OperationAction(action="release_control", control_id="PB1"))
    first = engine.apply(OperationAction(action="advance_time", milliseconds=400))
    second = engine.apply(OperationAction(action="advance_time", milliseconds=600))
    assert first.timers["T1"].status == "timing" and first.timers["T1"].elapsed_ms == 400
    assert second.timers["T1"].status == "completed"
    assert second.motors["M1"] == "phase_loss"
