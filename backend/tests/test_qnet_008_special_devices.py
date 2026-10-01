from __future__ import annotations

from app.domain import OperationAction, WiringConnection
from app.domain.operation_definition import OperationDefinition, OperationPower
from app.domain.problem_definition import BoardPosition, CircuitDefinition, CircuitDevice
from app.services import CatalogService, DeviceBehaviorRuntimeComposer
from app.simulation import OperationEngine
from problem_test_utils import PROJECT_ROOT


MODELS = (
    ("PWR", "power_source", "power_3p_control_training"),
    ("FR", "flasher_relay_8p", "flasher_relay_8p_training"),
    ("FLS", "floatless_level_switch_8p", "floatless_level_switch_8p_training"),
    ("SS", "selector_switch", "selector_switch_auto_manual"),
    ("BZ", "buzzer", "buzzer_two_terminal"),
    ("YL", "indicator_lamp", "indicator_lamp_two_terminal"),
    ("RL", "indicator_lamp", "indicator_lamp_two_terminal"),
    ("GL", "indicator_lamp", "indicator_lamp_two_terminal"),
)


def _wire(left: str, right: str) -> WiringConnection:
    return WiringConnection.model_validate(
        {"from": left, "to": right, "wire_color": "yellow"}
    )


def _engine() -> OperationEngine:
    devices = [
        CircuitDevice(
            device_id=device_id,
            device_type_id=device_type_id,
            label=device_id,
            behavior_model_id=model_id,
            board_position=BoardPosition(row=0, column=index, x=0.1, y=0.1),
        )
        for index, (device_id, device_type_id, model_id) in enumerate(MODELS)
    ]
    source = CircuitDefinition(
        schema_version="1.0", definition_status="functional", devices=devices
    )
    operation = OperationDefinition(
        simulation_status="functional",
        simulation_mode="actual_wiring",
        power=OperationPower(line_terminal_id="PWR-L", return_terminal_id="PWR-N"),
    )
    catalog = CatalogService(PROJECT_ROOT / "catalog", PROJECT_ROOT / "schemas")
    runtime = DeviceBehaviorRuntimeComposer(catalog).compose(source, operation)
    connections = [
        _wire("PWR-L", "FR-2"), _wire("FR-7", "PWR-N"),
        _wire("PWR-L", "FR-5"), _wire("FR-8", "YL-1"), _wire("YL-2", "PWR-N"),
        _wire("PWR-L", "FLS-5"), _wire("FLS-6", "PWR-N"),
        _wire("FLS-7", "FLS-E1"), _wire("FLS-8", "FLS-E2"),
        _wire("FLS-1", "FLS-E3"), _wire("PWR-L", "FLS-3"),
        _wire("FLS-4", "BZ-1"), _wire("BZ-2", "PWR-N"),
        _wire("PWR-L", "SS-A1"), _wire("SS-A2", "RL-1"),
        _wire("RL-2", "PWR-N"), _wire("PWR-L", "SS-M1"),
        _wire("SS-M2", "GL-1"), _wire("GL-2", "PWR-N"),
    ]
    return OperationEngine(
        session_id="q008-special",
        problem_id="qnet-special-test",
        wiring_attempt_id=0,
        circuit=runtime.circuit,
        definition=runtime.operation,
        connections=connections,
        catalog_composed=runtime.catalog_composed,
        composition_warnings=runtime.warnings,
    )


def test_flasher_cycles_and_resets_when_power_is_removed():
    engine = _engine()
    powered = engine.apply(OperationAction(action="set_power", value=True))
    assert powered.flashers["FR-FLASH"].status == "off"
    assert powered.indicators["YL"] == "on"  # PDF: FR 8-5 is the NC output.
    first = engine.apply(OperationAction(action="advance_time", milliseconds=1000))
    assert first.flashers["FR-FLASH"].status == "on"
    assert first.indicators["YL"] == "off"
    second = engine.apply(OperationAction(action="advance_time", milliseconds=1000))
    assert second.flashers["FR-FLASH"].status == "off"
    assert second.indicators["YL"] == "on"
    stopped = engine.apply(OperationAction(action="set_power", value=False))
    assert stopped.flashers["FR-FLASH"].status == "stopped"


def test_level_relay_requires_supply_electrodes_and_user_level_input():
    engine = _engine()
    engine.apply(OperationAction(action="set_power", value=True))
    detected = engine.apply(
        OperationAction(action="set_level", target_id="FLS-LEVEL", value=True)
    )
    assert detected.level_relays["FLS-LEVEL"].powered is True
    assert detected.level_relays["FLS-LEVEL"].wiring_ready is True
    assert detected.level_relays["FLS-LEVEL"].detected is True
    assert detected.audible_outputs["BZ"] == "on"
    released = engine.apply(
        OperationAction(action="set_level", target_id="FLS-LEVEL", value=False)
    )
    assert released.level_relays["FLS-LEVEL"].detected is False
    assert released.audible_outputs["BZ"] == "off"


def test_selector_closes_exactly_one_auto_or_manual_path():
    engine = _engine()
    automatic = engine.apply(OperationAction(action="set_power", value=True))
    assert automatic.indicators["RL"] == "on"
    assert automatic.indicators["GL"] == "off"
    manual = engine.apply(
        OperationAction(action="toggle_control", control_id="SS")
    )
    assert manual.indicators["RL"] == "off"
    assert manual.indicators["GL"] == "on"
