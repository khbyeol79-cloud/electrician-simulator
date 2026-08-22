"""0.12.0→0.13.0 수정·추가 파일 패치와 해시 목록을 만든다."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT.parent / "electrician-simulator-0.12.0-to-0.13.0-patch.zip"

MODIFIED = [
    "APPLY_PATCH_KO.md", "DELETED_FILES.txt", "README.md",
    "backend/app/__init__.py", "backend/app/api/problems.py", "backend/app/core/config.py",
    "backend/app/repositories/problem_repository.py",
    "backend/tests/test_device_behavior_catalog.py", "backend/tests/test_device_instance_factory.py",
    "backend/tests/test_problem_api.py", "catalog/device_behaviors.json",
    "docs/basic-board-manual-test-0.11.2.md", "docs/empty-board-manual-test-0.12.0.md",
    "frontend/package-lock.json", "frontend/package.json", "frontend/src/api/client.ts",
    "frontend/src/components/StatusBar.tsx", "frontend/src/components/circuit/CircuitDiagram.tsx",
    "frontend/src/components/circuit/CircuitQuestionPanel.tsx", "frontend/src/pages/CircuitAnalysisPage.tsx",
    "frontend/src/pages/OperationTestPage.tsx", "frontend/src/pages/WiringPage.tsx",
    "frontend/src/tests/CircuitDiagnostics.test.tsx", "scripts/run_basic_board_demo.py",
    "tools/validate_problem.py",
]

ADDED = [
    "TEST_RESULTS_0.13.0.md", "backend/tests/test_qnet_public_sources.py",
    "catalog/qnet_public_sources.json", "docs/qnet-18-manual-test-0.13.0.md",
    "docs/qnet-18-problem-audit-0.13.0.md", "scripts/build_incremental_patch_0_13.py",
    "scripts/import_qnet_public_sources.py", "scripts/run_qnet_18_smoke_test.py",
]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def files() -> list[tuple[str, str]]:
    result = [(path, "modified") for path in MODIFIED] + [(path, "added") for path in ADDED]
    for base in (ROOT / "frontend" / "dist",):
        result.extend((path.relative_to(ROOT).as_posix(), "added") for path in sorted(base.rglob("*")) if path.is_file())
    for base in sorted((ROOT / "problems").glob("qnet_electrician_practical_*")):
        result.extend((path.relative_to(ROOT).as_posix(), "added") for path in sorted(base.rglob("*")) if path.is_file())
    unique = {}
    for path, change_type in result:
        unique[path] = change_type
    return sorted(unique.items())


def main() -> int:
    entries = files()
    missing = [path for path, _ in entries if not (ROOT / path).is_file()]
    if missing:
        raise SystemExit(f"패치 파일이 없습니다: {missing}")
    manifest = {
        "base_version": "0.12.0", "target_version": "0.13.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "added_files": [path for path, kind in entries if kind == "added"],
        "modified_files": [path for path, kind in entries if kind == "modified"],
        "deleted_files": [line for line in (ROOT / "DELETED_FILES.txt").read_text(encoding="utf-8").splitlines() if line],
        "excluded": [".venv", "frontend/node_modules", "test caches", "PDF 원본과 렌더링 임시파일", "사용자 DB·자유회로 작업공간·로그", "기존 ZIP"],
        "manifest_self_hash_excluded": True,
        "files": [{"path": path, "change_type": kind, "size": (ROOT / path).stat().st_size, "sha256": digest(ROOT / path)} for path, kind in entries],
    }
    (ROOT / "PATCH_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.write(ROOT / "PATCH_MANIFEST.json", "PATCH_MANIFEST.json")
        for path, _ in entries:
            archive.write(ROOT / path, path)
    with zipfile.ZipFile(OUTPUT) as archive:
        bad = archive.testzip()
        if bad:
            raise SystemExit(f"ZIP 무결성 오류: {bad}")
    print(f"파일 {len(entries) + 1}개")
    print(f"크기 {OUTPUT.stat().st_size} bytes")
    print(f"SHA-256 {digest(OUTPUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
