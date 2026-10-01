from contextlib import closing
from pathlib import Path
import sqlite3
import zipfile

import pytest

from app.core.auth import AuthStore
from scripts import build_lan_release as release
from scripts.restore_service_backup import restore_and_select
from scripts.service_data import backup
from scripts.service_lifecycle import ServiceLease

PROJECT = Path(__file__).resolve().parents[2]


def backup_fixture(tmp_path):
    source = tmp_path / "original"
    store = AuthStore(source / "accounts.db")
    store.initialize()
    account = store.register("student01", "학생", "test123")
    store.set_admin("student01", True)
    store.save_service_option("network", {"host": "192.168.99.99", "port": 9876}, "student01")
    store.save_service_option("registration_open", False, "student01")
    user_db = source / "users" / (account["user_id"] + ".db")
    user_db.parent.mkdir()
    with closing(sqlite3.connect(user_db)) as db:
        db.execute("CREATE TABLE notes(text TEXT)")
        db.execute("INSERT INTO notes VALUES ('학습자료')")
        db.commit()
    archive = tmp_path / "백업 파일.zip"
    backup(source, archive)
    project = tmp_path / "새 PC"
    (project / "deploy").mkdir(parents=True)
    (project / "deploy/lan.env.example").write_bytes((PROJECT / "deploy/lan.env.example").read_bytes())
    return project, source, archive, account


def test_restore_selects_portable_copy_preserves_original_accounts_and_records(tmp_path):
    project, source, archive, account = backup_fixture(tmp_path)
    original = (source / "accounts.db").read_bytes()
    restored = restore_and_select(project, archive)
    assert restored.is_relative_to(project / "restored-data")
    config = (project / "service-config/service.env").read_text(encoding="utf-8")
    assert "ELECTRICIAN_DATA_DIR=" + restored.relative_to(project).as_posix() in config
    assert "APP_HOST=0.0.0.0" in config
    store = AuthStore(restored / "accounts.db")
    assert store.login("student01", "test123") == account
    assert store.is_admin(account["user_id"])
    assert store.service_option("network") is None
    assert store.service_option("registration_open") is False
    assert (source / "accounts.db").read_bytes() == original
    with closing(sqlite3.connect(restored / "users" / (account["user_id"] + ".db"))) as db:
        assert db.execute("SELECT text FROM notes").fetchone()[0] == "학습자료"
    second = restore_and_select(project, archive)
    assert second != restored and restored.is_dir()
    assert list((project / "service-config").glob("service.env.before-restore-*"))


def test_live_server_blocks_restore_and_config_stays_unchanged(tmp_path):
    project, _, archive, _ = backup_fixture(tmp_path)
    with ServiceLease(project / "user-data"):
        with pytest.raises(RuntimeError, match="중복"):
            restore_and_select(project, archive)
    assert not (project / "service-config/service.env").exists()
    assert not (project / "restored-data").exists()


@pytest.mark.parametrize("malformed", ["corrupt", "traversal"])
def test_bad_backup_never_switches_existing_data(tmp_path, malformed):
    project, _, archive, _ = backup_fixture(tmp_path)
    config = project / "service-config/service.env"
    config.parent.mkdir()
    config.write_text("ELECTRICIAN_DATA_DIR=user-data\nAPP_PORT=8765\nAUTH_COOKIE_SECURE=true\n", encoding="utf-8")
    old_config = config.read_bytes()
    if malformed == "corrupt":
        archive.write_bytes(b"not a zip")
    else:
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("../escape.db", b"bad")
            output.writestr("manifest.json", "{}")
    with pytest.raises((ValueError, zipfile.BadZipFile)):
        restore_and_select(project, archive)
    assert config.read_bytes() == old_config
    assert not (project / "escape.db").exists()


def test_restore_keeps_target_pc_transport_configuration(tmp_path):
    project, _, archive, _ = backup_fixture(tmp_path)
    config = project / "service-config/service.env"
    config.parent.mkdir()
    config.write_text("ELECTRICIAN_DATA_DIR=user-data\nAPP_PORT=8765\nAUTH_COOKIE_SECURE=true\n", encoding="utf-8")
    restore_and_select(project, archive)
    text = config.read_text(encoding="utf-8")
    assert "APP_PORT=8765" in text and "AUTH_COOKIE_SECURE=true" in text
    assert text.count("ELECTRICIAN_DATA_DIR=") == 1


def test_runtime_allowlist_excludes_private_user_and_development_files():
    paths = [p.relative_to(PROJECT).as_posix() for p in release.release_files(PROJECT)]
    for path in paths:
        assert not any(part in path.split("/") for part in (
            "user-data", "restored-data", "service-config", "user-data-backups", "node_modules", "docs", "tests", ".git"))
        assert not path.endswith((".db", ".log", ".map", ".key", ".pem"))
    assert "free_templates/basic_board_001/template.json" in paths
    for n in range(1, 19):
        assert f"problems/qnet_electrician_practical_{n:03d}/answer.json" in paths
        assert f"problems/qnet_electrician_practical_{n:03d}/layout-reference.png" in paths


def test_failed_build_never_creates_release(tmp_path, monkeypatch):
    def fail(_):
        raise RuntimeError("build failed")
    monkeypatch.setattr(release, "build_frontend", fail)
    with pytest.raises(RuntimeError, match="build failed"):
        release.create_release(PROJECT, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_bats_use_relative_quoted_paths_and_web_only_install():
    restore_bat = (PROJECT / "백업_복원.bat").read_text(encoding="utf-8")
    assert 'set "BACKUP_FILE=' in restore_bat
    assert '"%BACKUP_FILE%"' in restore_bat
    for name in ("배포ZIP_만들기.bat", "백업_복원.bat", "서버_최초설치.bat"):
        assert 'cd /d "%~dp0"' in (PROJECT / name).read_text(encoding="utf-8")
    assert "-WebOnly" in (PROJECT / "서버_최초설치.bat").read_text(encoding="utf-8")
