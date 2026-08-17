from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROBLEMS = ROOT / "problems"
EOCR_SUFFIXES = {1: "L1", 2: "L2", 3: "L3", 4: "96", 5: "98", 6: "A1", 7: "U", 8: "V", 9: "W", 10: "95", 11: "97", 12: "A2"}
MC_ROLES = {1: "L1", 2: "L2", 3: "L3", 4: "a1", 5: "b1", 6: "A1", 7: "U", 8: "V", 9: "W", 10: "a2", 11: "b2", 12: "A2"}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def board_pin(terminal_id: str, number: int, side: str, x: float, y: float, role: str) -> dict:
    return {
        "terminal_id": terminal_id,
        "label": str(number),
        "role_label": role,
        "number": number,
        "side": side,
        "x": round(x, 2),
        "y": y,
        "max_connections": 2,
        "enabled": True,
    }


def update_board(path: Path) -> None:
    board = read_json(path)
    for item in board["items"]:
        if item["item_id"] == "EOCR":
            item.update(item_type="socket_12p", socket_type_id="socket_12p_base", x=280, y=200, width=220, height=170)
            pins = []
            for side, numbers, y in (("top", range(1, 7), 200), ("bottom", range(7, 13), 370)):
                for index, number in enumerate(numbers):
                    suffix = EOCR_SUFFIXES[number]
                    pins.append(board_pin(f"EOCR-{suffix}", number, side, 280 + 220 * (index + 0.5) / 6, y, suffix))
            item["pins"] = pins
            item["label_area"] = {"x": 328.4, "y": 252.7, "width": 123.2, "height": 64.6}
        elif item["item_id"] in {"MC1", "MC2"}:
            for pin in item["pins"]:
                if pin["number"] in MC_ROLES:
                    pin["role_label"] = MC_ROLES[pin["number"]]
    write_json(path, board)


def circuit_terminal(device_id: str, number: int, role: str) -> dict:
    return {
        "terminal_id": f"{device_id}-{number}",
        "device_id": device_id,
        "pin_number": number,
        "terminal_type": "socket_pin",
        "electrical_role": role,
        "max_connections": 2,
        "enabled": True,
    }


def contactor_terminals(device_id: str) -> list[dict]:
    roles = {1: "line", 2: "line", 3: "line", 4: "contact_common", 5: "contact_common", 6: "coil", 7: "load", 8: "load", 9: "load", 10: "contact_no", 11: "contact_nc", 12: "coil"}
    return [circuit_terminal(device_id, number, role) for number, role in roles.items()]


def ensure_eocr_circuit(circuit: dict) -> None:
    if not any(item["device_id"] == "EOCR" for item in circuit["devices"]):
        circuit["devices"].append({
            "device_id": "EOCR", "device_type_id": "eocr", "label": "EOCR",
            "socket_type_id": "socket_12p_base",
            "board_position": {"row": 1, "column": 1, "x": 0.28, "y": 0.3},
            "installed_initially": True,
        })
    circuit["terminals"] = [item for item in circuit["terminals"] if item["device_id"] != "EOCR" and not item["terminal_id"].startswith("EOCR-")]
    roles = {1: "line", 2: "line", 3: "line", 4: "contact_nc", 5: "contact_no", 6: "coil", 7: "load", 8: "load", 9: "load", 10: "contact_common", 11: "contact_common", 12: "coil"}
    for number, role in roles.items():
        suffix = EOCR_SUFFIXES[number]
        circuit["terminals"].append({
            "terminal_id": f"EOCR-{suffix}", "device_id": "EOCR", "pin_number": number,
            "terminal_type": "socket_pin", "electrical_role": role,
            "max_connections": 2, "enabled": True,
        })


def set_contactor_circuit(circuit: dict, device_ids: list[str], with_interlock: bool) -> None:
    circuit["terminals"] = [item for item in circuit["terminals"] if item["device_id"] not in device_ids]
    for device_id in device_ids:
        circuit["terminals"].extend(contactor_terminals(device_id))
    circuit["contacts"] = [item for item in circuit["contacts"] if item["owner_device_id"] not in device_ids]
    for device_id in device_ids:
        circuit["contacts"].append({
            "contact_id": f"{device_id}-HOLD", "owner_device_id": device_id,
            "contact_type": "NO", "common_terminal_id": f"{device_id}-4",
            "switched_terminal_id": f"{device_id}-10", "controlled_by_coil_id": f"{device_id}-COIL",
            "normal_state": "open",
        })
        if with_interlock:
            circuit["contacts"].append({
                "contact_id": f"{device_id}-INTERLOCK", "owner_device_id": device_id,
                "contact_type": "NC", "common_terminal_id": f"{device_id}-5",
                "switched_terminal_id": f"{device_id}-11", "controlled_by_coil_id": f"{device_id}-COIL",
                "normal_state": "closed",
            })
    for coil in circuit["coils"]:
        if coil["owner_device_id"] in device_ids:
            coil["terminal_a_id"] = f"{coil['owner_device_id']}-6"
            coil["terminal_b_id"] = f"{coil['owner_device_id']}-12"


def set_eocr_internal_connections(operation: dict) -> None:
    internal = [item for item in operation["internal_connections"] if not item["from"].startswith("EOCR-") and not item["to"].startswith("EOCR-")]
    internal.extend([
        {"from": "EOCR-L1", "to": "EOCR-U"},
        {"from": "EOCR-L2", "to": "EOCR-V"},
        {"from": "EOCR-L3", "to": "EOCR-W"},
    ])
    operation["internal_connections"] = internal


def fix_8p_timer_contact(circuit: dict) -> None:
    for terminal in circuit["terminals"]:
        if terminal["terminal_id"] == "T1-6":
            terminal["terminal_id"] = "T1-1"
            terminal["pin_number"] = 1
            terminal["electrical_role"] = "contact_common"
    for contact in circuit["contacts"]:
        if contact["contact_id"] == "T1-C1":
            contact["common_terminal_id"] = "T1-1"
            contact["switched_terminal_id"] = "T1-3"


def wire(index: int, source: str, target: str, color: str = "yellow") -> dict:
    return {"connection_id": f"W-{index:03d}", "from": source, "to": target, "wire_color": color}


def update_base_operation(problem_id: str) -> None:
    folder = PROBLEMS / problem_id
    problem = read_json(folder / "problem.json")
    answer = read_json(folder / "answer.json")
    circuit = problem["circuit"]
    ensure_eocr_circuit(circuit)
    set_contactor_circuit(circuit, ["MC1"], with_interlock=False)
    fix_8p_timer_contact(circuit)
    set_eocr_internal_connections(problem["operation"])
    pairs = [
        ("TB5-01", "MCCB-L1", "brown"), ("TB5-02", "MCCB-L2", "black"), ("TB5-03", "MCCB-L3", "gray"),
        ("MCCB-T1", "EOCR-L1", "brown"), ("MCCB-T2", "EOCR-L2", "black"), ("MCCB-T3", "EOCR-L3", "gray"),
        ("TB5-04", "F-1", "yellow"), ("F-2", "TB5-05", "yellow"),
        ("TB5-06", "TB5-07", "yellow"), ("TB5-08", "MC1-6", "yellow"), ("MC1-12", "TB6-01", "yellow"),
        ("TB5-06", "MC1-4", "yellow"), ("MC1-10", "MC1-6", "yellow"),
        ("MC1-10", "T1-2", "yellow"), ("T1-7", "MC1-12", "yellow"),
        ("TB5-07", "T1-1", "yellow"), ("T1-3", "TB6-02", "yellow"), ("TB6-03", "T1-7", "yellow"),
    ]
    answer["wiring_connections"] = [wire(index, *pair) for index, pair in enumerate(pairs, 1)]
    write_json(folder / "problem.json", problem)
    write_json(folder / "answer.json", answer)


def update_forward_reverse() -> None:
    folder = PROBLEMS / "forward_reverse_interlock_demo_001"
    problem = read_json(folder / "problem.json")
    answer = read_json(folder / "answer.json")
    circuit = problem["circuit"]
    ensure_eocr_circuit(circuit)
    set_contactor_circuit(circuit, ["MC1", "MC2"], with_interlock=True)
    fix_8p_timer_contact(circuit)
    set_eocr_internal_connections(problem["operation"])
    for indicator in problem["operation"]["indicators"]:
        device_id = "MC1" if indicator["indicator_id"] == "RL" else "MC2"
        indicator["terminal_a_id"] = f"{device_id}-6"
        indicator["terminal_b_id"] = f"{device_id}-12"
    pairs = [
        ("TB5-01", "MCCB-L1", "brown"), ("TB5-02", "MCCB-L2", "black"), ("TB5-03", "MCCB-L3", "gray"),
        ("MCCB-T1", "EOCR-L1", "brown"), ("MCCB-T2", "EOCR-L2", "black"), ("MCCB-T3", "EOCR-L3", "gray"),
        ("TB5-04", "F-1", "yellow"), ("F-2", "TB5-05", "yellow"),
        ("TB5-06", "TB5-07", "yellow"), ("TB5-08", "MC2-5", "yellow"), ("MC2-11", "MC1-6", "yellow"), ("MC1-12", "TB6-01", "yellow"),
        ("TB5-07", "MC1-4", "yellow"), ("MC1-10", "TB5-08", "yellow"),
        ("TB5-06", "TB5-09", "yellow"), ("TB5-10", "MC1-5", "yellow"), ("MC1-11", "MC2-6", "yellow"), ("MC2-12", "TB6-01", "yellow"),
        ("TB5-09", "MC2-4", "yellow"), ("MC2-10", "TB5-10", "yellow"),
    ]
    answer["wiring_connections"] = [wire(index, *pair) for index, pair in enumerate(pairs, 1)]
    write_json(folder / "problem.json", problem)
    write_json(folder / "answer.json", answer)


def main() -> None:
    for board_path in PROBLEMS.glob("*/board.json"):
        if any(item["item_id"] == "EOCR" for item in read_json(board_path)["items"]):
            update_board(board_path)
    update_base_operation("operation_demo_001")
    update_base_operation("eocr_sequence_demo_001")
    update_forward_reverse()
    print("EOCR·MC 소켓 역할과 동작시험 배선을 갱신했습니다.")


if __name__ == "__main__":
    main()
