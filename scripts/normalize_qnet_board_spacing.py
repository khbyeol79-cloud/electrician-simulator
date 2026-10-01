"""Equal edge-to-edge gaps without changing audited PDF rows/order or terminal IDs."""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def normalize(board):
    blocks = [item for item in board['items'] if item['item_type'] == 'terminal_block']
    left = max(item['x'] for item in blocks) + board['routing_margin']
    right = min(item['x'] + item['width'] for item in blocks) - board['routing_margin']
    rows = defaultdict(list)
    for item in board['items']:
        if item['item_type'] != 'terminal_block':
            rows[item['row']].append(item)
    gap = min((right - left - sum(item['width'] for item in row)) / (len(row) - 1) for row in rows.values() if len(row) > 1)
    assert gap >= 24, 'Board cannot fit with safe device spacing'
    shifts = {}
    for row in rows.values():
        row.sort(key=lambda item: item['x'])
        cursor = (left + right - sum(item['width'] for item in row) - gap * (len(row) - 1)) / 2
        center = min(item['y'] for item in row) + max(item['height'] for item in row) / 2
        for item in row:
            dx, dy = cursor - item['x'], center - item['height'] / 2 - item['y']
            for part in [item, item['label_area'], *item['pins']]:
                part['x'] = round(part['x'] + dx, 2)
                part['y'] = round(part['y'] + dy, 2)
            shifts[item['item_id'] + '_body'] = (dx, dy)
            cursor += item['width'] + gap
    for area in board['forbidden_areas']:
        dx, dy = shifts.get(area['area_id'], (0, 0))
        area['x'], area['y'] = round(area['x'] + dx, 2), round(area['y'] + dy, 2)
    return board


if __name__ == '__main__':
    for n in range(1, 19):
        path = ROOT / f'problems/qnet_electrician_practical_{n:03}/board.json'
        board = normalize(json.loads(path.read_text(encoding='utf-8')))
        path.write_text(json.dumps(board, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'{n:03}: rows/order/IDs preserved; spacing normalized')
