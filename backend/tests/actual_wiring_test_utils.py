from __future__ import annotations

from app.domain.operation_definition import (
    OperationContactor,
    OperationControl,
    OperationDefinition,
    OperationMotor,
    OperationPower,
    OperationProtectionDevice,
)
from app.domain.problem_definition import BoardPosition, CircuitDefinition, CircuitDevice
from app.domain.wiring_attempt import WiringConnection
from app.services import CatalogService, DeviceBehaviorRuntimeComposer
from problem_test_utils import PROJECT_ROOT


MODELS = (
    ("PWR", "power_source", "power_3p_control_training"),
    ("PB0", "push_button", "push_button_nc"),
    ("PB1", "push_button", "push_button_no"),
    ("MC1", "auxiliary_relay_12p", "magnetic_contactor_12p_training"),
    ("EOCR", "eocr", "eocr_12p_training"),
    ("AL", "indicator_lamp", "indicator_lamp_two_terminal"),
    ("M1", "motor", "motor_three_phase"),
)


def source_definition():
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
    circuit = CircuitDefinition(
        schema_version="1.0",
        definition_status="functional",
        devices=devices,
    )
    operation = OperationDefinition(
        simulation_status="functional",
        simulation_mode="actual_wiring",
        power=OperationPower(
            line_terminal_id="PWR-L",
            return_terminal_id="PWR-N",
            phase_terminal_ids=["PWR-L1", "PWR-L2", "PWR-L3"],
        ),
        controls=[
            OperationControl(
                control_id="PB0", label="정지", control_type="pushbutton",
                mode="momentary", contact_type="NC",
                terminal_a_id="PB0-1", terminal_b_id="PB0-2",
            ),
            OperationControl(
                control_id="PB1", label="기동", control_type="pushbutton",
                mode="momentary", contact_type="NO",
                terminal_a_id="PB1-1", terminal_b_id="PB1-2",
            ),
        ],
        motors=[OperationMotor(
            motor_id="M1", label="M1 모터",
            forward_coil_id="MC1-COIL",
            phase_terminal_ids=["M1-U", "M1-V", "M1-W"],
            phase_source_terminal_ids=["PWR-L1", "PWR-L2", "PWR-L3"],
        )],
        contactors=[OperationContactor(
            contactor_id="MC1", label="MC1", coil_id="MC1-COIL",
            role="forward", start_control_id="PB1", motor_id="M1",
        )],
        protection_devices=[OperationProtectionDevice(
            protection_device_id="EOCR", label="EOCR",
            protected_coil_ids=["MC1-COIL"], protected_motor_ids=["M1"],
            reset_mode="manual",
        )],
    )
    return circuit, operation


def compose_actual():
    circuit, operation = source_definition()
    catalog = CatalogService(PROJECT_ROOT / "catalog", PROJECT_ROOT / "schemas")
    return DeviceBehaviorRuntimeComposer(catalog).compose(circuit, operation)


def wire(left: str, right: str, color: str = "yellow") -> WiringConnection:
    return WiringConnection.model_validate({"from": left, "to": right, "wire_color": color})


def actual_connections(*, swap_phases: bool = False, missing_phase: bool = False,
                       bypass_eocr: bool = False) -> list[WiringConnection]:
    phase_inputs = ["PWR-L1", "PWR-L3", "PWR-L2"] if swap_phases else [
        "PWR-L1", "PWR-L2", "PWR-L3"
    ]
    result = [
        wire("PWR-L", "PB0-1"),
        wire("PB0-2", "PB1-1"),
        wire("PB1-2", "MC1-6"),
        wire("MC1-12", "EOCR-95"),
        wire("EOCR-96", "PWR-N"),
        wire("PB1-1", "MC1-4"),
        wire("MC1-10", "PB1-2"),
        wire("PWR-L", "EOCR-97"),
        wire("EOCR-98", "AL-1"),
        wire("AL-2", "PWR-N"),
        wire(phase_inputs[0], "MC1-1", "brown"),
        wire(phase_inputs[1], "MC1-2", "black"),
        wire(phase_inputs[2], "MC1-3", "gray"),
        wire("MC1-7", "EOCR-L1", "brown"),
        wire("MC1-8", "EOCR-L2", "black"),
        wire("MC1-9", "EOCR-L3", "gray"),
        wire("EOCR-U", "M1-U", "brown"),
        wire("EOCR-V", "M1-V", "black"),
        wire("EOCR-W", "M1-W", "gray"),
    ]
    if missing_phase:
        result = [item for item in result if item.key != tuple(sorted(("MC1-9", "EOCR-L3")))]
    if bypass_eocr:
        result.append(wire("MC1-12", "PWR-N"))
    return result
