from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROBLEMS = ROOT / "problems"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def wire(index: int, source: str, target: str, color: str = "yellow") -> dict:
    return {"connection_id": f"W-{index:03d}", "from": source, "to": target, "wire_color": color}


def update_capacity(folder: Path) -> None:
    board_path = folder / "board.json"
    if board_path.is_file():
        board = read_json(board_path)
        for item in board.get("items", []):
            for pin in item.get("pins", []):
                pin["max_connections"] = 2
        write_json(board_path, board)

    problem_path = folder / "problem.json"
    if problem_path.is_file():
        problem = read_json(problem_path)
        for terminal in problem.get("circuit", {}).get("terminals", []):
            terminal["max_connections"] = 2
        write_json(problem_path, problem)


def update_base_answer(problem_id: str) -> None:
    path = PROBLEMS / problem_id / "answer.json"
    answer = read_json(path)
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
    write_json(path, answer)


def update_forward_reverse_answer() -> None:
    path = PROBLEMS / "forward_reverse_interlock_demo_001" / "answer.json"
    answer = read_json(path)
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
    write_json(path, answer)


def main() -> None:
    for folder in PROBLEMS.iterdir():
        if folder.is_dir():
            update_capacity(folder)
    update_base_answer("operation_demo_001")
    update_base_answer("eocr_sequence_demo_001")
    update_forward_reverse_answer()
    print("모든 단자를 최대 두 가닥으로 통일하고 분기 결선을 점퍼 방식으로 갱신했습니다.")


if __name__ == "__main__":
    main()
