"""Build source frontend, then create an allowlisted Windows LAN runtime ZIP."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
RUNTIME_FILES = (
    "backend/requirements-web.txt", "deploy/lan.env.example", "LAN_TRANSFER.md",
    "서버_최초설치.bat", "서버_시작.bat", "서버_종료_백업.bat", "백업_복원.bat",
    "scripts/setup_windows.ps1", "scripts/service_launcher.py", "scripts/run_service.py",
    "scripts/service_lifecycle.py", "scripts/service_data.py", "scripts/manage_admin.py",
    "scripts/restore_service_backup.py",
)
PACKAGE_FILES = ("manifest.json", "problem.json", "diagram.json", "board.json", "answer.json", "schematic.svg")
PROBLEM_IDS = tuple(f"qnet_electrician_practical_{i:03d}" for i in range(1, 19)) + (
    "eocr_sequence_demo_001", "forward_reverse_interlock_demo_001", "operation_demo_001",
    "practice_001", "training_socket_demo_001",  # compatibility for existing free workspaces
)


def release_files(project: Path) -> list[Path]:
    files = [project / name for name in RUNTIME_FILES]
    for folder, pattern in (("backend/app", "*.py"), ("catalog", "*.json"),
                            ("schemas", "*.json"), ("free_templates", "template.json")):
        files.extend((project / folder).rglob(pattern))
    # Vite output only: never source maps, environment files, user data or logs.
    files.extend(p for p in (project / "frontend/dist").rglob("*")
                 if p.is_file() and p.suffix.lower() in {".html", ".js", ".css", ".svg", ".png", ".ico", ".woff", ".woff2"})
    for problem_id in PROBLEM_IDS:
        files.extend(project / "problems" / problem_id / name for name in PACKAGE_FILES)
        if problem_id.startswith("qnet_"):
            files.append(project / "problems" / problem_id / "layout-reference.png")
            reference_ids = ["operation", "internal", "mc", "eocr", "timer", "relay", "socket8", "socket12"]
            if int(problem_id[-3:]) <= 9:
                reference_ids += ["fr", "fls", "ss"]
            files.extend(project / "problems" / problem_id / "study-references" / f"{name}.png"
                         for name in reference_ids)
    files.append(project / "frontend/dist/index.html")
    for path in files:
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(project):
            raise ValueError(f"Missing or unsafe release file: {path.relative_to(project)}")
        if any(parent.is_symlink() for parent in path.parents if parent != project and parent.is_relative_to(project)):
            raise ValueError("Symlink directories cannot be packaged")
    return sorted(set(files))


def build_frontend(project: Path):
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise ValueError("개발 PC에 Node.js/npm이 필요합니다. 이전 화면으로 ZIP을 만들지 않았습니다.")
    if not (project / "frontend/node_modules").is_dir():
        subprocess.run([npm, "ci"], cwd=project / "frontend", check=True)
    subprocess.run([npm, "run", "build"], cwd=project / "frontend", check=True)


def create_release(project: Path, output: Path, *, rebuild=True) -> Path:
    project = project.resolve(strict=True)
    if rebuild:
        build_frontend(project)
    files = release_files(project)
    # Private server-side operation tests are deliberately retained. Removing
    # them would silently break requirement evaluation after migration.
    sys.path.insert(0, str(project / "backend"))
    from app.repositories.problem_repository import ProblemRepository
    repository = ProblemRepository(project / "problems", project / "schemas", project / "catalog")
    result = repository.reload()
    if result.excluded:
        raise ValueError("문제 패키지 오류: 배포를 중단했습니다.")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "-" + uuid.uuid4().hex[:8]
    final = output / f"electrician-lan-{stamp}.zip"
    partial = final.with_suffix(".partial.zip")
    metadata = {"format": "electrician-lan-runtime", "version": 1,
                "created_at": datetime.now(timezone.utc).isoformat(), "files": {}}
    try:
        metadata["source_commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=project, text=True, stderr=subprocess.DEVNULL).strip()
        metadata["source_dirty"] = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=project, text=True, stderr=subprocess.DEVNULL).strip())
    except (OSError, subprocess.CalledProcessError):
        metadata["source_commit"] = None
    with zipfile.ZipFile(partial, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            name = path.relative_to(project).as_posix()
            data = path.read_bytes()
            # cmd.exe expects CRLF, independent of the Git checkout settings.
            if path.suffix.lower() == ".bat":
                data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            metadata["files"][name] = hashlib.sha256(data).hexdigest()
            archive.writestr("electrician-lan/" + name, data)
        archive.writestr("electrician-lan/release-manifest.json", json.dumps(metadata, indent=2))
    with zipfile.ZipFile(partial) as archive:
        if archive.testzip() is not None:
            raise ValueError("배포 ZIP 검사 실패")
        for name, checksum in metadata["files"].items():
            if hashlib.sha256(archive.read("electrician-lan/" + name)).hexdigest() != checksum:
                raise ValueError("배포 ZIP 체크섬 오류")
    if os.name == "nt":
        partial.rename(final)
    else:
        os.link(partial, final)
        partial.unlink()
    return final


if __name__ == "__main__":
    try:
        archive = create_release(PROJECT, PROJECT / "releases")
        print(f"배포 ZIP 생성 및 검증 완료: {archive}")
        print("계정·학습 기록은 포함되지 않습니다. 서버_종료_백업.bat로 만든 백업 ZIP도 별도로 가져가세요.")
    except (Exception, KeyboardInterrupt) as exc:
        print(f"배포를 완료하지 못했습니다: {exc}", file=sys.stderr)
        sys.exit(1)
