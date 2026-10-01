import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import zipfile

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from service_data import backup, restore
from app.core.auth import AuthStore


def test_backup_restore_keeps_same_password_nickname_owner_and_wal_study_data(tmp_path):
    root = tmp_path / "lan"
    root.mkdir()
    auth = AuthStore(root / "accounts.db")
    auth.initialize()
    user = auth.register("classroom01", "같은 닉네임", "classroom-example-password")
    token, _ = auth.create_session(user["user_id"])
    users = root / "users"
    users.mkdir()
    original = users / f"{user['user_id']}.db"
    db = sqlite3.connect(original)
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE study (memo TEXT)")
        db.execute("INSERT INTO study VALUES ('my wiring and analysis')")
        db.commit()
        archive = tmp_path / "backup.zip"
        backup(root, archive)
    finally:
        db.close()
    target = tmp_path / "raspberry-pi"
    restore(archive, target)
    restored = AuthStore(target / "accounts.db")
    assert restored.login("classroom01", "classroom-example-password") == user
    assert restored.authenticate(token) is None
    assert auth.authenticate(token) is not None  # Original LAN DB was not edited.
    with sqlite3.connect(target / "users" / original.name) as conn:
        assert conn.execute("SELECT memo FROM study").fetchone()[0] == "my wiring and analysis"
    with pytest.raises(ValueError):
        restore(archive, root)
    with pytest.raises(ValueError):
        backup(root, archive)


@pytest.mark.parametrize("kind", ["path", "hash", "duplicate", "database"])
def test_invalid_backup_never_publishes_or_overwrites_data(tmp_path, kind):
    name = "../accounts.db" if kind == "path" else "accounts.db"
    payload = b"not a sqlite database"
    manifest = {"format": "electrician-service-data", "version": 1,
                "files": {name: "incorrect" if kind == "hash" else hashlib.sha256(payload).hexdigest()}}
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("manifest.json", json.dumps(manifest))
        z.writestr(name, payload)
        if kind == "duplicate":
            with pytest.warns(UserWarning):
                z.writestr(name, payload)
    target = tmp_path / "restored"
    with pytest.raises((ValueError, sqlite3.DatabaseError)):
        restore(archive, target)
    assert not target.exists()
    assert not (tmp_path.parent / "accounts.db").exists()


def test_restored_real_application_uses_same_account_and_workspace(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.core.config import Settings
    from test_lan_accounts import test_paths, register, PASSWORD, PID
    source, target = tmp_path / "lan", tmp_path / "pi"
    with TestClient(create_app(Settings(paths=test_paths(source), auth_required=True))) as c:
        session, headers = register(c)
        old_cookie = c.cookies.get("electrician_session")
        draft_url = f"/api/problems/{PID}/practice-drafts/migration"
        result = c.put(draft_url, headers=headers, json={"problem_version": 1, "workspace_name": "이전 후에도 그대로", "connections": [{"from": "F-1", "to": "MCCB-T1", "wire_color": "yellow"}]})
        assert result.status_code == 200
    backup(source, tmp_path / "portable.zip")
    restore(tmp_path / "portable.zip", target)
    with TestClient(create_app(Settings(paths=test_paths(target), auth_required=True))) as c:
        c.cookies.set("electrician_session", old_cookie)
        assert c.get(draft_url).status_code == 401
        c.cookies.clear()
        logged = c.post("/api/auth/login", headers={"X-Requested-With": "ElectricianSimulator"}, json={"username": "student01", "password": PASSWORD})
        assert logged.status_code == 200
        assert logged.json()["user"] == session["user"]
        restored = c.get(draft_url).json()
        assert restored["workspace_name"] == "이전 후에도 그대로"
        assert restored["connections"][0]["from"] == "F-1"


@pytest.mark.parametrize("password,accepted", [("abc123", True), ("abc12", False), ("x" * 129, False)])
def test_password_reset_cli_uses_same_length_policy_as_registration(tmp_path, monkeypatch, password, accepted):
    from service_data import main
    import getpass
    store = AuthStore(tmp_path / "accounts.db")
    store.initialize()
    account = store.register("student01", "학생", "old-test-password")
    token, _ = store.create_session(account["user_id"])
    monkeypatch.setattr(sys, "argv", ["service_data.py", "reset-password", str(tmp_path), "student01", "--server-stopped"])
    monkeypatch.setattr(getpass, "getpass", lambda _: password)
    if accepted:
        main()
        assert store.login("student01", password) == account
        assert store.authenticate(token) is None
    else:
        with pytest.raises(ValueError, match="length"):
            main()
        assert store.login("student01", "old-test-password") == account
        assert store.authenticate(token) is not None
