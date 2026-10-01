from dataclasses import replace
import shutil

from fastapi.testclient import TestClient
import pytest

from app.core import paths
from app.core.config import Settings, load_settings
from app.main import create_app
from test_lan_accounts import PASSWORD, PID, register


@pytest.fixture
def portable_environment(tmp_path, monkeypatch):
    for key in ("ELECTRICIAN_DATA_DIR", "AUTH_REQUIRED", "ALLOW_LAN", "APP_ENV", "ALLOWED_ORIGINS"):
        monkeypatch.delenv(key, raising=False)
    root = tmp_path / "program"
    root.mkdir()
    other = tmp_path / "unrelated-working-directory"
    other.mkdir()
    monkeypatch.chdir(other)
    monkeypatch.setattr(paths, "_project_root", lambda: root)
    monkeypatch.setattr(paths, "_bundle_root", lambda: root)
    return root


@pytest.mark.parametrize("key", ["AUTH_REQUIRED", "ALLOW_LAN"])
def test_account_service_defaults_to_program_user_data(portable_environment, monkeypatch, key):
    monkeypatch.setenv(key, "true")
    settings = load_settings()
    assert settings.auth_required
    assert settings.paths.writable_root == portable_environment / "user-data"
    assert settings.paths.database_file == portable_environment / "user-data/app.db"
    assert not settings.paths.writable_root.exists()  # Path discovery never migrates/creates DBs.


def test_relative_setting_tracks_program_after_folder_move(portable_environment, tmp_path, monkeypatch):
    monkeypatch.setenv("ELECTRICIAN_DATA_DIR", "user-data")
    assert paths.build_paths().writable_root == portable_environment / "user-data"
    usb_copy = tmp_path / "usb-copy/program"
    usb_copy.mkdir(parents=True)
    monkeypatch.setattr(paths, "_bundle_root", lambda: usb_copy)
    assert paths.build_paths().writable_root == usb_copy / "user-data"


def test_absolute_existing_data_override_is_preserved(portable_environment, tmp_path, monkeypatch):
    existing = tmp_path / "existing-service-data"
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("ELECTRICIAN_DATA_DIR", str(existing))
    assert paths.build_paths().writable_root == existing


def test_service_launcher_accepts_portable_sample_path(portable_environment, monkeypatch, tmp_path):
    import sys
    import uvicorn
    from scripts.run_service import main
    config = tmp_path / "service.env"
    config.write_text("ELECTRICIAN_DATA_DIR=user-data\nALLOW_LAN=false\nAPP_HOST=127.0.0.1\n", encoding="utf-8")
    static = portable_environment / "frontend/dist"
    static.mkdir(parents=True)
    (static / "index.html").write_text("<html>test build</html>", encoding="utf-8")
    captured = {}
    def server(app, **kwargs):
        captured["settings"] = app.state.settings
        captured.update(kwargs)
    monkeypatch.setattr(uvicorn, "run", server)  # Never opens a listening socket.
    monkeypatch.setattr(sys, "argv", ["run_service.py", "--env-file", str(config)])
    main()
    assert captured["settings"].paths.writable_root == portable_environment / "user-data"
    assert captured["settings"].auth_required
    assert captured["workers"] == 1


def test_legacy_desktop_locations_are_not_silently_changed(portable_environment, tmp_path, monkeypatch):
    assert paths.build_paths().writable_root == portable_environment / "data/dev"
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    assert paths.build_paths().writable_root == tmp_path / "appdata/ElectricianSimulator"


def test_frozen_service_uses_executable_folder(tmp_path, monkeypatch):
    for key in ("ELECTRICIAN_DATA_DIR", "ALLOW_LAN"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(paths.sys, "executable", str(tmp_path / "portable/Simulator.exe"))
    assert paths.build_paths().writable_root == tmp_path / "portable/user-data"


@pytest.mark.parametrize("suffix", ["frontend/dist", "frontend/dist/user-data"])
def test_account_data_cannot_be_saved_under_public_static_folder(portable_environment, monkeypatch, suffix):
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("ELECTRICIAN_DATA_DIR", suffix)
    with pytest.raises(ValueError, match="공개 정적 웹 폴더"):
        load_settings()


def test_stopped_program_folder_copy_preserves_accounts_and_saved_work(tmp_path, monkeypatch):
    # Only temporary test data is copied; real desktop/LAN stores are untouched.
    real_resources = paths.build_paths()
    for key in ("ELECTRICIAN_DATA_DIR", "ALLOWED_ORIGINS"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    first, copied = tmp_path / "first-program", tmp_path / "usb-copy"
    first.mkdir()

    def settings_for(root):
        monkeypatch.setattr(paths, "_project_root", lambda: root)
        monkeypatch.setattr(paths, "_bundle_root", lambda: root)
        settings = load_settings()
        # Reuse read-only problem/static resources, isolate writable paths.
        settings.paths = replace(settings.paths, project_root=real_resources.project_root,
                                 bundle_root=real_resources.bundle_root,
                                 problems_dir=real_resources.problems_dir, catalog_dir=real_resources.catalog_dir,
                                 frontend_dist=real_resources.frontend_dist)
        return settings

    draft_url = f"/api/problems/{PID}/practice-drafts/portable"
    with TestClient(create_app(settings_for(first))) as client:
        account, headers = register(client)
        response = client.put(draft_url, headers=headers, json={"problem_version": 1, "workspace_name": "USB 이동 연습",
                              "connections": [{"from": "F-1", "to": "MCCB-T1", "wire_color": "yellow"}]})
        assert response.status_code == 200
    shutil.copytree(first, copied)  # Server/lifespan already stopped.
    unrelated = tmp_path / "another-working-directory"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)
    with TestClient(create_app(settings_for(copied))) as client:
        login = client.post("/api/auth/login", headers={"X-Requested-With": "ElectricianSimulator"},
                            json={"username": "student01", "password": PASSWORD})
        assert login.status_code == 200
        assert login.json()["user"] == account["user"]
        saved = client.get(draft_url).json()
        assert saved["workspace_name"] == "USB 이동 연습"
        assert saved["connections"][0]["from"] == "F-1"
        for resource in ("/user-data/accounts.db", f"/user-data/users/{account['user']['user_id']}.db"):
            response = client.get(resource)
            assert not response.content.startswith(b"SQLite format 3")
            assert response.headers.get("content-type", "").startswith("text/html") or response.status_code == 404
    assert (first / "user-data/accounts.db").exists()
    assert (copied / "user-data/accounts.db").exists()
