"""Q-Net 공개문제 PDF 18개를 검증 대기 문제 패키지로 가져온다.

이 스크립트는 PDF 6~9쪽의 공식 배치·회로·동작·내부결선 근거를 추적 가능한
형태로 저장한다. expected_nets나 동작 정의를 추측하지 않으며, 생성 답안은
항상 unverified이다.
"""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROBLEMS = ROOT / "problems"
BOARD_TEMPLATE = PROBLEMS / "forward_reverse_interlock_demo_001" / "board.json"

TITLES = {
    "001": "수위 자동·수동 운전과 순차 기동",
    "002": "수위 자동·수동 운전과 교대 운전",
    "003": "플리커 교대 운전과 지연 기동",
    "004": "교대 운전과 타이머 정지 구간",
    "005": "교대 운전 후 두 전동기 동시 운전",
    "006": "동시 운전 후 플리커 교대 운전",
    "007": "타이머·플리커 3단 반복 운전",
    "008": "수위 운전 표시와 한시 정지",
    "009": "수위 운전·순차 기동·플리커 경보",
    "010": "릴레이 허가와 리밋·타이머 기동",
    "011": "타이머 자기유지와 상호 전환",
    "012": "리밋 조건에 따른 두 전동기 연계",
    "013": "리밋 순간감지와 한시 연계 운전",
    "014": "리밋 논리와 한시 전동기 운전",
    "015": "리밋 OR·AND 조건 전동기 운전",
    "016": "리밋 허가와 타이머 연계 운전",
    "017": "배타 리밋 조건과 순차 허가",
    "018": "리밋 조건 자기유지와 지연 표시",
}

LAYOUTS = {
    "001": (["F", "EOCR", "MCCB", "X", "FR"], ["T", "FLS", "MC1", "MC2"]),
    "002": (["EOCR", "MCCB", "F", "X", "FR"], ["MC1", "MC2", "T", "FLS"]),
    "003": (["MCCB", "EOCR", "F", "X", "FR"], ["T", "FLS", "MC1", "MC2"]),
    "004": (["MCCB", "EOCR", "FR", "X", "F"], ["FLS", "MC1", "MC2", "T"]),
    "005": (["EOCR", "F", "MCCB", "FR", "X"], ["MC1", "MC2", "FLS", "T"]),
    "006": (["EOCR", "MCCB", "F", "X", "FR"], ["FLS", "T", "MC1", "MC2"]),
    "007": (["MCCB", "F", "EOCR", "FR", "X"], ["FLS", "T", "MC1", "MC2"]),
    "008": (["F", "MCCB", "EOCR", "X", "FR"], ["T", "MC1", "MC2", "FLS"]),
    "009": (["MCCB", "EOCR", "F", "FR", "X"], ["T", "MC1", "MC2", "FLS"]),
    "010": (["MCCB", "EOCR", "X2", "X1", "F"], ["T1", "T2", "MC1", "MC2"]),
    "011": (["EOCR", "MCCB", "F", "X2", "X1"], ["MC1", "MC2", "T2", "T1"]),
    "012": (["F", "MCCB", "EOCR", "X1", "X2"], ["T2", "T1", "MC1", "MC2"]),
    "013": (["EOCR", "MCCB", "F", "X1", "X2"], ["T1", "MC1", "MC2", "T2"]),
    "014": (["F", "MCCB", "EOCR", "X2", "X1"], ["T2", "T1", "MC1", "MC2"]),
    "015": (["MCCB", "EOCR", "F", "X2", "X1"], ["T2", "MC1", "MC2", "T1"]),
    "016": (["MCCB", "EOCR", "X1", "X2", "F"], ["T2", "MC1", "MC2", "T1"]),
    "017": (["MCCB", "F", "EOCR", "X1", "X2"], ["T1", "MC1", "MC2", "T2"]),
    "018": (["MCCB", "EOCR", "F", "X1", "X2"], ["T2", "MC1", "MC2", "T1"]),
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def page_count(path: Path) -> int:
    output = subprocess.run(["pdfinfo", str(path)], check=True, capture_output=True, text=True).stdout
    for line in output.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise RuntimeError(f"PDF 페이지 수를 확인할 수 없습니다: {path}")


def replace_prefix(value: str, old: str, new: str) -> str:
    return new + value[len(old):] if value == old or value.startswith(old + "-") else value


def move_item(source: dict, item_id: str, x: float, y: float, row: int) -> dict:
    item = copy.deepcopy(source)
    old_id = item["item_id"]
    dx, dy = x - item["x"], y - item["y"]
    item["item_id"] = item_id
    item["label"] = item_id
    item["row"] = row
    item["x"], item["y"] = x, y
    for pin in item["pins"]:
        pin["terminal_id"] = replace_prefix(pin["terminal_id"], old_id, item_id)
        pin["x"] += dx
        pin["y"] += dy
    if item.get("label_area"):
        item["label_area"]["x"] += dx
        item["label_area"]["y"] += dy
    return item


def board_for(number: str) -> dict:
    base = read_json(BOARD_TEMPLATE)
    templates = {item["item_id"]: item for item in base["items"]}
    board = {key: copy.deepcopy(value) for key, value in base.items() if key != "items"}
    board["board_id"] = f"qnet_public_{number}_board_v1"
    board["layout_mode"] = "fixed"
    top, bottom = LAYOUTS[number]
    top_x = [90, 315, 540, 765, 990] if len(top) == 5 else [130, 405, 680, 955]
    bottom_x = [90, 390, 690, 990]

    def template_id(device_id: str) -> str:
        if device_id == "MCCB": return "MCCB"
        if device_id == "EOCR": return "EOCR"
        if device_id == "F": return "F"
        if device_id.startswith("MC"): return "MC1"
        return "X1"

    items = [copy.deepcopy(templates["TB5"])]
    items.extend(move_item(templates[template_id(device)], device, x, 210, 1) for device, x in zip(top, top_x))
    items.extend(move_item(templates[template_id(device)], device, x, 500, 2) for device, x in zip(bottom, bottom_x))
    items.append(copy.deepcopy(templates["TB6"]))
    board["items"] = items
    board["forbidden_areas"] = [
        {
            "area_id": f"{item['item_id']}_body",
            "x": item["x"], "y": item["y"],
            "width": item["width"], "height": item["height"],
        }
        for item in items
    ]
    return board


def external_device(device_id: str, label: str, suffixes: list[str], placement: str = "top") -> dict:
    colors = {"L1": "brown", "L2": "black", "L3": "gray"}
    return {
        "device_id": device_id, "label": label, "placement": placement,
        "terminals": [
            {
                "terminal_id": f"{device_id}-{suffix}", "label": suffix,
                "terminal_role": "external", "operation_terminal_id": None,
                "max_connections": 1, "wire_color": colors.get(suffix, "yellow"),
            }
            for suffix in suffixes
        ],
    }


def external_devices(number: str) -> list[dict]:
    devices = [
        external_device("PWR", "외부 전원", ["L1", "L2", "L3", "PE"]),
        external_device("PB0", "PB0 정지(NC)", ["1", "2"]),
        external_device("PB1", "PB1 기동(NO)", ["1", "2"]),
    ]
    if int(number) <= 9:
        devices += [
            external_device("SS", "셀렉터 스위치 M/A", ["C", "M", "A"]),
            external_device("FLS", "플로트레스 스위치", ["E1", "E2", "E3", "PE"]),
            external_device("BZ", "부저", ["1", "2"], "bottom"),
        ]
    else:
        devices += [
            external_device("PB2", "PB2 기동(NO)", ["1", "2"]),
            external_device("LS1", "리밋 스위치 LS1", ["1", "2"]),
            external_device("LS2", "리밋 스위치 LS2", ["1", "2"]),
            external_device("WL", "백색 표시등", ["1", "2"], "bottom"),
        ]
    devices += [
        external_device("YL", "황색 표시등", ["1", "2"], "bottom"),
        external_device("RL", "적색 표시등", ["1", "2"], "bottom"),
        external_device("GL", "녹색 표시등", ["1", "2"], "bottom"),
        external_device("M1", "전동기 M1", ["U", "V", "W", "PE"], "bottom"),
        external_device("M2", "전동기 M2", ["U", "V", "W", "PE"], "bottom"),
    ]
    return devices


def render_schematic(pdf: Path, target: Path) -> tuple[int, int]:
    with tempfile.TemporaryDirectory(prefix="qnet-page-") as temp:
        prefix = Path(temp) / "page"
        subprocess.run([
            "pdftoppm", "-f", "7", "-singlefile", "-png", "-r", "200",
            str(pdf), str(prefix),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        image = (prefix.with_suffix(".png")).read_bytes()
    width, height = 2337, 1654
    encoded = base64.b64encode(image).decode("ascii")
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}"><image width="{width}" height="{height}" '
        f'href="data:image/png;base64,{encoded}"/></svg>\n'
    )
    target.write_text(svg, encoding="utf-8")
    return width, height


def create_package(number: str, pdf: Path) -> dict:
    problem_id = f"qnet_electrician_practical_{number}"
    target = PROBLEMS / problem_id
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    source_hash = sha256(pdf)
    width, height = render_schematic(pdf, target / "schematic.svg")
    source_name = pdf.name

    manifest = {
        "schema_version": "1.0", "problem_id": problem_id,
        "title": f"Q-Net 공개문제 {number} · {TITLES[number]}", "version": 1,
        "problem_type": "official", "status": "draft", "difficulty": "advanced",
        "estimated_minutes": 270, "tags": ["Q-Net", f"공개문제-{number}", "PDF대조중"],
        "source": {
            "type": "official", "name": "Q-Net 전기기능사 실기 공개문제",
            "reference": f"{source_name} | sha256:{source_hash} | 근거 6~9쪽",
            "verified_date": None,
        },
        "files": {"problem": "problem.json", "answer": "answer.json", "schematic": "schematic.svg", "diagram": "diagram.json", "board": "board.json"},
    }
    problem = {
        "schema_version": "1.0", "problem_id": problem_id,
        "description": f"공식 공개문제 {number}의 원본 회로도와 배치를 대조하는 단계입니다. 비공개 정답 네트워크와 동작시험은 아직 교차검증 전이므로 채점되지 않습니다.",
        "instructions": ["7쪽 공식 시퀀스 회로도를 확대해 확인하세요.", "6쪽 배치 근거를 반영한 보드를 확인하세요.", "검증 완료 전에는 학습 채점이나 동작시험에 사용하지 마세요."],
        "learning_objectives": [TITLES[number], "공식 회로의 기구와 접점 구조 확인"],
        "power_supply": {"system": "3P3W_AC_220V", "voltage": 220, "frequency": 60, "wire_colors": {"L1": "brown", "L2": "black", "L3": "gray", "control": "yellow"}},
        "schematic": {"file": "schematic.svg", "format": "svg", "view_box": f"0 0 {width} {height}"},
        "board": {"layout_id": f"qnet_public_{number}_board_v1"},
        "available_devices": [{"device_id": item, "source_page": 6} for row in LAYOUTS[number] for item in row],
        "circuit": {"schema_version": "1.0", "definition_status": "structure_only", "devices": [], "terminals": [], "contacts": [], "coils": []},
        "socket_questions": [], "device_layout": None, "mounting": None, "operation": None,
        "wiring_semantics": {"schema_version": "1.0", "extra_jumper_policy": "warning", "external_devices": external_devices(number)},
    }
    answer = {
        "schema_version": "1.0", "problem_id": problem_id, "answer_version": 1,
        "verification": {"status": "unverified", "verified_by": None, "verified_at": None, "notes": "PDF 회로의 접점별 소켓 핀 선택과 expected_nets 교차검증 전"},
        "socket_pin_answers": {}, "required_connections": [], "expected_nets": [],
        "allowed_alternatives": [], "forbidden_connections": [], "wiring_connections": [],
        "wiring_forbidden_connections": [], "mounting_answer": [],
        "wire_color_rules": {"L1": "brown", "L2": "black", "L3": "gray", "control": "yellow"},
        "operation_tests": [],
    }
    diagram = {
        "schema_version": "1.0", "view_box": {"x": 0, "y": 0, "width": width, "height": height},
        "sections": [{"section_id": "official_pdf", "label": "공식 회로도", "bounds": {"x": 1, "y": 1, "width": width - 2, "height": height - 2}}],
        "elements": [], "conductors": [],
    }
    write_json(target / "manifest.json", manifest)
    write_json(target / "problem.json", problem)
    write_json(target / "answer.json", answer)
    write_json(target / "diagram.json", diagram)
    write_json(target / "board.json", board_for(number))
    return {"number": number, "problem_id": problem_id, "source_file": source_name, "size_bytes": pdf.stat().st_size, "page_count": page_count(pdf), "sha256": source_hash, "status": "draft", "evidence_pages": [6, 7, 8, 9]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_directory", type=Path)
    parser.add_argument(
        "--boards-only", action="store_true",
        help="기존 문제 정의를 보존하고 PDF 6쪽 검수 배치만 동기화한다.",
    )
    parser.add_argument(
        "--problem", action="append", choices=sorted(LAYOUTS),
        help="처리할 공개문제 번호. 생략하면 001~018 전체를 처리한다.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="기존 문제 패키지를 삭제하고 전체 재생성하는 작업을 명시적으로 허용한다.",
    )
    args = parser.parse_args()
    numbers = args.problem or sorted(LAYOUTS)
    if args.boards_only:
        for number in numbers:
            target = PROBLEMS / f"qnet_electrician_practical_{number}" / "board.json"
            if not target.exists():
                raise SystemExit(f"{number}: 기존 board.json을 찾을 수 없습니다.")
            write_json(target, board_for(number))
            print(f"[배치 동기화] {number} PDF 6쪽")
        return 0
    if not args.force:
        raise SystemExit("전체 문제 패키지 재생성은 기존 기능 정의를 덮어씁니다. 실행하려면 --force를 지정하세요.")
    records = []
    for number in numbers:
        matches = sorted(args.pdf_directory.glob(f"전기기능사-{number}-A4, 2025-08-04.pdf"))
        if len(matches) != 1:
            raise SystemExit(f"{number}: 원본 PDF를 정확히 1개 찾을 수 있어야 합니다.")
        records.append(create_package(number, matches[0]))
        print(f"[생성] {number} {TITLES[number]}")
    if numbers == sorted(LAYOUTS):
        write_json(ROOT / "catalog" / "qnet_public_sources.json", {"schema_version": "1.0", "edition": "2025-08-04", "records": records})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
