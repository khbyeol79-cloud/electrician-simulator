from __future__ import annotations

import re

from app.domain import OperationAction
from app.repositories import ProblemRepository
from app.services import DeviceBehaviorRuntimeComposer
from app.services.free_circuit_template_service import FreeCircuitTemplateService
from app.simulation import OperationEngine
from problem_test_utils import PROJECT_ROOT
from scripts.run_basic_board_demo import (
    interlock_connections,
    make_engine,
    motor_connections,
    power_and_start,
    self_hold_connections,
    timer_connections,
)


def runtime_definition():
    repository = ProblemRepository(
        PROJECT_ROOT / "problems", PROJECT_ROOT / "schemas", PROJECT_ROOT / "catalog"
    )
    repository.reload()
    template = FreeCircuitTemplateService(
        repository, PROJECT_ROOT / "free_templates"
    ).get("basic_board_001")
    return template, DeviceBehaviorRuntimeComposer(repository.catalog).compose(
        template.circuit, template.operation
    )


def test_basic_board_runtime_references_are_composed_without_answer_data():
    template, runtime = runtime_definition()
    assert template.operation.simulation_mode == "actual_wiring"
    assert runtime.catalog_composed is True
    assert not template.circuit.terminals
    assert {item.coil_id for item in runtime.circuit.coils} >= {
        "X1-COIL", "X2-COIL", "T1-COIL", "T2-COIL", "MC1-COIL", "MC2-COIL"
    }
    assert {item.contact_id for item in runtime.circuit.contacts} >= {
        "X1-C1", "T1-C1", "MC1-MAIN1", "MC1-HOLD", "MC1-INTERLOCK",
        "EOCR-TRIP-NC", "EOCR-TRIP-NO",
    }


def test_basic_board_x1_self_hold_stop_and_timer_lamp():
    _, runtime = runtime_definition()
    held_engine = make_engine(runtime, self_hold_connections(True))
    held = power_and_start(held_engine)
    assert held.coils["X1-COIL"] is True
    stopped = held_engine.apply(OperationAction(action="press_control", control_id="PB0"))
    assert stopped.coils["X1-COIL"] is False

    timer = make_engine(runtime, timer_connections())
    before = timer.apply(OperationAction(action="set_power", value=True))
    assert before.indicators["GL"] == "off"
    after = timer.apply(OperationAction(action="advance_time", milliseconds=1000))
    assert after.timers["T1-TIMER"].status == "completed"
    assert after.indicators["GL"] == "on"


def test_basic_board_motor_phases_interlock_and_eocr_are_actual_wiring():
    _, runtime = runtime_definition()
    assert power_and_start(make_engine(runtime, motor_connections())).motors["M1"] == "forward"
    assert power_and_start(make_engine(runtime, motor_connections(swap=True))).motors["M1"] == "reverse"
    assert power_and_start(make_engine(runtime, motor_connections(missing=True))).motors["M1"] == "phase_loss"

    interlocked = make_engine(runtime, interlock_connections())
    power_and_start(interlocked)
    blocked = interlocked.apply(OperationAction(action="press_control", control_id="PB2"))
    assert blocked.coils["MC2-COIL"] is False
    assert blocked.interlocks["ELEC-MC1-MC2"].status == "blocking"

    protected = make_engine(runtime, motor_connections())
    power_and_start(protected)
    tripped = protected.apply(OperationAction(
        action="trigger_fault", target_id="EOCR", fault_type="overload"
    ))
    assert tripped.coils["MC1-COIL"] is False
    assert tripped.indicators["RL"] == "on"
    reset = protected.apply(OperationAction(action="reset_fault", target_id="EOCR"))
    assert reset.coils["MC1-COIL"] is False


def test_basic_board_manual_wiring_table_only_uses_real_terminal_ids():
    template, runtime = runtime_definition()
    known = {item.terminal_id for item in runtime.circuit.terminals}
    known.update(template.board.terminal_ids)
    known.update(
        terminal.terminal_id
        for device in template.wiring_semantics.external_devices
        for terminal in device.terminals
    )
    document = (PROJECT_ROOT / "docs" / "basic-board-manual-test-0.11.2.md").read_text(
        encoding="utf-8"
    )
    rows = re.findall(r"^\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", document, re.MULTILINE)
    assert len(rows) == 60
    referenced = {terminal.strip() for row in rows for terminal in row}
    assert referenced <= known
