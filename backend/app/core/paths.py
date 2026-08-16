from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


APP_DIRECTORY_NAME = "ElectricianSimulator"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return _project_root()


def _writable_root(project_root: Path) -> Path:
    override = os.getenv("ELECTRICIAN_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()

    if os.getenv("APP_ENV", "development").lower() == "development":
        return project_root / "data" / "dev"

    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_DIRECTORY_NAME
    return Path.home() / f".{APP_DIRECTORY_NAME.lower()}"


@dataclass(frozen=True)
class AppPaths:
    project_root: Path
    bundle_root: Path
    frontend_dist: Path
    problems_dir: Path
    catalog_dir: Path
    writable_root: Path
    database_file: Path
    logs_dir: Path
    log_file: Path

    def ensure_writable_directories(self) -> None:
        self.writable_root.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


def build_paths() -> AppPaths:
    project_root = _project_root()
    bundle_root = _bundle_root()
    writable_root = _writable_root(project_root)
    return AppPaths(
        project_root=project_root,
        bundle_root=bundle_root,
        frontend_dist=bundle_root / "frontend" / "dist",
        problems_dir=bundle_root / "problems",
        catalog_dir=bundle_root / "catalog",
        writable_root=writable_root,
        database_file=writable_root / "app.db",
        logs_dir=writable_root / "logs",
        log_file=writable_root / "logs" / "app.log",
    )
