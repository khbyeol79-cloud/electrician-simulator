from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.domain.device_behavior import DeviceInstanceCreate  # noqa: E402
from app.domain.operation_definition import (  # noqa: E402
    OperationContactor,
    OperationDefinition,
    OperationMotor,
    OperationPower,
    OperationProtectionDevice,
    TerminalPair,
)
from app.domain.problem_definition import BoardPosition, CircuitDefinition  # noqa: E402
from app.services import CatalogService, DeviceInstanceFactory  # noqa: E402


PROBLEM_ID = "qnet_electrician_practical_010"
PACKAGE = ROOT / "problems" / PROBLEM_ID


def position(row: int, column: int, x: float, y: float) -> BoardPosition:
    return BoardPosition(row=row, column=column, x=x, y=y)


DEVICE_SPECS = [
    ("PWR", "외부 전원", "power_3p_control_training", position(0, 0, 0.02, 0.02), {}, None),
    ("MCCB", "MCCB", "mccb_3p_training", position(1, 0, 0.12, 0.28), {}, None),
    ("EOCR", "EOCR", "eocr_12p_training", position(1, 1, 0.28, 0.28), {}, "socket_12p_base"),
    ("F", "FUSE", "fuse_dual_4terminal_training", position(1, 2, 0.41, 0.28), {}, None),
    ("X1", "X1", "auxiliary_relay_8p_training_partial", position(1, 3, 0.56, 0.28), {}, "socket_8p_base"),
    ("X2", "X2", "auxiliary_relay_8p_training_partial", position(1, 4, 0.72, 0.28), {}, "socket_8p_base"),
    ("T1", "T1", "timer_8p_on_delay_training_partial", position(2, 0, 0.15, 0.62), {"delay_ms": 1000}, "socket_8p_base"),
    ("T2", "T2", "timer_8p_on_delay_training_partial", position(2, 1, 0.31, 0.62), {"delay_ms": 1000}, "socket_8p_base"),
    ("MC1", "MC1", "magnetic_contactor_12p_training", position(2, 2, 0.50, 0.62), {}, "socket_12p_base"),
    ("MC2", "MC2", "magnetic_contactor_12p_training", position(2, 3, 0.69, 0.62), {}, "socket_12p_base"),
    ("PB0", "PB0 정지", "push_button_nc", position(0, 1, 0.10, 0.05), {}, None),
    ("PB1", "PB1 기동", "push_button_no", position(0, 2, 0.18, 0.05), {}, None),
    ("PB2", "PB2 기동", "push_button_no", position(0, 3, 0.26, 0.05), {}, None),
    ("LS1", "LS1", "limit_switch_no", position(0, 4, 0.34, 0.05), {}, None),
    ("LS2", "LS2", "limit_switch_no", position(0, 5, 0.42, 0.05), {}, None),
    ("YL", "황색 표시등", "indicator_lamp_two_terminal", position(3, 0, 0.12, 0.90), {"display_color": "yellow"}, None),
    ("WL", "백색 표시등", "indicator_lamp_two_terminal", position(3, 1, 0.26, 0.90), {"display_color": "white"}, None),
    ("RL", "적색 표시등", "indicator_lamp_two_terminal", position(3, 2, 0.40, 0.90), {"display_color": "red"}, None),
    ("GL", "녹색 표시등", "indicator_lamp_two_terminal", position(3, 3, 0.54, 0.90), {"display_color": "green"}, None),
    ("M1", "전동기 M1", "motor_three_phase", position(3, 4, 0.70, 0.90), {}, None),
    ("M2", "전동기 M2", "motor_three_phase", position(3, 5, 0.86, 0.90), {}, None),
]


EXPECTED_NETS = [
    ("P01_L1_IN", ["PWR-L1", "MCCB-L1"]),
    ("P02_L2_IN", ["PWR-L2", "MCCB-L2"]),
    ("P03_L3_IN", ["PWR-L3", "MCCB-L3"]),
    ("P04_PE", ["PWR-PE", "M1-PE", "M2-PE"]),
    ("P05_L1_LOAD", ["MCCB-T1", "EOCR-L1", "F-1"]),
    ("P06_L2_LOAD", ["MCCB-T2", "EOCR-L2"]),
    ("P07_L3_LOAD", ["MCCB-T3", "EOCR-L3", "F-3"]),
    ("P08_EOCR_U", ["EOCR-U", "MC1-1", "MC2-1"]),
    ("P09_EOCR_V", ["EOCR-V", "MC1-2", "MC2-2"]),
    ("P10_EOCR_W", ["EOCR-W", "MC1-3", "MC2-3"]),
    ("P11_M1_U", ["MC1-7", "M1-U"]),
    ("P12_M1_V", ["MC1-8", "M1-V"]),
    ("P13_M1_W", ["MC1-9", "M1-W"]),
    ("P14_M2_U", ["MC2-7", "M2-U"]),
    ("P15_M2_V", ["MC2-8", "M2-V"]),
    ("P16_M2_W", ["MC2-9", "M2-W"]),
    ("C01_PROTECTED_LINE", ["F-2", "EOCR-A1", "EOCR-95", "EOCR-97"]),
    ("C02_STOP_IN", ["EOCR-96", "PB0-1"]),
    ("C03_CONTROL_BUS", ["PB0-2", "PB1-1", "PB2-1", "X1-1", "X1-8", "X2-1", "X2-8", "MC1-4", "MC2-4"]),
    ("C04_X1_RUN", ["PB1-2", "X1-3", "X1-2", "LS1-1", "T1-1"]),
    ("C05_T1_COIL", ["LS1-2", "T1-2"]),
    ("C06_MC1_COIL", ["T1-3", "MC1-6"]),
    ("C07_X2_RUN", ["PB2-2", "X2-3", "X2-2", "LS2-1", "T2-1"]),
    ("C08_T2_COIL", ["LS2-2", "T2-2"]),
    ("C09_MC2_COIL", ["T2-3", "MC2-6"]),
    ("C10_X1_WL_IN", ["X1-6", "MC1-5"]),
    ("C11_X2_WL_IN", ["X2-6", "MC2-5"]),
    ("C12_WL", ["MC1-11", "MC2-11", "WL-1"]),
    ("C13_RL", ["MC1-10", "RL-1"]),
    ("C14_GL", ["MC2-10", "GL-1"]),
    ("C15_YL", ["EOCR-98", "YL-1"]),
    ("C16_RETURN", ["F-4", "EOCR-A2", "X1-7", "T1-7", "MC1-12", "X2-7", "T2-7", "MC2-12", "WL-2", "RL-2", "GL-2", "YL-2"]),
]


def fragments():
    catalog = CatalogService(ROOT / "catalog", ROOT / "schemas")
    factory = DeviceInstanceFactory(catalog)
    result = []
    for instance_id, label, model_id, board_position, settings, socket_type in DEVICE_SPECS:
        result.append(factory.create(DeviceInstanceCreate(
            model_id=model_id,
            instance_id=instance_id,
            label=label,
            board_position=board_position,
            settings=settings,
            socket_type_id=socket_type,
            installed_initially=True,
        )))
    return result


def build_circuit_and_operation():
    parts = fragments()
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
        indicators=[item for part in parts for item in part.indicators],
        motors=[
            OperationMotor(motor_id="M1", label="전동기 M1", forward_coil_id="MC1-COIL", phase_terminal_ids=["M1-U", "M1-V", "M1-W"], phase_source_terminal_ids=["PWR-L1", "PWR-L2", "PWR-L3"]),
            OperationMotor(motor_id="M2", label="전동기 M2", forward_coil_id="MC2-COIL", phase_terminal_ids=["M2-U", "M2-V", "M2-W"], phase_source_terminal_ids=["PWR-L1", "PWR-L2", "PWR-L3"]),
        ],
        contactors=[
            OperationContactor(contactor_id="MC1", label="MC1", coil_id="MC1-COIL", role="general", start_control_id="PB1", motor_id="M1"),
            OperationContactor(contactor_id="MC2", label="MC2", coil_id="MC2-COIL", role="general", start_control_id="PB2", motor_id="M2"),
        ],
        interlocks=[],
        protection_devices=[OperationProtectionDevice(
            protection_device_id="EOCR",
            label="EOCR",
            protected_coil_ids=["MC1-COIL", "MC2-COIL"],
            protected_motor_ids=["M1", "M2"],
            protection_contact_ids=["EOCR-TRIP-NC", "EOCR-TRIP-NO"],
            reset_mode="manual",
        )],
        internal_connections=[item for part in parts for item in part.intrinsic_connections],
    )
    return circuit, operation


def build_problem():
    problem = json.loads((PACKAGE / "problem.json").read_text(encoding="utf-8"))
    circuit, operation = build_circuit_and_operation()
    problem["description"] = "Q-Net 공개문제 010의 PDF 6~9쪽을 구조화한 비공개 기능검증 개발본입니다. 공식 FUSE 번호 근거가 없어 일반 사용자 채점과 동작시험은 계속 차단됩니다."
    problem["instructions"] = [
        "7쪽 공식 시퀀스 회로도를 확대해 확인하세요.",
        "6쪽 배치와 9쪽 내부결선도를 대조하세요.",
        "이 문제는 draft/unverified이며 일반 사용자 채점과 동작시험은 제공하지 않습니다.",
    ]
    problem["circuit"] = circuit.model_dump(mode="json", by_alias=True)
    problem["operation"] = operation.model_dump(mode="json", by_alias=True)
    problem["wiring_semantics"]["extra_jumper_policy"] = "reject"
    public_contact_types = {"PB0": "NC", "PB1": "NO", "PB2": "NO", "LS1": "NO", "LS2": "NO"}
    for device in problem["wiring_semantics"]["external_devices"]:
        if device["device_id"] in public_contact_types:
            device["contact_type"] = public_contact_types[device["device_id"]]
    return problem


def connection(connection_id: str, left: str, right: str, color: str = "yellow"):
    return {"connection_id": connection_id, "from": left, "to": right, "wire_color": color}


def canonical_connections():
    edges: list[tuple[str, str, str]] = []
    colors = {"P01_L1_IN": "brown", "P02_L2_IN": "black", "P03_L3_IN": "gray", "P05_L1_LOAD": "brown", "P06_L2_LOAD": "black", "P07_L3_LOAD": "gray", "P08_EOCR_U": "brown", "P09_EOCR_V": "black", "P10_EOCR_W": "gray", "P11_M1_U": "brown", "P12_M1_V": "black", "P13_M1_W": "gray", "P14_M2_U": "brown", "P15_M2_V": "black", "P16_M2_W": "gray"}
    special = {
        "P04_PE": [("PWR-PE", "TB5-05"), ("M1-PE", "TB5-05"), ("TB5-05", "TB5-06"), ("TB5-06", "M2-PE")],
        "C03_CONTROL_BUS": [("PB0-2", "TB5-01"), ("PB1-1", "TB5-01"), ("TB5-01", "TB5-02"), ("PB2-1", "TB5-02"), ("TB5-02", "X1-1"), ("X1-1", "X1-8"), ("X1-8", "X2-1"), ("X2-1", "X2-8"), ("X2-8", "MC1-4"), ("MC1-4", "MC2-4")],
        "C04_X1_RUN": [("PB1-2", "TB5-03"), ("TB5-03", "X1-3"), ("X1-3", "X1-2"), ("X1-2", "TB5-07"), ("TB5-07", "LS1-1"), ("TB5-07", "T1-1")],
        "C07_X2_RUN": [("PB2-2", "TB5-04"), ("TB5-04", "X2-3"), ("X2-3", "X2-2"), ("X2-2", "TB5-08"), ("TB5-08", "LS2-1"), ("TB5-08", "T2-1")],
        "C16_RETURN": [("WL-2", "TB6-01"), ("RL-2", "TB6-01"), ("TB6-01", "TB6-02"), ("TB6-01", "TB6-04"), ("GL-2", "TB6-02"), ("YL-2", "TB6-02"), ("TB6-02", "TB6-03"), ("TB6-03", "F-4"), ("F-4", "EOCR-A2"), ("EOCR-A2", "X1-7"), ("X1-7", "T1-7"), ("T1-7", "MC1-12"), ("TB6-04", "X2-7"), ("X2-7", "T2-7"), ("T2-7", "MC2-12")],
    }
    for net_id, terminals in EXPECTED_NETS:
        if net_id in special:
            edges.extend((left, right, "yellow") for left, right in special[net_id])
        else:
            color = colors.get(net_id, "yellow")
            edges.extend((terminals[index], terminals[index + 1], color) for index in range(len(terminals) - 1))
    return [connection(f"W-{index:03d}", left, right, color) for index, (left, right, color) in enumerate(edges, 1)]


def operation_tests():
    return [
        {"test_id": "PB1_TIMER_MC1", "label": "PB1·X1·LS1·T1·MC1·M1", "steps": [
            {"action": "set_power", "value": True, "expect": {"coils": {"X1-COIL": False, "MC1-COIL": False}, "motors": {"M1": "stopped"}}},
            {"action": "press_control", "control_id": "PB1", "expect": {"coils": {"X1-COIL": True}, "indicators": {"WL": "on"}}},
            {"action": "release_control", "control_id": "PB1", "expect": {"coils": {"X1-COIL": True}}},
            {"action": "press_control", "control_id": "LS1", "expect": {"coils": {"T1-COIL": True}, "timers": {"T1-TIMER": {"status": "timing"}}}},
            {"action": "advance_time", "milliseconds": 999, "expect": {"coils": {"MC1-COIL": False}, "motors": {"M1": "stopped"}}},
            {"action": "advance_time", "milliseconds": 1, "expect": {"coils": {"MC1-COIL": True}, "motors": {"M1": "forward"}, "indicators": {"RL": "on", "WL": "off"}}},
            {"action": "release_control", "control_id": "LS1", "expect": {"coils": {"T1-COIL": False, "MC1-COIL": False}, "motors": {"M1": "stopped"}, "indicators": {"RL": "off", "WL": "on"}}},
        ]},
        {"test_id": "PB2_TIMER_MC2", "label": "PB2·X2·LS2·T2·MC2·M2", "steps": [
            {"action": "set_power", "value": True},
            {"action": "press_control", "control_id": "PB2", "expect": {"coils": {"X2-COIL": True}, "indicators": {"WL": "on"}}},
            {"action": "release_control", "control_id": "PB2", "expect": {"coils": {"X2-COIL": True}}},
            {"action": "press_control", "control_id": "LS2", "expect": {"coils": {"T2-COIL": True}}},
            {"action": "advance_time", "milliseconds": 1000, "expect": {"coils": {"MC2-COIL": True}, "motors": {"M2": "forward"}, "indicators": {"GL": "on", "WL": "off"}}},
            {"action": "release_control", "control_id": "LS2", "expect": {"coils": {"MC2-COIL": False}, "motors": {"M2": "stopped"}, "indicators": {"GL": "off", "WL": "on"}}},
        ]},
        {"test_id": "STOP_BOTH", "label": "PB0 전체 정지", "steps": [
            {"action": "set_power", "value": True}, {"action": "press_control", "control_id": "PB1"}, {"action": "release_control", "control_id": "PB1"},
            {"action": "press_control", "control_id": "PB0", "expect": {"coils": {"X1-COIL": False, "T1-COIL": False, "MC1-COIL": False}, "motors": {"M1": "stopped", "M2": "stopped"}}},
        ]},
        {"test_id": "EOCR_TRIP_RESET", "label": "EOCR 트립·수동 리셋", "steps": [
            {"action": "set_power", "value": True}, {"action": "press_control", "control_id": "PB1"}, {"action": "release_control", "control_id": "PB1"},
            {"action": "trigger_fault", "target_id": "EOCR", "fault_type": "overload", "expect": {"coils": {"X1-COIL": False, "MC1-COIL": False}, "protections": {"EOCR": {"status": "reset_required"}}, "indicators": {"YL": "on"}}},
            {"action": "reset_fault", "target_id": "EOCR", "expect": {"protections": {"EOCR": {"status": "normal"}}, "indicators": {"YL": "off"}}},
        ]},
        {"test_id": "POWER_RESET", "label": "전원 차단 초기화", "steps": [
            {"action": "set_power", "value": True}, {"action": "press_control", "control_id": "PB1"}, {"action": "release_control", "control_id": "PB1"},
            {"action": "press_control", "control_id": "LS1"}, {"action": "advance_time", "milliseconds": 1000},
            {"action": "set_power", "value": False, "expect": {"powered": False, "coils": {"X1-COIL": False, "T1-COIL": False, "MC1-COIL": False}, "motors": {"M1": "power_off"}, "indicators": {"RL": "off", "WL": "off", "YL": "off"}}},
        ]},
    ]


def build_answer():
    answer = json.loads((PACKAGE / "answer.json").read_text(encoding="utf-8"))
    answer["answer_version"] = 2
    answer["verification"] = {
        "status": "unverified", "verified_by": None, "verified_at": None,
        "notes": "내부 자동검증용 개발 답안. FUSE 1-2/3-4는 사용자 제공 실기 명명이며 Q-Net 공식 단자번호가 아니므로 일반 채점과 동작시험은 차단한다.",
    }
    answer["expected_nets"] = [{"net_id": net_id, "terminals": terminals} for net_id, terminals in EXPECTED_NETS]
    answer["allowed_alternatives"] = [
        {"alternative_id": "X1_CONTACT_SWAP", "label": "X1 동등 전환접점 교환", "terminal_swaps": [{"left": ["X1-1", "X1-4", "X1-3"], "right": ["X1-8", "X1-5", "X1-6"]}]},
        {"alternative_id": "X2_CONTACT_SWAP", "label": "X2 동등 전환접점 교환", "terminal_swaps": [{"left": ["X2-1", "X2-4", "X2-3"], "right": ["X2-8", "X2-5", "X2-6"]}]},
        {"alternative_id": "T1_CONTACT_SWAP", "label": "T1 동등 계시접점 교환", "terminal_swaps": [{"left": ["T1-1", "T1-4", "T1-3"], "right": ["T1-8", "T1-5", "T1-6"]}]},
        {"alternative_id": "T2_CONTACT_SWAP", "label": "T2 동등 계시접점 교환", "terminal_swaps": [{"left": ["T2-1", "T2-4", "T2-3"], "right": ["T2-8", "T2-5", "T2-6"]}]},
    ]
    answer["wiring_connections"] = canonical_connections()
    answer["wiring_forbidden_connections"] = [
        {"from": "F-1", "to": "F-3"}, {"from": "F-1", "to": "F-4"}, {"from": "F-2", "to": "F-3"}, {"from": "F-2", "to": "F-4"},
        {"from": "PWR-L1", "to": "PWR-L2"}, {"from": "PWR-L1", "to": "PWR-L3"}, {"from": "PWR-L2", "to": "PWR-L3"},
    ]
    answer["operation_tests"] = operation_tests()
    return answer


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["problem", "answer"])
    args = parser.parse_args()
    payload = build_problem() if args.kind == "problem" else build_answer()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
