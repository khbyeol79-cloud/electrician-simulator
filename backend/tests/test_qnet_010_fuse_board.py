from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_qnet_010_keeps_one_fuse_device_with_four_wire_endpoints():
    board = json.loads(
        (PROJECT_ROOT / "problems" / "qnet_electrician_practical_010" / "board.json").read_text(encoding="utf-8")
    )
    fuse_items = [item for item in board["items"] if item.get("item_id") == "F"]
    assert len(fuse_items) == 1
    pins = fuse_items[0]["pins"]
    assert {pin["terminal_id"] for pin in pins} == {"F-1", "F-2", "F-3", "F-4"}
    assert {pin["number"] for pin in pins} == {1, 2, 3, 4}
    assert all(pin["enabled"] for pin in pins)
    assert board["layout_mode"] == "fixed"


def test_qnet_010_fixed_device_labels_do_not_overlap():
    board = json.loads(
        (PROJECT_ROOT / "problems" / "qnet_electrician_practical_010" / "board.json").read_text(encoding="utf-8")
    )
    labels = [item["label_area"] for item in board["items"] if item["item_type"] != "terminal_block"]
    for index, left in enumerate(labels):
        for right in labels[index + 1:]:
            separated = (
                left["x"] + left["width"] <= right["x"] or right["x"] + right["width"] <= left["x"]
                or left["y"] + left["height"] <= right["y"] or right["y"] + right["height"] <= left["y"]
            )
            assert separated


def test_qnet_010_fuse_pin_geometry_matches_two_vertical_cartridges():
    board = json.loads(
        (PROJECT_ROOT / "problems" / "qnet_electrician_practical_010" / "board.json").read_text(encoding="utf-8")
    )
    fuse = next(item for item in board["items"] if item.get("item_id") == "F")
    pins = {pin["terminal_id"]: pin for pin in fuse["pins"]}
    assert pins["F-1"]["x"] == pins["F-2"]["x"]
    assert pins["F-3"]["x"] == pins["F-4"]["x"]
    assert pins["F-1"]["y"] < pins["F-2"]["y"]
    assert pins["F-3"]["y"] < pins["F-4"]["y"]
    assert pins["F-1"]["x"] < pins["F-3"]["x"]


def test_qnet_010_fuse_uses_compact_center_label_for_dual_cartridge_graphic():
    board = json.loads(
        (PROJECT_ROOT / "problems" / "qnet_electrician_practical_010" / "board.json").read_text(encoding="utf-8")
    )
    fuse = next(item for item in board["items"] if item.get("item_id") == "F")
    assert fuse["label"] == "F"
    assert fuse["label_area"]["width"] <= 30
    assert fuse["label_area"]["height"] <= 24
