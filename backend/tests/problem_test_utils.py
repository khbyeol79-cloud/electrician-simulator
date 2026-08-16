from __future__ import annotations

import json
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def copy_schemas(target_root: Path) -> Path:
    destination = target_root / "schemas"
    shutil.copytree(PROJECT_ROOT / "schemas", destination)
    return destination


def copy_problem(target_root: Path, problem_id: str = "practice_001") -> Path:
    destination = target_root / problem_id
    shutil.copytree(PROJECT_ROOT / "problems" / "practice_001", destination)
    if problem_id != "practice_001":
        for name in ("manifest.json", "problem.json", "answer.json"):
            path = destination / name
            data = json.loads(path.read_text(encoding="utf-8"))
            data["problem_id"] = problem_id
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination


def update_json(path: Path, updater) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    updater(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

