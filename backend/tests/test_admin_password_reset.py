import json

import pytest
from fastapi import HTTPException

from app.core.auth import COOKIE_NAME
from test_lan_accounts import PASSWORD
from test_service_admin import admin_client  # noqa: F401


def payload(**changes):
    return {"admin_password": PASSWORD, "new_password": "new123", "confirmation": "new123", **changes}


def test_reset_requires_reauthentication_and_preserves_study(admin_client):
    client, headers = admin_client
    store = client.app.state.auth_store
    student = store.register("student02", "학생", PASSWORD)
    token, _ = store.create_session(student["user_id"])
    users = store.path.parent / "users"
    users.mkdir()
    study = users / (student["user_id"] + ".db")
    study.write_bytes(b"original study")
    url = f"/api/admin/accounts/{student['user_id']}/reset-password"
    assert client.post(url, headers=headers, json=payload(admin_password="incorrect")).status_code == 403
    assert store.authenticate(token)
    assert client.post(url, json=payload()).status_code == 403
    assert client.post(url, headers={**headers, "Origin": "http://evil.example"}, json=payload()).status_code == 403
    response = client.post(url, headers=headers, json=payload())
    assert response.json() == {"reset": True, "reauthenticate": False}
    assert response.headers["cache-control"] == "no-store"
    assert store.authenticate(token) is None
    assert store.login("student02", "new123") == student
    with pytest.raises(HTTPException) as old_login:
        store.login("student02", PASSWORD)
    assert old_login.value.status_code == 401
    assert study.read_bytes() == b"original study"
    assert client.get("/api/admin/status").status_code == 200
    audit = client.get("/api/admin/status").json()["audit"][0]
    assert audit["action"] == "reset-password" and audit["target"] == "student02"
    assert "new123" not in json.dumps(audit) and PASSWORD not in json.dumps(audit)


@pytest.mark.parametrize("changes", [
    {"new_password": "short", "confirmation": "short"},
    {"confirmation": "different"}, {"new_password": "z" * 129},
    {"admin_password": ""}, {"extra_secret": "DO-NOT-ECHO"},
])
def test_invalid_reset_never_echoes_passwords(admin_client, changes):
    client, headers = admin_client
    response = client.post("/api/admin/accounts/no-such-user/reset-password", headers=headers, json=payload(**changes))
    assert response.status_code == 422
    assert not any(value in response.text for value in (PASSWORD, "new123", "DO-NOT-ECHO", "different"))


def test_self_reset_revokes_own_session(admin_client):
    client, headers = admin_client
    user_id = client.get("/api/auth/me").json()["user"]["user_id"]
    response = client.post(f"/api/admin/accounts/{user_id}/reset-password", headers=headers, json=payload())
    assert response.json() == {"reset": True, "reauthenticate": True}
    assert client.get("/api/admin/status").status_code == 401


def test_reset_missing_target_rate_limit_and_nonadmin(admin_client):
    client, headers = admin_client
    url = "/api/admin/accounts/missing/reset-password"
    assert client.post(url, headers=headers, json=payload()).status_code == 404
    for _ in range(9):
        assert client.post(url, headers=headers, json=payload(admin_password="wrong")).status_code == 403
    assert client.post(url, headers=headers, json=payload()).status_code == 429
    store = client.app.state.auth_store
    student = store.register("student02", "학생", PASSWORD)
    token, csrf = store.create_session(student["user_id"])
    client.cookies.set(COOKIE_NAME, token)
    assert client.post(url, headers={"X-Requested-With": "ElectricianSimulator", "X-CSRF-Token": csrf}, json=payload()).status_code == 403
