from dataclasses import replace
import sqlite3

from fastapi.testclient import TestClient
import pytest

from app.core.auth import COOKIE_NAME, AuthStore, verify_password
from app.core.config import Settings
from app.core.paths import build_paths
from app.main import create_app

PASSWORD = "classroom-example-password"
PID = "qnet_electrician_practical_001"


def test_paths(tmp_path):
    return replace(build_paths(), writable_root=tmp_path, database_file=tmp_path / "app.db",
                   logs_dir=tmp_path / "logs", log_file=tmp_path / "logs/app.log")
test_paths.__test__ = False


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(Settings(paths=test_paths(tmp_path), allow_lan=True))) as c:
        yield c


def register(client, username="student01", nickname="동일 닉네임"):
    response = client.post("/api/auth/register", headers={"X-Requested-With": "ElectricianSimulator"},
                           json={"username": username, "password": PASSWORD, "nickname": nickname})
    assert response.status_code == 201, response.text
    session = response.json()
    return session, {"X-Requested-With": "ElectricianSimulator", "X-CSRF-Token": session["csrf_token"],
                     "X-Session-User": session["user"]["user_id"]}


def test_auth_is_required_and_caller_cannot_select_legacy_database(client):
    assert client.get("/api/auth/me").json()["required"]
    for path in ("/api/problems", "/api/free-circuits", f"/api/problems/{PID}/analysis-draft"):
        assert client.get(path, headers={"X-User-Id": "default"}).status_code == 401
    session, headers = register(client)
    assert session["user"]["user_id"].startswith("acct_")
    assert client.get("/api/problems", headers={"X-User-Id": "someone_else"}).status_code == 200
    with client.app.state.auth_store.connection() as db:
        row = db.execute("SELECT * FROM accounts").fetchone()
        assert row["password_hash"] != PASSWORD
        assert verify_password(PASSWORD, row["password_hash"])
        assert not verify_password("incorrect", row["password_hash"])
        assert db.execute("SELECT token_hash FROM auth_sessions").fetchone()[0] != client.cookies[COOKIE_NAME]
    assert "password" not in session["user"]
    assert not (client.app.state.settings.paths.writable_root / "users/someone_else.db").exists()


def test_csrf_origin_validation_no_secret_echo_and_code_free_registration(client):
    assert client.get("/api/auth/me").json()["registration_open"]
    payload = {"username": "student01", "password": PASSWORD, "nickname": "학생"}
    assert client.post("/api/auth/register", json=payload).status_code == 403
    headers = {"X-Requested-With": "ElectricianSimulator"}
    assert client.post("/api/auth/register", json=payload, headers={**headers, "Origin": "http://evil.example"}).status_code == 403
    invalid = client.post("/api/auth/register", json={**payload, "username": "!"}, headers=headers)
    assert invalid.status_code == 422 and PASSWORD not in invalid.text
    _, authenticated = register(client)
    assert client.post("/api/auth/logout", headers=headers).status_code == 403
    assert client.post("/api/problems/reload", headers=authenticated).status_code == 403


def test_accounts_with_same_nickname_isolate_all_study_data_and_sessions(client):
    a, ah = register(client)
    a_cookie = client.cookies[COOKIE_NAME]
    analysis = f"/api/problems/{PID}/analysis-draft"
    payload = {"problem_version": 1, "memo": "student A only", "selected_device_ids": [], "selected_socket_ids": [], "selected_terminal_ids": [], "annotations": {}}
    assert client.put(analysis, json=payload, headers=ah).status_code == 200
    draft = f"/api/problems/{PID}/practice-drafts/main"
    assert client.put(draft, json={"problem_version": 1, "connections": [], "workspace_name": "A 결선"}, headers=ah).status_code == 200
    operation = client.post(f"/api/problems/{PID}/practice-sessions", json={"problem_version": 1}, headers=ah)
    assert operation.status_code == 201, operation.text
    session_id = operation.json()["session_id"]
    free = client.post("/api/free-circuits/workspaces", json={"name": "A 자유회로"}, headers=ah)
    assert free.status_code in (200, 201), free.text
    free_id = free.json()["workspace_id"]
    client.cookies.clear()
    b, bh = register(client, "student02")
    assert a["user"]["nickname"] == b["user"]["nickname"] and a["user"]["user_id"] != b["user"]["user_id"]
    assert client.get(analysis, headers={"X-User-Id": a["user"]["user_id"]}).json() is None
    assert client.get(draft, headers=bh).json() is None
    setup = client.get(f"/api/problems/{PID}/operation-setup", headers=bh).json()
    assert not setup["operation_ready"] and setup["wiring_draft"] is None
    assert "저장된 결선이 없습니다" in setup["message"]
    assert "기구 배치 정보" not in setup["message"]
    assert client.get(f"/api/operation-sessions/{session_id}", headers=bh).status_code == 404
    assert client.get(f"/api/free-circuits/{free_id}", headers=bh).status_code == 404
    assert client.put(analysis, json=payload, headers=ah).status_code in (401, 403)
    assert client.get(analysis, headers=ah).status_code == 401
    client.cookies.clear(); client.cookies.set(COOKIE_NAME, a_cookie)
    assert client.get(analysis, headers=ah).json()["memo"] == "student A only"
    assert client.get(draft, headers=ah).json()["workspace_name"] == "A 결선"
    assert client.get(f"/api/operation-sessions/{session_id}", headers=ah).status_code == 200


def test_login_logout_rotation_and_password_reset(client):
    account, headers = register(client)
    old = client.cookies[COOKIE_NAME]
    response = client.post("/api/auth/login", headers={"X-Requested-With": "ElectricianSimulator"}, json={"username": "STUDENT01", "password": PASSWORD})
    assert response.status_code == 200
    assert client.cookies[COOKIE_NAME] != old
    assert "httponly" in response.headers["set-cookie"].lower() and "samesite=strict" in response.headers["set-cookie"].lower()
    assert "max-age" not in response.headers["set-cookie"].lower()
    assert client.app.state.auth_store.authenticate(old) is None
    headers["X-CSRF-Token"] = response.json()["csrf_token"]
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/problems").status_code == 401
    client.app.state.auth_store.reset_password("student01", "replacement-example-password")
    assert client.post("/api/auth/login", headers={"X-Requested-With": "ElectricianSimulator"}, json={"username": "student01", "password": PASSWORD}).status_code == 401


def test_six_character_password_can_register_and_login(client):
    headers = {"X-Requested-With": "ElectricianSimulator"}
    created = client.post("/api/auth/register", headers=headers,
                          json={"username": "sixchars", "password": "abc123", "nickname": "학생"})
    assert created.status_code == 201
    client.cookies.clear()
    logged = client.post("/api/auth/login", headers=headers, json={"username": "sixchars", "password": "abc123"})
    assert logged.status_code == 200
    assert logged.json()["user"] == created.json()["user"]


@pytest.mark.parametrize("password", ["abc12", "x" * 129])
def test_registration_rejects_password_outside_six_to_128_characters(client, password):
    response = client.post("/api/auth/register", headers={"X-Requested-With": "ElectricianSimulator"},
                           json={"username": "badlength", "password": password, "nickname": "학생"})
    assert response.status_code == 422
    assert "6~128" in response.json()["detail"]
    assert password not in response.text


def test_session_lifetime_covers_class_but_expires_and_survives_server_restart(tmp_path):
    now = [0.0]
    store = AuthStore(tmp_path / "accounts.db", clock=lambda: now[0])
    store.initialize()
    user = store.register("student01", "학생", PASSWORD)
    token, _ = store.create_session(user["user_id"])
    for minute in range(8 * 60 + 1):
        now[0] = minute * 60
        assert store.authenticate(token)["user_id"] == user["user_id"]
    restarted = AuthStore(store.path, clock=lambda: now[0])
    assert restarted.login("student01", PASSWORD) == user
    assert restarted.authenticate(token)
    now[0] += 1801
    assert restarted.authenticate(token) is None
    token, _ = store.create_session(user["user_id"])
    for hour in range(1, 11):
        now[0] += 3600
        # Advance last activity separately to isolate absolute expiry from idle.
        with store.connection() as db:
            db.execute("UPDATE auth_sessions SET last_seen=?", (now[0],))
        assert bool(store.authenticate(token)) == (hour < 10)


def test_brute_force_limit_and_registration_closed(client):
    register(client)
    for _ in range(15):
        response = client.post("/api/auth/login", headers={"X-Requested-With": "ElectricianSimulator"}, json={"username": "absent", "password": "wrong"})
        assert response.status_code == 401
    assert client.post("/api/auth/login", headers={"X-Requested-With": "ElectricianSimulator"}, json={"username": "absent", "password": "wrong"}).status_code == 429
    client.app.state.settings.registration_open = False
    assert not client.get("/api/auth/me").json()["registration_open"]
    assert client.post("/api/auth/register", headers={"X-Requested-With": "ElectricianSimulator"},
                       json={"username": "newstudent", "password": PASSWORD, "nickname": "학생"}).status_code == 403
    # Closing new enrollment never blocks existing accounts.
    assert client.post("/api/auth/login", headers={"X-Requested-With": "ElectricianSimulator"},
                       json={"username": "student01", "password": PASSWORD}).status_code == 200


def test_registration_open_setting_defaults_on_and_can_be_disabled(monkeypatch):
    from app.core.config import load_settings
    monkeypatch.delenv("REGISTRATION_OPEN", raising=False)
    assert load_settings().registration_open
    monkeypatch.setenv("REGISTRATION_OPEN", "false")
    assert not load_settings().registration_open
    monkeypatch.setenv("REGISTRATION_OPEN", "true")
    assert load_settings().registration_open


def test_lan_always_enables_auth_and_rejects_cross_origin_configuration():
    assert Settings(allow_lan=True, auth_required=False).auth_required
    with pytest.raises(ValueError):
        Settings(allow_lan=True, allowed_origins=["http://other"])


def test_twenty_concurrent_accounts_keep_independent_analysis_and_wiring(client):
    from concurrent.futures import ThreadPoolExecutor
    from contextlib import closing
    identities = []
    for i in range(20):
        client.cookies.clear()
        account, headers = register(client, f"class{i:02}")
        identities.append((i, client.cookies[COOKIE_NAME], headers))

    def study(identity):
        index, cookie, headers = identity
        with closing(TestClient(client.app)) as student:
            student.cookies.set(COOKIE_NAME, cookie)
            for turn in range(5):
                memo = f"owner-{index}-revision-{turn}"
                analysis = f"/api/problems/{PID}/analysis-draft"
                payload = {"problem_version": 1, "memo": memo, "selected_device_ids": [], "selected_socket_ids": [], "selected_terminal_ids": [], "annotations": {}}
                assert student.put(analysis, json=payload, headers=headers).status_code == 200
                assert student.get(analysis, headers=headers).json()["memo"] == memo
                draft = f"/api/problems/{PID}/practice-drafts/main"
                saved = student.put(draft, json={"problem_version": 1, "connections": [], "workspace_name": f"owner-{index}"}, headers=headers)
                assert saved.status_code == 200
                assert student.get(draft, headers=headers).json()["workspace_name"] == f"owner-{index}"
        return index

    with ThreadPoolExecutor(max_workers=20) as pool:
        assert set(pool.map(study, identities)) == set(range(20))


def test_idle_simulations_expire_without_deleting_saved_work_and_active_class_survives():
    from types import SimpleNamespace
    from app.simulation import OperationSessionManager, OperationSessionNotFound
    now = [0.0]
    manager = OperationSessionManager(clock=lambda: now[0], per_user_limit=2)
    for name in ("one", "two", "three"):
        manager.add(SimpleNamespace(session_id=name), "alice")
        now[0] += 1
    with pytest.raises(OperationSessionNotFound):
        manager.get("one", "alice")
    manager.add(SimpleNamespace(session_id="bob"), "bob")
    for hour in range(1, 9):
        now[0] = hour * 3600
        assert manager.get("three", "alice").session_id == "three"
    with pytest.raises(OperationSessionNotFound):
        manager.get("three", "bob")
    with pytest.raises(OperationSessionNotFound):
        manager.get("bob", "bob")
