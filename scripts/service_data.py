"""Offline portable account/study backup. Restore NEVER overwrites a directory.

Run with the same project version on Windows/Linux. Stop the service first so
the accounts and per-user databases form one coherent point-in-time set.
Archives contain password hashes and private work: protect/encrypt them.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import getpass
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import zipfile

DB_NAME = re.compile(r"(?:accounts|app)\.db|users/[A-Za-z0-9_-]{1,64}\.db")
MAX_TOTAL = 10 * 1024**3


def checked_databases(root):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Data directory required")
    files = [p for p in (root / "accounts.db", root / "app.db") if p.is_file()]
    users = root / "users"
    if users.is_symlink():
        raise ValueError("Symlink data directories are not supported")
    if users.exists():
        files.extend(sorted(users.glob("*.db")))
    if not files:
        raise ValueError("No databases found; check ELECTRICIAN_DATA_DIR")
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Database must be inside the data directory")
        if not DB_NAME.fullmatch(path.relative_to(root).as_posix()):
            raise ValueError("Unsupported database name")
    return root, files


def integrity(path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Database integrity check failed")


def backup(root, destination):
    root, files = checked_databases(root)
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError("Backup destination already exists; choose a new filename")
    manifest = {"format": "electrician-service-data", "version": 1,
                "created_at": datetime.now(timezone.utc).isoformat(), "files": {}}
    # Exclusive creation also protects against another process winning a race.
    with tempfile.TemporaryDirectory(prefix="electrician-backup-") as temporary:
        with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            for index, source in enumerate(files):
                target = Path(temporary) / f"{index}.db"
                with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as src:
                    with closing(sqlite3.connect(target)) as dst:
                        src.backup(dst)  # Captures committed WAL content safely.
                integrity(target)
                name = source.relative_to(root).as_posix()
                data = target.read_bytes()
                manifest["files"][name] = hashlib.sha256(data).hexdigest()
                archive.writestr(name, data)
            archive.writestr("manifest.json", json.dumps(manifest, indent=2))
    return manifest


def restore(source, destination):
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve()
    if destination.exists():
        raise ValueError("Restore only to a NEW directory. Existing data is never overwritten.")
    if not destination.parent.is_dir():
        raise ValueError("Destination parent must already exist")
    with zipfile.ZipFile(source) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)) or names.count("manifest.json") != 1:
            raise ValueError("Duplicate entries or missing manifest")
        if any(name != "manifest.json" and not DB_NAME.fullmatch(name) for name in names):
            raise ValueError("Unexpected archive path")
        if sum(info.file_size for info in infos) > MAX_TOTAL:
            raise ValueError("Archive exceeds the 10 GiB review limit")
        if archive.getinfo("manifest.json").file_size > 1024 * 1024:
            raise ValueError("Manifest too large")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("format") != "electrician-service-data" or manifest.get("version") != 1:
            raise ValueError("Unsupported backup format")
        if set(manifest.get("files", {})) != set(names) - {"manifest.json"} or not manifest["files"]:
            raise ValueError("Manifest file list mismatch")
        with tempfile.TemporaryDirectory(prefix=".electrician-restore-", dir=destination.parent) as temporary:
            staged = Path(temporary) / "data"
            staged.mkdir()
            for name, checksum in manifest["files"].items():
                data = archive.read(name)
                if hashlib.sha256(data).hexdigest() != checksum:
                    raise ValueError("Backup checksum mismatch")
                target = staged / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                integrity(target)
            # Credentials/IDs stay unchanged. Old browser tokens cannot follow
            # the service to a new host, and migration clears old lockouts.
            if (staged / "accounts.db").exists():
                with closing(sqlite3.connect(staged / "accounts.db")) as db:
                    db.execute("DELETE FROM auth_sessions")
                    db.execute("DELETE FROM auth_limits")
                    db.commit()
            if destination.exists():
                raise ValueError("Restore destination appeared during restore")
            staged.rename(destination)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for verb in ("backup", "restore"):
        item = sub.add_parser(verb)
        item.add_argument("source", type=Path)
        item.add_argument("destination", type=Path)
        item.add_argument("--server-stopped", action="store_true", required=True)
    reset = sub.add_parser("reset-password")
    reset.add_argument("data_dir", type=Path)
    reset.add_argument("username")
    reset.add_argument("--server-stopped", action="store_true", required=True)
    args = parser.parse_args()
    if args.command == "backup":
        result = backup(args.source, args.destination)
    elif args.command == "restore":
        result = restore(args.source, args.destination)
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
        from app.core.auth import AuthStore, MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH
        path = args.data_dir.resolve(strict=True) / "accounts.db"
        if not path.is_file():
            raise ValueError("Account database not found")
        password = getpass.getpass(f"New password ({MIN_PASSWORD_LENGTH}-{MAX_PASSWORD_LENGTH} characters): ")
        if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH or password != getpass.getpass("Repeat password: "):
            raise ValueError("Password length or confirmation mismatch")
        AuthStore(path).reset_password(args.username.strip().lower(), password)
        print("Password replaced; previous login sessions revoked.")
        return
    print(f"{args.command}: {len(result['files'])} databases verified. Original data preserved.")


if __name__ == "__main__":
    main()
