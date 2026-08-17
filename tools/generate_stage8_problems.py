from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROBLEMS = ROOT / "problems"
BASE = PROBLEMS / "operation_demo_001"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def copy_base(problem_id: str) -> Path:
    target = PROBLEMS / problem_id
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(BASE, target)
    return target


def terminal(terminal_id: str, device_id: str, pin: int, role: str, max_connections: int = 2) -> dict:
    return {
        "terminal_id": terminal_id,
        "device_id": device_id,
        "pin_number": pin,
        "terminal_type": "socket_pin",
        "electrical_role": role,
        "max_connections": max_connections,
        "enabled": True,
    }


def connection(index: int, source: str, target: str, color: str = "yellow") -> dict:
    return {"connection_id": f"W-{index:03d}", "from": source, "to": target, "wire_color": color}


def update_identity(target: Path, problem_id: str, title: str, tags: list[str]) -> tuple[dict, dict, dict]:
    manifest = read_json(target / "manifest.json")
    manifest.update(problem_id=problem_id, title=title, tags=["자체제작", *tags])
    manifest["source"] = {
        "type": "original",
        "name": "프로그램 논리 동작시험 검증용 자체 제작 문제",
        "reference": "Q-net 공개문제 원본 또는 실제 시험 정답이 아님",
        "verified_date": None,
    }
    problem = read_json(target / "problem.json")
    problem["problem_id"] = problem_id
    problem["description"] = f"{title}. 이 문제는 프로그램 기능 확인용 자체 제작 연습문제이며 Q-net 공개문제 원본이 아닙니다."
    problem["instructions"] = [
        "회로도 분석 결과를 참고하여 제어함을 결선합니다.",
        "정상 결선 제출 후 동작시험에서 버튼과 보호장치를 조작합니다.",
        "이 문제는 프로그램 기능 확인용 자체 제작 연습문제입니다.",
    ]
    answer = read_json(target / "answer.json")
    answer["problem_id"] = problem_id
    answer["verification"] = {
        "status": "reviewed",
        "verified_by": "0.8.2 자동 회귀시험",
        "verified_at": "2026-08-16T00:00:00+09:00",
        "notes": "프로그램 기능 확인용 자체 제작 정답이며 실제 시험 답안이 아닙니다.",
    }
    return manifest, problem, answer


def generate_forward_reverse() -> None:
    problem_id = "forward_reverse_interlock_demo_001"
    target = copy_base(problem_id)
    manifest, problem, answer = update_identity(
        target, problem_id, "정·역회전 자기유지·인터록·EOCR 연습", ["정역회전", "인터록", "EOCR"]
    )
    board = read_json(target / "board.json")
    for item in board["items"]:
        for pin in item["pins"]:
            if pin["terminal_id"] == "TB5-06":
                pin["max_connections"] = 6
    circuit = problem["circuit"]
    circuit["devices"].extend([
        {"device_id": "MC2", "device_type_id": "auxiliary_relay_12p", "label": "MC2", "socket_type_id": "socket_12p_base", "board_position": {"row": 2, "column": 2, "x": 0.6, "y": 0.65}, "installed_initially": True},
        {"device_id": "PB2", "device_type_id": "push_button", "label": "PB2", "socket_type_id": None, "board_position": {"row": 0, "column": 2, "x": 0.2, "y": 0.1}, "installed_initially": True},
    ])
    by_terminal = {item["terminal_id"]: item for item in circuit["terminals"]}
    by_terminal["TB5-06"]["max_connections"] = 6
    mc2_roles = {1: "line", 2: "line", 3: "line", 4: "contact_common", 5: "contact_common", 6: "coil", 7: "load", 8: "load", 9: "load", 10: "contact_no", 11: "contact_nc", 12: "coil"}
    circuit["terminals"] = list(by_terminal.values()) + [terminal(f"MC2-{number}", "MC2", number, role) for number, role in mc2_roles.items()]
    contacts = list(circuit["contacts"])
    contacts.extend([
        {"contact_id": "MC1-INTERLOCK", "owner_device_id": "MC1", "contact_type": "NC", "common_terminal_id": "MC1-5", "switched_terminal_id": "MC1-11", "nc_terminal_id": None, "no_terminal_id": None, "controlled_by_coil_id": "MC1-COIL", "normal_state": "closed"},
        {"contact_id": "MC2-HOLD", "owner_device_id": "MC2", "contact_type": "NO", "common_terminal_id": "MC2-4", "switched_terminal_id": "MC2-10", "nc_terminal_id": None, "no_terminal_id": None, "controlled_by_coil_id": "MC2-COIL", "normal_state": "open"},
        {"contact_id": "MC2-INTERLOCK", "owner_device_id": "MC2", "contact_type": "NC", "common_terminal_id": "MC2-5", "switched_terminal_id": "MC2-11", "nc_terminal_id": None, "no_terminal_id": None, "controlled_by_coil_id": "MC2-COIL", "normal_state": "closed"},
    ])
    circuit["contacts"] = contacts
    circuit["coils"].append({"coil_id": "MC2-COIL", "owner_device_id": "MC2", "terminal_a_id": "MC2-6", "terminal_b_id": "MC2-12", "rated_voltage": 220, "voltage_type": "AC", "frequency": 60})
    problem["device_layout"]["fixed_placements"] = [
        {"mount_device_id": "DEVICE-MC1", "label": "MC1 정회전 접촉기", "device_type_id": "auxiliary_relay_12p", "graphic_type": "contactor", "socket_id": "MC1", "socket_type_id": "socket_12p_base"},
        {"mount_device_id": "DEVICE-MC2", "label": "MC2 역회전 접촉기", "device_type_id": "auxiliary_relay_12p", "graphic_type": "contactor", "socket_id": "MC2", "socket_type_id": "socket_12p_base"},
    ]
    problem["operation"] = {
        "schema_version": "1.0", "simulation_status": "functional",
        "power": {"line_terminal_id": "TB5-04", "return_terminal_id": "TB6-01", "phase_terminal_ids": ["TB5-01", "TB5-02", "TB5-03"]},
        "controls": [
            {"control_id": "PB0", "label": "PB0 정지", "control_type": "pushbutton", "mode": "momentary", "contact_type": "NC", "terminal_a_id": "TB5-05", "terminal_b_id": "TB5-06", "initial_active": False},
            {"control_id": "PB1", "label": "PB1 정회전", "control_type": "pushbutton", "mode": "momentary", "contact_type": "NO", "terminal_a_id": "TB5-07", "terminal_b_id": "TB5-08", "initial_active": False},
            {"control_id": "PB2", "label": "PB2 역회전", "control_type": "pushbutton", "mode": "momentary", "contact_type": "NO", "terminal_a_id": "TB5-09", "terminal_b_id": "TB5-10", "initial_active": False},
        ],
        "timers": [],
        "indicators": [
            {"indicator_id": "RL", "label": "정회전 표시", "display_color": "red", "terminal_a_id": "MC1-6", "terminal_b_id": "MC1-12"},
            {"indicator_id": "GL", "label": "역회전 표시", "display_color": "green", "terminal_a_id": "MC2-6", "terminal_b_id": "MC2-12"},
        ],
        "motors": [{"motor_id": "M1", "label": "M1 모터", "forward_coil_id": "MC1-COIL", "reverse_coil_id": "MC2-COIL", "phase_terminal_ids": ["EOCR-U", "EOCR-V", "EOCR-W"], "phase_source_terminal_ids": ["TB5-01", "TB5-02", "TB5-03"], "forward_phase_order": [0, 1, 2]}],
        "contactors": [
            {"contactor_id": "MC1", "label": "MC1 정회전", "coil_id": "MC1-COIL", "role": "forward", "start_control_id": "PB1", "motor_id": "M1"},
            {"contactor_id": "MC2", "label": "MC2 역회전", "coil_id": "MC2-COIL", "role": "reverse", "start_control_id": "PB2", "motor_id": "M1"},
        ],
        "interlocks": [
            {"interlock_id": "ELEC-MC1-MC2", "label": "MC1·MC2 전기적 인터록", "type": "electrical", "contactor_ids": ["MC1", "MC2"], "contact_ids": ["MC1-INTERLOCK", "MC2-INTERLOCK"], "policy": "prevent_simultaneous_activation"},
            {"interlock_id": "MECH-MC1-MC2", "label": "MC1·MC2 기계적 인터록", "type": "mechanical", "contactor_ids": ["MC1", "MC2"], "contact_ids": [], "policy": "prevent_simultaneous_activation"},
        ],
        "protection_devices": [{"protection_device_id": "EOCR", "label": "EOCR", "protection_type": "eocr", "protected_coil_ids": ["MC1-COIL", "MC2-COIL"], "protected_motor_ids": ["M1"], "reset_mode": "manual", "allowed_fault_types": ["overload"]}],
        "direction_change_policy": "stop_before_reverse",
        "internal_connections": [{"from": "MCCB-L1", "to": "MCCB-T1"}, {"from": "MCCB-L2", "to": "MCCB-T2"}, {"from": "MCCB-L3", "to": "MCCB-T3"}, {"from": "F-1", "to": "F-2"}],
    }
    pairs = [
        ("TB5-01", "MCCB-L1", "brown"), ("TB5-02", "MCCB-L2", "black"), ("TB5-03", "MCCB-L3", "gray"),
        ("MCCB-T1", "EOCR-L1", "brown"), ("MCCB-T2", "EOCR-L2", "black"), ("MCCB-T3", "EOCR-L3", "gray"),
        ("TB5-04", "F-1", "yellow"), ("F-2", "TB5-05", "yellow"),
        ("TB5-06", "TB5-07", "yellow"), ("TB5-08", "MC2-5", "yellow"), ("MC2-11", "MC1-6", "yellow"), ("MC1-12", "TB6-01", "yellow"),
        ("TB5-06", "MC1-4", "yellow"), ("MC1-10", "TB5-08", "yellow"),
        ("TB5-06", "TB5-09", "yellow"), ("TB5-10", "MC1-5", "yellow"), ("MC1-11", "MC2-6", "yellow"), ("MC2-12", "TB6-01", "yellow"),
        ("TB5-06", "MC2-4", "yellow"), ("MC2-10", "TB5-10", "yellow"),
    ]
    answer["wiring_connections"] = [connection(index, a, b, color) for index, (a, b, color) in enumerate(pairs, 1)]
    answer["operation_tests"] = [
        {"test_id": "FORWARD_HOLD_INTERLOCK", "label": "정회전 자기유지와 역방향 차단", "steps": [
            {"action": "set_power", "value": True},
            {"action": "press_control", "control_id": "PB1", "expect": {"coils": {"MC1-COIL": True}, "motors": {"M1": "forward"}}},
            {"action": "release_control", "control_id": "PB1", "expect": {"coils": {"MC1-COIL": True}}},
            {"action": "press_control", "control_id": "PB2", "expect": {"coils": {"MC2-COIL": False}, "motors": {"M1": "forward"}}},
            {"action": "press_control", "control_id": "PB0", "expect": {"coils": {"MC1-COIL": False}, "motors": {"M1": "stopped"}}},
        ]},
        {"test_id": "REVERSE_AND_EOCR", "label": "역회전과 EOCR 트립·복귀", "steps": [
            {"action": "set_power", "value": True},
            {"action": "press_control", "control_id": "PB2", "expect": {"coils": {"MC2-COIL": True}, "motors": {"M1": "reverse"}}},
            {"action": "release_control", "control_id": "PB2", "expect": {"coils": {"MC2-COIL": True}}},
            {"action": "trigger_fault", "target_id": "EOCR", "fault_type": "overload", "expect": {"coils": {"MC2-COIL": False}, "motors": {"M1": "protection_trip"}, "protections": {"EOCR": {"status": "reset_required"}}}},
            {"action": "reset_fault", "target_id": "EOCR", "expect": {"protections": {"EOCR": {"status": "normal"}}, "motors": {"M1": "stopped"}}},
        ]},
    ]
    write_json(target / "manifest.json", manifest)
    write_json(target / "problem.json", problem)
    write_json(target / "answer.json", answer)
    write_json(target / "board.json", board)
    (target / "schematic.svg").write_text((target / "schematic.svg").read_text(encoding="utf-8").replace("가상 소켓번호 입력 기능 확인", "정·역회전 인터록 기능 확인"), encoding="utf-8")


def generate_eocr_sequence() -> None:
    problem_id = "eocr_sequence_demo_001"
    target = copy_base(problem_id)
    manifest, problem, answer = update_identity(target, problem_id, "자기유지·타이머·EOCR 보호 연습", ["자기유지", "타이머", "EOCR"])
    problem["operation"]["contactors"] = [{"contactor_id": "MC1", "label": "MC1", "coil_id": "MC1-COIL", "role": "forward", "start_control_id": "PB1", "motor_id": "M1"}]
    problem["operation"]["interlocks"] = []
    problem["operation"]["protection_devices"] = [{"protection_device_id": "EOCR", "label": "EOCR", "protection_type": "eocr", "protected_coil_ids": ["MC1-COIL", "T1-COIL"], "protected_motor_ids": ["M1"], "reset_mode": "manual", "allowed_fault_types": ["overload"]}]
    problem["operation"]["direction_change_policy"] = "block_both"
    answer["operation_tests"].append({"test_id": "EOCR_TRIP_RESET", "label": "EOCR 트립과 수동 복귀", "steps": [
        {"action": "set_power", "value": True},
        {"action": "press_control", "control_id": "PB1", "expect": {"coils": {"MC1-COIL": True}, "motors": {"M1": "forward"}}},
        {"action": "release_control", "control_id": "PB1"},
        {"action": "trigger_fault", "target_id": "EOCR", "fault_type": "overload", "expect": {"coils": {"MC1-COIL": False}, "motors": {"M1": "protection_trip"}}},
        {"action": "reset_fault", "target_id": "EOCR", "expect": {"protections": {"EOCR": {"status": "normal"}}, "motors": {"M1": "stopped"}}},
    ]})
    write_json(target / "manifest.json", manifest)
    write_json(target / "problem.json", problem)
    write_json(target / "answer.json", answer)
    (target / "schematic.svg").write_text((target / "schematic.svg").read_text(encoding="utf-8").replace("가상 소켓번호 입력 기능 확인", "타이머·EOCR 기능 확인"), encoding="utf-8")


def main() -> None:
    generate_forward_reverse()
    generate_eocr_sequence()
    print("0.8.2 자체 제작 문제 2개를 생성했습니다.")


if __name__ == "__main__":
    main()
