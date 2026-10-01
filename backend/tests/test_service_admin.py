import json
import sys

from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

from app.core.auth import AuthStore, COOKIE_NAME
from app.core.config import Settings
from app.core.service_admin import NetworkOptions, apply_saved_network
from app.main import create_app
from test_lan_accounts import test_paths, PASSWORD, register


@pytest.fixture
def admin_client(tmp_path):
    settings = Settings(paths=test_paths(tmp_path), auth_required=True, service_managed=True)
    with TestClient(create_app(settings)) as client:
        session, _ = register(client, "operator01")
        client.app.state.auth_store.set_admin("operator01", True)
        response = client.post("/api/auth/login", headers={"X-Requested-With": "ElectricianSimulator"},
                               json={"username": "operator01", "password": PASSWORD})
        assert response.json()["is_admin"] is True
        headers = {"X-Requested-With": "ElectricianSimulator", "X-CSRF-Token": response.json()["csrf_token"],
                   "X-Session-User": session["user"]["user_id"]}
        yield client, headers


def test_student_and_anonymous_cannot_access_any_admin_capability(tmp_path):
    with TestClient(create_app(Settings(paths=test_paths(tmp_path), auth_required=True))) as client:
        paths = ("/api/admin/status", "/api/admin/accounts")
        for path in paths:
            assert client.get(path).status_code == 401
        session, headers = register(client)
        assert session["is_admin"] is False
        for path in paths:
            assert client.get(path, headers={"X-User-Id": "admin", "X-Admin": "true"}).status_code == 403
        for path, payload in (("registration", {"enabled": False}), ("network", {"host": "0.0.0.0", "port": 8017})):
            assert client.put("/api/admin/" + path, headers=headers, json=payload).status_code == 403
        assert client.post("/api/admin/accounts/any/logout", headers=headers).status_code == 403
        assert client.post("/api/auth/register", headers=headers, json={
            "username": "hacker01", "password": PASSWORD, "nickname": "학생", "is_admin": True,
        }).status_code == 422


def test_admin_endpoints_are_disabled_in_legacy_nickname_mode(tmp_path):
    with TestClient(create_app(Settings(paths=test_paths(tmp_path)))) as client:
        assert client.get("/api/admin/status").status_code == 404
        assert client.put("/api/admin/registration", json={"enabled": True}).status_code == 404


def test_registration_switch_is_immediate_persistent_and_csrf_protected(admin_client):
    client, headers = admin_client
    url = "/api/admin/registration"
    assert client.put(url, json={"enabled": False}).status_code == 403
    assert client.put(url, headers={**headers, "Origin": "http://evil.example"}, json={"enabled": False}).status_code == 403
    assert client.put(url, headers=headers, json={"enabled": False}).status_code == 200
    assert client.get("/api/auth/me").json()["registration_open"] is False
    assert client.post("/api/auth/register", headers=headers, json={
        "username": "student02", "password": PASSWORD, "nickname": "학생",
    }).status_code == 403
    settings = client.app.state.settings
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get("/api/auth/me").json()["registration_open"] is False
    assert client.put(url, headers=headers, json={"enabled": True}).json()["registration_open"] is True
    assert client.put(url, headers=headers, json={"enabled": "false"}).status_code == 422


def test_network_is_saved_only_and_applied_by_launcher_after_restart(admin_client):
    client, headers = admin_client
    desired = {"host": "192.168.0.14", "port": 8017}
    assert client.put("/api/admin/network", headers=headers, json=desired).status_code == 200
    current = client.get("/api/admin/status").json()
    assert current["current_network"] == {"host": "127.0.0.1", "port": 8000}
    assert current["saved_network"] == desired and current["restart_required"]
    applied = apply_saved_network(client.app.state.settings)
    assert (applied.host, applied.port, applied.allow_lan, applied.auth_required) == ("192.168.0.14", 8017, True, True)
    with TestClient(create_app(applied)) as restarted:
        restarted.cookies.set(COOKIE_NAME, client.cookies[COOKIE_NAME])
        assert restarted.get("/api/admin/status").json()["restart_required"] is False
    client.put("/api/admin/network", headers=headers, json={"host": "127.0.0.1", "port": 8001})
    assert not apply_saved_network(applied).allow_lan
    assert apply_saved_network(applied).auth_required  # Local-only still requires account login.


def test_direct_uvicorn_does_not_promise_to_apply_saved_bind_settings(admin_client):
    client, headers = admin_client
    client.app.state.settings.service_managed = False
    assert client.put("/api/admin/network", headers=headers, json={"host": "0.0.0.0", "port": 9000}).status_code == 409
    assert client.get("/api/admin/status").json()["service_managed"] is False


@pytest.mark.parametrize("host", ["8.8.8.8", "example.org", "::", "169.254.1.2", "192.168.1.1\nAPP_DEBUG=true"])
def test_network_settings_only_accept_local_or_rfc1918_ipv4(host):
    with pytest.raises(ValidationError):
        NetworkOptions(host=host, port=8017)


@pytest.mark.parametrize("port", [0, 80, 65536, "8000", True])
def test_network_port_is_strict_unprivileged_integer(port):
    with pytest.raises(ValidationError):
        NetworkOptions(host="0.0.0.0", port=port)


def test_accounts_and_status_do_not_expose_credentials_or_study_content(admin_client):
    client, headers = admin_client
    response = client.get("/api/admin/status")
    status = response.json()
    assert status["account_count"] == status["active_sessions"] == 1
    assert status["disk_free_bytes"] > 0 and status["uptime_seconds"] >= 0
    assert response.headers["cache-control"] == "no-store"
    accounts = client.get("/api/admin/accounts").json()
    assert accounts[0]["username"] == "operator01" and accounts[0]["is_admin"]
    assert client.post(f"/api/admin/accounts/{accounts[0]['user_id']}/logout", headers=headers).status_code == 400
    assert client.post("/api/admin/accounts/no-such-user/logout", headers=headers).status_code == 404
    serialized = json.dumps([status, accounts])
    for secret in (PASSWORD, client.cookies[COOKIE_NAME], headers["X-CSRF-Token"], "password_hash", "expected_nets"):
        assert secret not in serialized


def test_remote_logout_preserves_account_and_study_database(admin_client):
    client, headers = admin_client
    store = client.app.state.auth_store
    student = store.register("student02", "학생", PASSWORD)
    token, _ = store.create_session(student["user_id"])
    users = store.path.parent / "users"
    users.mkdir()
    study = users / (student["user_id"] + ".db")
    study.write_bytes(b"unchanged test study data")
    assert client.post(f"/api/admin/accounts/{student['user_id']}/logout", headers=headers).status_code == 200
    assert store.authenticate(token) is None
    assert store.login("student02", PASSWORD) == student
    assert study.read_bytes() == b"unchanged test study data"
    assert client.get("/api/admin/status").json()["audit"][0]["action"] == "logout-account"


def test_local_role_assignment_revokes_sessions_and_preserves_existing_accounts(tmp_path, monkeypatch):
    from scripts.manage_admin import main
    store = AuthStore(tmp_path / "accounts.db")
    store.initialize()
    student = store.register("student01", "학생", PASSWORD)
    token, _ = store.create_session(student["user_id"])
    monkeypatch.setattr(sys, "argv", ["manage_admin.py", str(tmp_path), "STUDENT01", "--server-stopped"])
    main()
    assert store.is_admin(student["user_id"])
    assert store.authenticate(token) is None
    assert store.login("student01", PASSWORD) == student
    token, _ = store.create_session(student["user_id"])
    monkeypatch.setattr(sys, "argv", ["manage_admin.py", str(tmp_path), "student01", "--revoke", "--server-stopped"])
    main()
    assert not store.is_admin(student["user_id"])
    assert store.authenticate(token) is None


def test_old_database_migrates_and_admin_settings_follow_backup(tmp_path):
    from scripts.service_data import backup, restore
    source = tmp_path / "source"
    store = AuthStore(source / "accounts.db")
    store.initialize()
    account = store.register("operator01", "운영자", PASSWORD)
    with store.connection() as db:
        for table in ("account_admins", "service_options", "admin_audit"):
            db.execute(f"DROP TABLE {table}")
    settings = Settings(paths=test_paths(source), auth_required=True)
    assert apply_saved_network(settings).host == settings.host
    store.initialize()
    assert store.login("operator01", PASSWORD) == account
    store.set_admin("operator01", True)
    store.save_service_option("network", {"host": "127.0.0.1", "port": 8017}, "operator01")
    store.save_service_option("registration_open", False, "operator01")
    archive = tmp_path / "backup.zip"
    backup(source, archive)
    restored = tmp_path / "restored"
    restore(archive, restored)
    restored_store = AuthStore(restored / "accounts.db")
    assert restored_store.is_admin(account["user_id"])
    assert restored_store.service_option("registration_open") is False
    assert apply_saved_network(Settings(paths=test_paths(restored), auth_required=True)).port == 8017


def test_local_network_recovery_does_not_reset_registration_or_accounts(tmp_path, monkeypatch):
    from scripts.manage_admin import main
    store = AuthStore(tmp_path / "accounts.db")
    store.initialize()
    account = store.register("operator01", "운영자", PASSWORD)
    store.set_admin("operator01", True)
    store.save_service_option("network", {"host": "192.168.99.99", "port": 9000}, "operator01")
    store.save_service_option("registration_open", False, "operator01")
    monkeypatch.setattr(sys, "argv", ["manage_admin.py", str(tmp_path), "--clear-network", "--server-stopped"])
    main()
    assert store.service_option("network") is None
    assert store.service_option("registration_open") is False
    assert store.login("operator01", PASSWORD) == account
    assert store.is_admin(account["user_id"])
