from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.domain.device_behavior import DeviceInstanceCreate  # noqa: E402
from app.domain.operation_definition import (  # noqa: E402
    OperationAction,
    OperationContactor,
    OperationDefinition,
    OperationExpectation,
    OperationMotor,
    OperationPower,
    OperationProtectionDevice,
    OperationRequirement,
)
from app.domain.problem_definition import (  # noqa: E402
    BoardPosition,
    CircuitDefinition,
    CircuitTerminal,
)
from app.services import CatalogService, DeviceInstanceFactory  # noqa: E402


CATALOG = CatalogService(ROOT / "catalog", ROOT / "schemas")
FACTORY = DeviceInstanceFactory(CATALOG)


def pos(index: int) -> BoardPosition:
    return BoardPosition(
        row=index // 6, column=index % 6, x=0.08 + (index % 6) * 0.15, y=0.08 + (index // 6) * 0.26
    )


def fragment(spec, index: int):
    instance_id, label, model_id, settings = spec
    model = CATALOG.get_device_behavior(model_id)
    assert model is not None
    return FACTORY.create(DeviceInstanceCreate(
        model_id=model_id,
        instance_id=instance_id,
        label=label,
        board_position=pos(index),
        settings=settings,
        socket_type_id=(model.compatible_socket_type_ids[0] if model.compatible_socket_type_ids else None),
        installed_initially=True,
    ))


def requirement(requirement_id: str, label: str, actions, **expected):
    return OperationRequirement(
        requirement_id=requirement_id,
        label=label,
        scenario_id=requirement_id,
        scenario_label=label,
        next_action="결선을 바꾸거나 조작 순서를 다시 실행해 전기적 상태를 확인하세요.",
        actions=actions,
        expectations=[OperationExpectation(path=path, expected=value) for path, value in expected.items()],
    )


def action(name: str, **values):
    return OperationAction(action=name, **values)


def build_runtime(specs, *, requirements, motors, contactors):
    parts = [fragment(spec, index) for index, spec in enumerate(specs)]
    circuit = CircuitDefinition(
        schema_version="1.0",
        definition_status="functional",
        devices=[part.device for part in parts],
        terminals=[item for part in parts for item in part.terminals],
        contacts=[item for part in parts for item in part.contacts],
        coils=[item for part in parts for item in part.coils],
    )
    operation = OperationDefinition(
        schema_version="1.0",
        simulation_status="functional",
        simulation_mode="actual_wiring",
        power=OperationPower(
            line_terminal_id="PWR-L1",
            return_terminal_id="PWR-L3",
            phase_terminal_ids=["PWR-L1", "PWR-L2", "PWR-L3"],
        ),
        controls=[item for part in parts for item in part.controls],
        timers=[item for part in parts for item in part.timers],
        flashers=[item for part in parts for item in part.flashers],
        level_relays=[item for part in parts for item in part.level_relays],
        indicators=[item for part in parts for item in part.indicators],
        audible_outputs=[item for part in parts for item in part.audible_outputs],
        motors=motors,
        contactors=contactors,
        protection_devices=[OperationProtectionDevice(
            protection_device_id="EOCR",
            label="EOCR",
            protected_coil_ids=[item.coil_id for item in contactors],
            protected_motor_ids=[item.motor_id for item in motors],
            protection_contact_ids=["EOCR-TRIP-NC", "EOCR-TRIP-NO"],
            supply_terminal_a_id="EOCR-A1",
            supply_terminal_b_id="EOCR-A2",
            reset_mode="manual",
        )],
        fuse_channels=[item for part in parts for item in part.fuse_channels],
        requirements=requirements,
        internal_connections=[item for part in parts for item in part.intrinsic_connections],
    )
    return circuit, operation


COMMON_HEAD = [
    ("PWR", "외부 전원", "power_3p_control_training", {}),
    ("MCCB", "MCCB", "mccb_3p_training", {}),
    ("EOCR", "EOCR", "eocr_12p_training", {}),
    ("F", "FUSE", "fuse_dual_4terminal_training", {}),
]


def q008():
    specs = [*COMMON_HEAD,
        ("X", "X", "auxiliary_relay_8p_training_partial", {}),
        ("FR", "FR", "flasher_relay_8p_training", {"flash_interval_ms": 1000}),
        ("T", "T", "timer_8p_on_delay_training_partial", {"delay_ms": 1000}),
        ("FLS", "FLS", "floatless_level_switch_8p_training", {}),
        ("MC1", "MC1", "magnetic_contactor_12p_training", {}),
        ("MC2", "MC2", "magnetic_contactor_12p_training", {}),
        ("PB0", "PB0 정지", "push_button_nc", {}),
        ("PB1", "PB1 기동", "push_button_no", {}),
        ("SS", "SS 자동·수동", "selector_switch_auto_manual", {}),
        ("BZ", "부저", "buzzer_two_terminal", {}),
        ("YL", "황색 표시등", "indicator_lamp_two_terminal", {"display_color": "yellow"}),
        ("RL", "적색 표시등", "indicator_lamp_two_terminal", {"display_color": "red"}),
        ("GL", "녹색 표시등", "indicator_lamp_two_terminal", {"display_color": "green"}),
        ("M1", "전동기 M1", "motor_three_phase", {}),
        ("M2", "전동기 M2", "motor_three_phase", {}),
    ]
    auto = [action("set_power", value=True), action("set_level", target_id="FLS-LEVEL", value=True)]
    manual = [action("set_power", value=True), action("toggle_control", control_id="SS"), action("press_control", control_id="PB1"), action("release_control", control_id="PB1")]
    requirements = [
        requirement("AUTO_LEVEL", "SS 자동에서 수위 감지 시 FLS·X·MC1·MC2 및 두 전동기가 동작하는가", auto, **{"level_relays.FLS-LEVEL.detected": True, "coils.X-COIL": True, "coils.MC1-COIL": True, "coils.MC2-COIL": True, "motors.M1": "forward", "motors.M2": "forward"}),
        requirement("AUTO_LAMPS", "자동 운전에서 RL·GL은 켜지고 FR 첫 전환 후 YL이 꺼지는가", [*auto, action("advance_time", milliseconds=1000)], **{"indicators.RL": "on", "indicators.GL": "on", "indicators.YL": "off"}),
        requirement("AUTO_RELEASE", "수위 감지 해제 시 자동 운전이 정지하는가", [*auto, action("set_level", target_id="FLS-LEVEL", value=False)], **{"coils.X-COIL": False, "coils.MC1-COIL": False, "coils.MC2-COIL": False, "motors.M1": "stopped", "motors.M2": "stopped"}),
        requirement("MANUAL_START", "SS 수동에서 PB1 기동 시 T·MC1·MC2와 두 전동기가 동작하는가", manual, **{"coils.T-COIL": True, "coils.MC1-COIL": True, "coils.MC2-COIL": True, "motors.M1": "forward", "motors.M2": "forward"}),
        requirement("MANUAL_TIMER", "수동 운전에서 설정시간 뒤 T 접점으로 운전이 정지하는가", [*manual, action("advance_time", milliseconds=1000)], **{"timers.T-TIMER.status": "completed", "coils.MC1-COIL": False, "coils.MC2-COIL": False}),
        requirement("STOP", "운전 중 PB0을 누르면 제어회로와 전동기가 정지하는가", [*manual, action("press_control", control_id="PB0")], **{"coils.MC1-COIL": False, "coils.MC2-COIL": False, "motors.M1": "stopped", "motors.M2": "stopped"}),
        requirement("EOCR", "EOCR 과부하 시 전동기가 정지하고 BZ가 동작하는가", [*manual, action("trigger_fault", target_id="EOCR", fault_type="overload")], **{"motors.M1": "protection_trip", "motors.M2": "protection_trip", "audible_outputs.BZ": "on"}),
    ]
    motors = [
        OperationMotor(motor_id="M1", label="전동기 M1", forward_coil_id="MC1-COIL", phase_terminal_ids=["M1-U", "M1-V", "M1-W"], phase_source_terminal_ids=["PWR-L1", "PWR-L2", "PWR-L3"]),
        OperationMotor(motor_id="M2", label="전동기 M2", forward_coil_id="MC2-COIL", phase_terminal_ids=["M2-U", "M2-V", "M2-W"], phase_source_terminal_ids=["PWR-L1", "PWR-L2", "PWR-L3"]),
    ]
    contactors = [
        OperationContactor(contactor_id="MC1", label="MC1", coil_id="MC1-COIL", role="general", start_control_id="PB1", motor_id="M1"),
        OperationContactor(contactor_id="MC2", label="MC2", coil_id="MC2-COIL", role="general", start_control_id="PB1", motor_id="M2"),
    ]
    circuit, operation = build_runtime(specs, requirements=requirements, motors=motors, contactors=contactors)
    circuit.terminals.extend([
        CircuitTerminal(terminal_id=f"FLS-E{number}", device_id="FLS", terminal_type="external_terminal", electrical_role="control", max_connections=1)
        for number in (1, 2, 3)
    ])
    return circuit, operation


def q018():
    specs = [*COMMON_HEAD,
        ("X1", "X1", "auxiliary_relay_8p_training_partial", {}),
        ("X2", "X2", "auxiliary_relay_8p_training_partial", {}),
        ("T1", "T1", "timer_8p_on_delay_training_partial", {"delay_ms": 1000}),
        ("T2", "T2", "timer_8p_on_delay_training_partial", {"delay_ms": 1000}),
        ("MC1", "MC1", "magnetic_contactor_12p_training", {}),
        ("MC2", "MC2", "magnetic_contactor_12p_training", {}),
        ("PB0", "PB0 정지", "push_button_nc", {}),
        ("PB1", "PB1 기동", "push_button_no", {}),
        ("PB2", "PB2 기동", "push_button_no", {}),
        ("LS1", "LS1", "limit_switch_no", {}),
        ("LS2", "LS2", "limit_switch_no", {}),
        ("RL", "적색 표시등", "indicator_lamp_two_terminal", {"display_color": "red"}),
        ("GL", "녹색 표시등", "indicator_lamp_two_terminal", {"display_color": "green"}),
        ("WL", "백색 표시등", "indicator_lamp_two_terminal", {"display_color": "white"}),
        ("YL", "황색 표시등", "indicator_lamp_two_terminal", {"display_color": "yellow"}),
        ("M1", "전동기 M1", "motor_three_phase", {}),
        ("M2", "전동기 M2", "motor_three_phase", {}),
    ]
    one_held = [action("set_power", value=True), action("toggle_control", control_id="LS1"), action("press_control", control_id="PB1")]
    two_held = [action("set_power", value=True), action("toggle_control", control_id="LS2"), action("press_control", control_id="PB2")]
    one_latched = [*one_held, action("release_control", control_id="PB1"), action("advance_time", milliseconds=1000)]
    two_latched = [*two_held, action("release_control", control_id="PB2"), action("advance_time", milliseconds=1000)]
    requirements = [
        requirement("LS1_X1", "LS1 감지·LS2 해제에서 PB1을 누르면 X1이 여자되는가", one_held, **{"coils.X1-COIL": True}),
        requirement("MC1_RL", "PB1을 누르는 동안 MC1·M1·RL이 즉시 동작하는가", one_held, **{"coils.MC1-COIL": True, "motors.M1": "forward", "indicators.RL": "on"}),
        requirement("T1_WL", "PB1을 놓아도 순시 접점으로 유지되고 T1 설정시간 뒤 WL이 점등되는가", one_latched, **{"coils.MC1-COIL": True, "timers.T1-TIMER.status": "completed", "indicators.WL": "on"}),
        requirement("LS2_X2", "LS2 감지·LS1 해제에서 PB2를 누르면 X2가 여자되는가", two_held, **{"coils.X2-COIL": True}),
        requirement("MC2_GL", "PB2를 누르는 동안 MC2·M2·GL이 즉시 동작하는가", two_held, **{"coils.MC2-COIL": True, "motors.M2": "forward", "indicators.GL": "on"}),
        requirement("T2_WL", "PB2를 놓아도 순시 접점으로 유지되고 T2 설정시간 뒤 WL이 점등되는가", two_latched, **{"coils.MC2-COIL": True, "timers.T2-TIMER.status": "completed", "indicators.WL": "on"}),
        requirement("STOP", "자기유지 운전 중 PB0을 누르면 릴레이·타이머·전자접촉기·전동기가 정지하는가", [*one_latched, action("press_control", control_id="PB0")], **{"coils.X1-COIL": False, "coils.T1-COIL": False, "coils.MC1-COIL": False, "motors.M1": "stopped"}),
        requirement("EOCR", "자기유지 운전 중 EOCR 과부하 시 전동기가 정지하고 YL이 점등되는가", [*one_latched, action("trigger_fault", target_id="EOCR", fault_type="overload")], **{"coils.MC1-COIL": False, "motors.M1": "protection_trip", "indicators.YL": "on"}),
    ]
    motors = [
        OperationMotor(motor_id="M1", label="전동기 M1", forward_coil_id="MC1-COIL", phase_terminal_ids=["M1-U", "M1-V", "M1-W"], phase_source_terminal_ids=["PWR-L1", "PWR-L2", "PWR-L3"]),
        OperationMotor(motor_id="M2", label="전동기 M2", forward_coil_id="MC2-COIL", phase_terminal_ids=["M2-U", "M2-V", "M2-W"], phase_source_terminal_ids=["PWR-L1", "PWR-L2", "PWR-L3"]),
    ]
    contactors = [
        OperationContactor(contactor_id="MC1", label="MC1", coil_id="MC1-COIL", role="general", start_control_id="PB1", motor_id="M1"),
        OperationContactor(contactor_id="MC2", label="MC2", coil_id="MC2-COIL", role="general", start_control_id="PB2", motor_id="M2"),
    ]
    return build_runtime(specs, requirements=requirements, motors=motors, contactors=contactors)


def build(problem_number: str):
    problem_id = f"qnet_electrician_practical_{problem_number}"
    package = ROOT / "problems" / problem_id
    problem = json.loads((package / "problem.json").read_text(encoding="utf-8"))
    if problem_number == "010":
        if problem.get("circuit", {}).get("definition_status") != "functional":
            raise ValueError("Q-Net 010 공개 기능 회로가 준비되지 않았습니다.")
        if problem.get("operation", {}).get("simulation_status") != "functional":
            raise ValueError("Q-Net 010 공개 동작 정의가 준비되지 않았습니다.")
        return package, problem
    circuit, operation = q008() if problem_number == "008" else q018()
    problem["description"] = f"Q-Net 공개문제 {problem_number}의 PDF 6~9쪽을 구조화한 draft/unverified 무채점 기능 연습본입니다. 현재 사용자 결선의 전기적 동작과 공개 요구사항 충족 여부만 확인합니다."
    problem["instructions"] = [
        "공식 PDF 6~9쪽의 배치·회로·내부결선도를 함께 확인하세요.",
        "개인 분석과 결선은 자동저장되며 정답·점수·합격/불합격 판정은 제공하지 않습니다.",
        "동작시험 결과는 현재 결선의 전기적 상태이며 공식 정답 인증이 아닙니다.",
    ]
    problem["circuit"] = circuit.model_dump(mode="json", by_alias=True)
    problem["operation"] = operation.model_dump(mode="json", by_alias=True)
    problem["wiring_semantics"]["extra_jumper_policy"] = "reject"
    contacts = {"PB0": "NC", "PB1": "NO", "PB2": "NO", "LS1": "NO", "LS2": "NO"}
    for device in problem["wiring_semantics"]["external_devices"]:
        if device["device_id"] in contacts:
            device["contact_type"] = contacts[device["device_id"]]
    if problem_number == "008":
        devices = problem["wiring_semantics"]["external_devices"]
        selector = next(item for item in devices if item["device_id"] == "SS")
        selector["terminals"] = [
            {"terminal_id": f"SS-{suffix}", "label": suffix, "terminal_role": "external", "operation_terminal_id": None, "max_connections": 1, "wire_color": "yellow"}
            for suffix in ("A1", "A2", "M1", "M2")
        ]
    return package, problem


def build_dual_fuse_board(package: Path) -> dict:
    """Keep every public practice board on the physical two-cartridge fuse layout."""
    board_path = package / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    fuse = next(item for item in board["items"] if item["item_id"] == "F")
    left_x = fuse["x"] + 35
    right_x = fuse["x"] + 85
    top_y = fuse["y"]
    bottom_y = fuse["y"] + fuse["height"]
    fuse["label"] = "F"
    fuse["pins"] = [
        {
            "terminal_id": f"F-{number}",
            "label": str(number),
            "number": number,
            "side": side,
            "x": x,
            "y": y,
            "max_connections": 2,
            "enabled": True,
            "terminal_role": "functional",
        }
        for number, side, x, y in (
            (1, "top", left_x, top_y),
            (3, "top", right_x, top_y),
            (2, "bottom", left_x, bottom_y),
            (4, "bottom", right_x, bottom_y),
        )
    ]
    fuse["label_area"] = {
        "x": fuse["x"] + 48,
        "y": fuse["y"] + 64,
        "width": 24,
        "height": 22,
    }
    return board


def main() -> int:
    parser = argparse.ArgumentParser(description="Q-Net 008·010·018 공개 근거 기반 무채점 문제 템플릿 생성기")
    parser.add_argument("problem", choices=["008", "010", "018", "all"])
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    for number in (["008", "010", "018"] if args.problem == "all" else [args.problem]):
        package, payload = build(number)
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        if args.write:
            (package / "problem.json").write_text(text, encoding="utf-8")
            board = build_dual_fuse_board(package)
            (package / "board.json").write_text(
                json.dumps(board, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            manifest_path = package / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["capabilities"] = {"board_visible": True, "wiring_editable": True, "wiring_gradable": False, "operation_previewable": True, "operation_gradable": False}
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
