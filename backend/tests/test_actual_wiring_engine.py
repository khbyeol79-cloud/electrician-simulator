from __future__ import annotations

from app.domain import OperationAction
from app.simulation import OperationEngine
from actual_wiring_test_utils import actual_connections, compose_actual


def engine(**connection_options) -> OperationEngine:
    runtime = compose_actual()
    return OperationEngine(
        session_id="actual", problem_id="free:actual", wiring_attempt_id=0,
        circuit=runtime.circuit, definition=runtime.operation,
        connections=actual_connections(**connection_options),
        catalog_composed=runtime.catalog_composed,
        composition_warnings=runtime.warnings,
    )


def start(item: OperationEngine):
    item.apply(OperationAction(action="set_power", value=True))
    return item.apply(OperationAction(action="press_control", control_id="PB1"))


def test_mc_main_contacts_follow_coil_and_actual_phase_path_runs_motor():
    item = engine()
    initial = item.state()
    assert initial.simulation_mode == "actual_wiring"
    assert initial.catalog_composed is True
    assert initial.contacts["MC1-MAIN1"] == "open"
    running = start(item)
    assert running.coils["MC1-COIL"] is True
    assert running.contacts["MC1-MAIN1"] == "closed"
    assert running.contacts["MC1-MAIN2"] == "closed"
    assert running.contacts["MC1-MAIN3"] == "closed"
    assert running.motors["M1"] == "forward"
    held = item.apply(OperationAction(action="release_control", control_id="PB1"))
    assert held.coils["MC1-COIL"] is True
    stopped = item.apply(OperationAction(action="press_control", control_id="PB0"))
    assert stopped.coils["MC1-COIL"] is False
    assert stopped.contacts["MC1-MAIN1"] == "open"
    assert stopped.motors["M1"] == "stopped"


def test_phase_swap_reverses_direction_without_role_changes():
    normal = start(engine())
    swapped = start(engine(swap_phases=True))
    assert normal.motors["M1"] == "forward"
    assert swapped.motors["M1"] == "reverse"


def test_missing_phase_is_reported_from_actual_path():
    state = start(engine(missing_phase=True))
    assert state.motors["M1"] == "phase_loss"
    assert any(item.code == "motor_phase_loss:M1" for item in state.faults)


def test_eocr_contacts_open_and_close_and_wired_nc_drops_coil():
    item = engine()
    running = start(item)
    assert running.contacts["EOCR-TRIP-NC"] == "closed"
    assert running.contacts["EOCR-TRIP-NO"] == "open"
    assert running.indicators["AL"] == "off"
    tripped = item.apply(OperationAction(
        action="trigger_fault", target_id="EOCR", fault_type="overload"
    ))
    assert tripped.contacts["EOCR-TRIP-NC"] == "open"
    assert tripped.contacts["EOCR-TRIP-NO"] == "closed"
    assert tripped.indicators["AL"] == "on"
    assert tripped.coils["MC1-COIL"] is False
    assert tripped.motors["M1"] == "protection_trip"
    assert not any(code.startswith("protection_bypassed") for code in tripped.active_faults)


def test_bypassed_eocr_does_not_force_coil_off_and_reports_danger():
    item = engine(bypass_eocr=True)
    start(item)
    tripped = item.apply(OperationAction(
        action="trigger_fault", target_id="EOCR", fault_type="overload"
    ))
    assert tripped.coils["MC1-COIL"] is True
    assert tripped.motors["M1"] == "forward"
    assert any(code.startswith("protection_bypassed:EOCR") for code in tripped.active_faults)


def test_eocr_reset_does_not_restart_a_dropped_self_hold_circuit():
    item = engine()
    start(item)
    item.apply(OperationAction(action="release_control", control_id="PB1"))
    item.apply(OperationAction(action="trigger_fault", target_id="EOCR", fault_type="overload"))
    reset = item.apply(OperationAction(action="reset_fault", target_id="EOCR"))
    assert reset.coils["MC1-COIL"] is False
    restarted = item.apply(OperationAction(action="press_control", control_id="PB1"))
    assert restarted.coils["MC1-COIL"] is True
