from contextlib import closing
import json
import os
from pathlib import Path
import socket
import struct
import sqlite3
import subprocess
import sys
import time
from urllib.request import Request, urlopen
import zipfile

import pytest

from app.core.auth import AuthStore
from scripts import service_lifecycle as lifecycle
from scripts.service_data import restore

PROJECT = Path(__file__).resolve().parents[2]


def study_data(tmp_path):
    root = tmp_path / "사용자 자료"
    store = AuthStore(root / "accounts.db")
    store.initialize()
    account = store.register("student01", "학생", "test123")
    store.set_admin("student01", True)
    store.save_service_option("registration_open", False, "student01")
    user_db = root / "users" / (account["user_id"] + ".db")
    user_db.parent.mkdir()
    with closing(sqlite3.connect(user_db)) as db:
        db.execute("CREATE TABLE saved(value TEXT)")
        db.execute("INSERT INTO saved VALUES ('학습 기록')")
        db.commit()
    return root, account


def test_verified_zip_is_usb_ready_unique_and_restores_accounts_and_study(tmp_path):
    root, account = study_data(tmp_path)
    destination = tmp_path / "USB용 백업"
    first = lifecycle.verified_backup(root, destination)
    second = lifecycle.verified_backup(root, destination)
    assert first != second and first.is_file() and second.is_file()
    assert not list(destination.glob("*.partial.zip"))
    with zipfile.ZipFile(first) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {"accounts.db", f"users/{account['user_id']}.db", "manifest.json"}
    restored = tmp_path / "restored"
    restore(first, restored)
    store = AuthStore(restored / "accounts.db")
    assert store.login("student01", "test123") == account
    assert store.is_admin(account["user_id"])
    assert store.service_option("registration_open") is False
    with closing(sqlite3.connect(restored / "users" / (account["user_id"] + ".db"))) as db:
        assert db.execute("SELECT value FROM saved").fetchone()[0] == "학습 기록"


def test_lease_rejects_duplicate_start_and_does_not_kill_stale_pid(tmp_path):
    root = tmp_path / "data"
    directory = lifecycle.runtime_dir(root)
    with lifecycle.ServiceLease(root):
        assert lifecycle.lease_held(root)
        with pytest.raises(RuntimeError, match="중복"):
            with lifecycle.ServiceLease(root):
                pytest.fail("lease must not be shared")
    assert not lifecycle.lease_held(root)
    lifecycle.write_state(directory, {"run_id": "old", "state": "running", "pid": os.getpid()})
    with pytest.raises(RuntimeError, match="찾지 못"):
        lifecycle.stop_and_wait(root, timeout=0.01)
    assert not (directory / "stop.json").exists()


def test_timeout_never_claims_success_or_forces_exit(tmp_path):
    root = tmp_path / "data"
    with lifecycle.ServiceLease(root):
        lifecycle.write_state(lifecycle.runtime_dir(root), {"run_id": "current", "state": "running"})
        with pytest.raises(TimeoutError, match="강제 종료하지"):
            lifecycle.stop_and_wait(root, timeout=0.01)
        assert lifecycle.lease_held(root)
        assert lifecycle.read_json(lifecycle.runtime_dir(root) / "stop.json") == {"run_id": "current"}


def test_backup_error_leaves_no_completed_archive_or_original_changes(tmp_path, monkeypatch):
    from scripts import service_data
    root, _ = study_data(tmp_path)
    original = (root / "accounts.db").read_bytes()
    def broken_backup(source, target):
        target.write_bytes(b"interrupted partial archive")
        raise OSError("disk full")
    monkeypatch.setattr(service_data, "backup", broken_backup)
    destination = tmp_path / "backups"
    with pytest.raises(OSError, match="disk full"):
        lifecycle.verified_backup(root, destination)
    assert all(path.name.endswith(".partial.zip") for path in destination.iterdir())
    assert (root / "accounts.db").read_bytes() == original


def test_corrupt_archive_is_not_published(tmp_path, monkeypatch):
    from scripts import service_data
    root, _ = study_data(tmp_path)
    original = service_data.backup
    def tamper(source, target):
        manifest = original(source, target)
        manifest["files"]["accounts.db"] = "bad hash"
        return manifest
    monkeypatch.setattr(service_data, "backup", tamper)
    with pytest.raises(ValueError, match="목록 검사"):
        lifecycle.verified_backup(root, tmp_path / "backups")
    assert all(p.name.endswith(".partial.zip") for p in (tmp_path / "backups").iterdir())


def test_post_shutdown_backup_failure_is_explicit_and_releases_lease(tmp_path, monkeypatch):
    import uvicorn
    from app.core.config import Settings
    from test_lan_accounts import test_paths
    root, _ = study_data(tmp_path)
    settings = Settings(paths=test_paths(root), auth_required=True)
    def clean_run(server):
        server.clean_shutdown = True
    def fail_backup(*_):
        raise OSError("disk full")
    monkeypatch.setattr(uvicorn.Server, "run", clean_run)
    monkeypatch.setattr(lifecycle, "verified_backup", fail_backup)
    with pytest.raises(OSError, match="disk full"):
        lifecycle.serve_and_backup(settings, tmp_path / "backups")
    result = lifecycle.read_json(lifecycle.runtime_dir(root) / "status.json")
    assert result["state"] == "failed" and result["backup"] is None
    assert "disk full" in result["error"]
    assert not lifecycle.lease_held(root)


def test_manual_launcher_cannot_be_stopped_by_local_controller(tmp_path):
    root = tmp_path / "data"
    with lifecycle.ServiceLease(root):
        lifecycle.write_state(lifecycle.runtime_dir(root), {"state": "manual"})
        with pytest.raises(RuntimeError, match="수동 실행"):
            lifecycle.stop_and_wait(root)
        assert not (lifecycle.runtime_dir(root) / "stop.json").exists()


def test_real_managed_server_stop_backup_and_restart(tmp_path):
    """Isolated real HTTP process, never binds LAN or reads user-data."""
    with closing(socket.socket()) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    root = tmp_path / "서버 사용자 자료"
    config = tmp_path / "서비스 설정.env"
    config.write_text(f"ELECTRICIAN_DATA_DIR={root}\nALLOW_LAN=false\nAPP_HOST=127.0.0.1\nAPP_PORT={port}\nAUTH_COOKIE_SECURE=false\nALLOWED_ORIGINS=\n", encoding="utf-8")
    backup_dir = tmp_path / "백업 폴더"
    command = [sys.executable, "-X", "utf8", str(PROJECT / "scripts/service_launcher.py")]
    address = f"http://127.0.0.1:{port}"
    env = {**os.environ, "PYTHONPATH": str(PROJECT / "backend")}
    for iteration in range(2):
        log_path = tmp_path / f"server-{iteration}.log"
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(command + ["start", "--env-file", str(config), "--backup-dir", str(backup_dir)],
                                       cwd=tmp_path, env=env, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 40
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        pytest.fail(log_path.read_text(encoding="utf-8"))
                    state = lifecycle.read_json(lifecycle.runtime_dir(root) / "status.json")
                    if state.get("state") == "running":
                        break
                    time.sleep(0.1)
                else:
                    pytest.fail("managed server startup timed out")
                # Browsers may close tabs or reset keep-alive sockets abruptly.
                # Shutdown must still reach the verified backup, not hang in
                # a Windows transport's server.wait_closed().
                for _ in range(8):
                    with closing(socket.create_connection(("127.0.0.1", port), timeout=5)) as reset_socket:
                        reset_socket.sendall(b"GET /api/health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: keep-alive\r\n\r\n")
                        reset_socket.recv(2048)
                        linger = struct.pack("hh" if os.name == "nt" else "ii", 1, 0)
                        reset_socket.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger)
                if iteration == 0:
                    duplicate = subprocess.run(command + ["start", "--env-file", str(config)], env=env,
                                               capture_output=True, text=True, encoding="utf-8", timeout=20)
                    assert duplicate.returncode != 0 and "중복" in duplicate.stderr
                    body = json.dumps({"username": "student01", "password": "test123", "nickname": "학생"}).encode()
                    with urlopen(Request(address + "/api/auth/register", data=body,
                                         headers={"Content-Type": "application/json", "X-Requested-With": "ElectricianSimulator"}), timeout=10) as response:
                        session = json.load(response)
                        cookie = response.headers["Set-Cookie"].split(";")[0]
                    draft = {"problem_version": 1, "workspace_name": "종료 백업 검증", "connections": [
                        {"from": "F-1", "to": "MCCB-T1", "wire_color": "yellow"}]}
                    with urlopen(Request(address + "/api/problems/qnet_electrician_practical_001/practice-drafts/stop-backup",
                                         method="PUT", data=json.dumps(draft).encode(), headers={"Content-Type": "application/json",
                                         "Cookie": cookie, "X-CSRF-Token": session["csrf_token"], "X-Requested-With": "ElectricianSimulator"}), timeout=10) as response:
                        assert response.status == 200
                result = subprocess.run(command + ["stop", "--env-file", str(config), "--confirm-saved"],
                                        cwd=tmp_path, env=env, capture_output=True, text=True, encoding="utf-8", timeout=45)
                assert result.returncode == 0, result.stderr + log_path.read_text(encoding="utf-8")
                assert "백업 완료" in result.stdout
                assert process.wait(timeout=10) == 0
                state = lifecycle.read_json(lifecycle.runtime_dir(root) / "status.json")
                assert state["state"] == "complete"
                with zipfile.ZipFile(state["backup"]) as archive:
                    assert archive.testzip() is None
                    assert f"users/{session['user']['user_id']}.db" in archive.namelist()
                assert not lifecycle.lease_held(root)
            finally:
                if process.poll() is None:
                    # Only this test-owned subprocess, never any user server.
                    process.terminate()
                    process.wait(timeout=10)
    assert len(list(backup_dir.glob("*.zip"))) == 2
    restored = tmp_path / "restored"
    restore(state["backup"], restored)
    assert AuthStore(restored / "accounts.db").login("student01", "test123")["user_id"] == session["user"]["user_id"]
