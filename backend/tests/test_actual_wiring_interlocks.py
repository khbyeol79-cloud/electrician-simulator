from __future__ import annotations

import json

from app.domain import OperationAction, WiringConnection
from app.repositories import ProblemRepository
from app.simulation import OperationEngine
from problem_test_utils import PROJECT_ROOT


PROBLEM_ID = "forward_reverse_interlock_demo_001"


def definition(*, keep_mechanical: bool, bypass: bool):
    repository = ProblemRepository(
        PROJECT_ROOT / "problems", PROJECT_ROOT / "schemas", PROJECT_ROOT / "catalog"
    )
    repository.reload()
    package = repository._get_package_internal(PROBLEM_ID)
    circuit = package.problem.circuit.model_copy(deep=True)
    operation = package.problem.operation.model_copy(deep=True)
    operation.simulation_mode = "actual_wiring"
    if not keep_mechanical:
        operation.interlocks = [item for item in operation.interlocks if item.type == "electrical"]
    answer = json.loads(
        (PROJECT_ROOT / "problems" / PROBLEM_ID / "answer.json").read_text(
            encoding="utf-8"
        )
    )
    connections = [
        WiringConnection.model_validate({
            "from": item["from"], "to": item["to"],
            "wire_color": item.get("wire_color", "yellow"),
        })
        for item in answer["wiring_connections"]
    ]
    if bypass:
        connections.extend([
            WiringConnection.model_validate({"from": "TB5-08", "to": "MC1-6"}),
            WiringConnection.model_validate({"from": "TB5-10", "to": "MC2-6"}),
        ])
    return circuit, operation, connections


def run(*, keep_mechanical: bool, bypass: bool):
    circuit, operation, connections = definition(
        keep_mechanical=keep_mechanical, bypass=bypass
    )
    item = OperationEngine(
        session_id="interlock", problem_id=PROBLEM_ID, wiring_attempt_id=1,
        circuit=circuit, definition=operation, connections=connections,
    )
    item.apply(OperationAction(action="set_power", value=True))
    item.apply(OperationAction(action="press_control", control_id="PB1"))
    item.apply(OperationAction(action="release_control", control_id="PB1"))
    return item, item.apply(OperationAction(action="press_control", control_id="PB2"))


def test_actual_nc_contact_blocks_opposite_coil_without_metadata_force():
    _, state = run(keep_mechanical=False, bypass=False)
    assert state.coils["MC1-COIL"] is True
    assert state.coils["MC2-COIL"] is False
    assert state.contacts["MC1-INTERLOCK"] == "open"
    assert state.interlocks["ELEC-MC1-MC2"].status == "blocking"


def test_electrical_interlock_metadata_alone_does_not_hide_a_bypass():
    _, state = run(keep_mechanical=False, bypass=True)
    assert state.coils["MC1-COIL"] is True
    assert state.coils["MC2-COIL"] is True
    assert state.interlocks["ELEC-MC1-MC2"].status == "fault"
    assert any(code.startswith("interlock_bypassed") for code in state.active_faults)


def test_mechanical_interlock_still_prevents_simultaneous_activation():
    _, state = run(keep_mechanical=True, bypass=True)
    assert state.coils["MC1-COIL"] is True
    assert state.coils["MC2-COIL"] is False
    assert state.interlocks["MECH-MC1-MC2"].status == "blocking"
    assert not any(code.startswith("interlock_bypassed") for code in state.active_faults)
