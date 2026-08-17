from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def rect(x, y, width, height):
    return {"x": x, "y": y, "width": width, "height": height}


def pin(terminal_id, label, number, side, x, y, max_connections=2, role_label=None):
    result = {"terminal_id": terminal_id, "label": label, "number": number, "side": side, "x": x, "y": y, "max_connections": max_connections, "enabled": True}
    if role_label is not None:
        result["role_label"] = role_label
    return result


def socket(item_id, label, socket_type, row, x, y, width, height, terminal_ids=None, role_labels=None):
    if socket_type == "socket_8p_base":
        top, bottom, item_type = [6, 5, 4, 3], [7, 8, 1, 2], "socket_8p"
    else:
        top, bottom, item_type = [1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12], "socket_12p"
    pins = []
    for side, numbers, py in (("top", top, y), ("bottom", bottom, y + height)):
        for index, number in enumerate(numbers):
            px = x + width * (index + 0.5) / len(numbers)
            terminal_suffix = (terminal_ids or {}).get(number, str(number))
            pins.append(pin(f"{item_id}-{terminal_suffix}", str(number), number, side, round(px, 2), py, role_label=(role_labels or {}).get(number)))
    return {
        "item_id": item_id, "label": label, "item_type": item_type, "socket_type_id": socket_type,
        "row": row, "x": x, "y": y, "width": width, "height": height, "pins": pins,
        "label_area": rect(x + width * .22, y + height * .31, width * .56, height * .38),
    }


def terminal_block(item_id, label, row, x, y, width, count, side):
    pins = [pin(f"{item_id}-{index:02d}", str(index), None, side, round(x + width * (index - .5) / count, 2), y if side == "top" else y + 70, 3) for index in range(1, count + 1)]
    return {"item_id": item_id, "label": label, "item_type": "terminal_block", "socket_type_id": None, "row": row, "x": x, "y": y, "width": width, "height": 70, "pins": pins, "label_area": rect(x + width * .39, y + 20, width * .22, 30)}


def component(item_id, label, row, x, y, width, labels):
    top_labels, bottom_labels = labels
    pins = []
    for side, values, py in (("top", top_labels, y), ("bottom", bottom_labels, y + 150)):
        for index, value in enumerate(values):
            px = x + width * (index + .5) / len(values)
            pins.append(pin(f"{item_id}-{value}", value, None, side, round(px, 2), py))
    return {"item_id": item_id, "label": label, "item_type": "component", "socket_type_id": None, "row": row, "x": x, "y": y, "width": width, "height": 150, "pins": pins, "label_area": rect(x + 22, y + 54, width - 44, 42)}


def base(board_id, items):
    return {
        "schema_version": "1.0", "board_id": board_id, "width": 1400, "height": 900, "routing_margin": 36,
        "items": items,
        "routing_channels": [
            {"channel_id": "top_lane", "channel_type": "horizontal", **rect(45, 145, 1310, 35)},
            {"channel_id": "middle_lane", "channel_type": "horizontal", **rect(45, 425, 1310, 35)},
            {"channel_id": "bottom_lane", "channel_type": "horizontal", **rect(45, 735, 1310, 35)},
            {"channel_id": "left_outer", "channel_type": "left_outer", **rect(20, 30, 35, 835)},
            {"channel_id": "right_outer", "channel_type": "right_outer", **rect(1345, 30, 35, 835)},
        ],
        "forbidden_areas": [{"area_id": f"{item['item_id']}_body", **rect(item["x"], item["y"], item["width"], item["height"])} for item in items],
    }


training_items = [
    terminal_block("TB5", "TB5 (10P+10P)", 0, 110, 45, 1180, 20, "bottom"),
    component("MCCB", "MCCB", 1, 90, 210, 160, (["L1", "L2", "L3"], ["T1", "T2", "T3"])),
    socket("EOCR", "EOCR", "socket_12p_base", 1, 280, 200, 220, 170,
           {1: "L1", 2: "L2", 3: "L3", 4: "96", 5: "98", 6: "A1", 7: "U", 8: "V", 9: "W", 10: "95", 11: "97", 12: "A2"},
           {1: "L1", 2: "L2", 3: "L3", 4: "96", 5: "98", 6: "A1", 7: "U", 8: "V", 9: "W", 10: "95", 11: "97", 12: "A2"}),
    component("F", "FUSE", 1, 510, 210, 120, (["1"], ["2"])),
    socket("X1", "X1", "socket_8p_base", 1, 700, 200, 180, 170),
    socket("X2", "X2", "socket_8p_base", 1, 990, 200, 180, 170),
    socket("T2", "T2", "socket_8p_base", 2, 90, 500, 180, 170),
    socket("MC1", "MC1", "socket_12p_base", 2, 350, 500, 220, 170, role_labels={1: "L1", 2: "L2", 3: "L3", 4: "a1", 5: "b1", 6: "A1", 7: "U", 8: "V", 9: "W", 10: "a2", 11: "b2", 12: "A2"}),
    socket("MC2", "MC2", "socket_12p_base", 2, 680, 500, 220, 170, role_labels={1: "L1", 2: "L2", 3: "L3", 4: "a1", 5: "b1", 6: "A1", 7: "U", 8: "V", 9: "W", 10: "a2", 11: "b2", 12: "A2"}),
    socket("T1", "T1", "socket_8p_base", 2, 1010, 500, 180, 170),
    terminal_block("TB6", "TB6 (10P+10P)", 3, 110, 785, 1180, 20, "top"),
]

practice_items = [
    terminal_block("TB-A", "연습 상단 단자대", 0, 260, 80, 880, 12, "bottom"),
    socket("X3", "X3 · 12P", "socket_12p_base", 1, 590, 330, 220, 180),
    terminal_block("TB-B", "연습 하단 단자대", 2, 260, 720, 880, 12, "top"),
]

outputs = {
    ROOT / "problems" / "training_socket_demo_001" / "board.json": base("training_wiring_board_v1", training_items),
    ROOT / "problems" / "practice_001" / "board.json": base("practice_board_v1", practice_items),
    ROOT / "problems" / "_template" / "board.json": base("template_board_v1", practice_items),
}
for path, data in outputs.items():
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path.relative_to(ROOT))
