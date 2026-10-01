"""Extract clickable terminal-pair geometry (not answers) from official raster diagrams.

Offline authoring tool: requires opencv-python-headless and numpy. Generated geometry
is shipped with the frontend; neither dependency is needed by the application.
"""
import base64
import json
import re
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def extract(path):
    image = cv2.imdecode(np.frombuffer(base64.b64decode(re.search(r'base64,([^\"]+)', path.read_text())[1]), np.uint8), 0)
    contours, _ = cv2.findContours(cv2.threshold(image, 150, 255, cv2.THRESH_BINARY)[1], cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    rings = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if 7 <= w <= 12 and 7 <= h <= 12 and abs(w - h) <= 2 and 300 <= y <= 1150 and cv2.contourArea(contour) / (w * h) > .48:
            rings.append((x + w / 2, y + h / 2))
    targets = {}
    for x, y in rings:
        for xx, yy in rings:
            orientation = 'vertical' if abs(x - xx) < 2 and 32 <= yy - y <= 52 else 'horizontal' if abs(y - yy) < 2 and 32 <= xx - x <= 52 else None
            if orientation:
                cx, cy = round((x + xx) / 2, 1), round((y + yy) / 2, 1)
                key = f'contact:{cx}:{cy}'
                targets[key] = dict(id=key, x=cx, y=cy, orientation=orientation)
    # Lower control-circuit row: coil/lamp circles and the buzzer square have
    # the same ~52px outline. Keep contact IDs/order stable for saved annotations.
    bodies = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if x > 650 and 900 < y < 1250 and 47 <= w <= 57 and 47 <= h <= 57 and abs(w-h) <= 3:
            bodies.append((round(x+w/2, 1), round(y+h/2, 1)))
    row = max(bodies, key=lambda p: sum(abs(q[1]-p[1]) < 4 for q in bodies))[1] if bodies else None
    body_targets = {f'contact:body:{x}:{y}': dict(id=f'contact:body:{x}:{y}', x=x, y=y, orientation='vertical', kind='body')
                    for x, y in bodies if abs(y-row) < 4}
    return sorted(targets.values(), key=lambda item: (item['y'], item['x'])) + sorted(body_targets.values(), key=lambda item: item['x'])


if __name__ == '__main__':
    data = {f'qnet_electrician_practical_{n:03}': extract(ROOT / f'problems/qnet_electrician_practical_{n:03}/schematic.svg') for n in range(1, 19)}
    (ROOT / 'frontend/src/features/circuit/contactHotspots.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print({key[-3:]: len(value) for key, value in data.items()})
