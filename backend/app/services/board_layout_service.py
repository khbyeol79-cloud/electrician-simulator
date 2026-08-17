from __future__ import annotations

from collections import defaultdict

from app.domain.board_definition import BoardDefinition, BoardItem


MINIMUM_ITEM_GAP = 24.0


def _horizontal_bounds(board: BoardDefinition) -> tuple[float, float]:
    terminal_blocks = [item for item in board.items if item.item_type == "terminal_block"]
    if terminal_blocks:
        left = max(item.x for item in terminal_blocks)
        right = min(item.x + item.width for item in terminal_blocks)
        if right > left:
            return left, right
    return board.routing_margin, board.width - board.routing_margin


def _move_item(item: BoardItem, x: float, y: float) -> tuple[float, float]:
    dx = x - item.x
    dy = y - item.y
    item.x = round(x, 2)
    item.y = round(y, 2)
    for pin in item.pins:
        pin.x = round(pin.x + dx, 2)
        pin.y = round(pin.y + dy, 2)
    item.label_area.x = round(item.label_area.x + dx, 2)
    item.label_area.y = round(item.label_area.y + dy, 2)
    return dx, dy


def align_board_rows(board: BoardDefinition) -> BoardDefinition:
    """행과 좌우 순서를 유지하며 장치를 단자대 안쪽에 균등 정렬한다."""
    if board.layout_mode == "fixed":
        return board

    aligned = board.model_copy(deep=True)
    left_bound, right_bound = _horizontal_bounds(aligned)
    inner_left = left_bound + aligned.routing_margin
    inner_right = right_bound - aligned.routing_margin
    available_width = inner_right - inner_left

    rows: dict[int, list[BoardItem]] = defaultdict(list)
    for item in aligned.items:
        if item.item_type != "terminal_block":
            rows[item.row].append(item)

    shifts: dict[str, tuple[float, float]] = {}
    for items in rows.values():
        items.sort(key=lambda item: item.x)
        total_width = sum(item.width for item in items)
        if not items or total_width > available_width:
            continue
        center_y = sum(item.y + item.height / 2 for item in items) / len(items)
        if len(items) == 1:
            positions = [inner_left + (available_width - items[0].width) / 2]
        else:
            gap = (available_width - total_width) / (len(items) - 1)
            if gap < MINIMUM_ITEM_GAP:
                continue
            positions = []
            cursor = inner_left
            for item in items:
                positions.append(cursor)
                cursor += item.width + gap
        for item, x in zip(items, positions, strict=True):
            y = center_y - item.height / 2
            shifts[item.item_id] = _move_item(item, x, y)

    for area in aligned.forbidden_areas:
        item_id = area.area_id.removesuffix("_body")
        shift = shifts.get(item_id)
        if shift:
            area.x = round(area.x + shift[0], 2)
            area.y = round(area.y + shift[1], 2)
    return aligned
