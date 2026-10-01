from __future__ import annotations

import sqlite3

import pytest

from app.database import SQLiteDatabase


def test_database_initialization_is_idempotent(tmp_path):
    database = SQLiteDatabase(tmp_path / "test.db")
    database.initialize()
    database.initialize()
    assert database.is_ready() is True

    with database.connect() as connection:
        version = connection.execute(
            "SELECT value FROM app_meta WHERE key='schema_version'"
        ).fetchone()["value"]
        assert version == "12"
    with database.connect() as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(free_circuit_workspaces)")}
    assert "assembly_json" in columns

    with database.connect() as connection:
        tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"circuit_attempts", "circuit_attempt_responses", "circuit_analysis_drafts", "wiring_drafts", "practice_wiring_drafts", "practice_wiring_snapshots", "wiring_attempts", "mounting_drafts", "mounting_attempts", "operation_attempts", "operation_progress_flags", "free_circuit_workspaces"}.issubset(tables)


def test_database_context_releases_file_handle(tmp_path):
    database_file = tmp_path / "temporary-user.db"
    database = SQLiteDatabase(database_file)
    database.initialize()

    with database.connect() as connection:
        assert connection.execute("SELECT 1").fetchone()[0] == 1

    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        connection.execute("SELECT 1")

    database_file.unlink()
    assert database_file.exists() is False


def test_version_5_database_is_upgraded_without_losing_user_settings(tmp_path):
    database_file = tmp_path / "legacy-0.7.db"
    with sqlite3.connect(database_file) as connection:
        connection.executescript(
            """
            CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE user_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO app_meta(key, value) VALUES('schema_version', '5');
            INSERT INTO user_settings(key, value) VALUES('selected_problem_id', 'operation_demo_001');
            """
        )

    database = SQLiteDatabase(database_file)
    database.initialize()

    with database.connect() as connection:
        version = connection.execute(
            "SELECT value FROM app_meta WHERE key='schema_version'"
        ).fetchone()["value"]
        selected = connection.execute(
            "SELECT value FROM user_settings WHERE key='selected_problem_id'"
        ).fetchone()["value"]
    assert version == "12"
    assert selected == "operation_demo_001"

    with database.connect() as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(free_circuit_workspaces)")}
    assert {"board_json", "device_layout_json", "wiring_semantics_json", "editor_json", "schema_version"}.issubset(columns)
    assert database.is_ready() is True


def test_schema_11_practice_draft_is_migrated_without_data_loss(tmp_path):
    database_file = tmp_path / "legacy-practice.db"
    database = SQLiteDatabase(database_file)
    database.initialize()
    with database.connect() as connection:
        connection.execute(
            """INSERT INTO practice_wiring_drafts(
                   problem_id, workspace_id, problem_version, mode, connections_json)
               VALUES ('qnet_electrician_practical_010', 'legacy', 1, 'graphic', '[{"from":"F-1","to":"F-2"}]')"""
        )
        connection.execute("UPDATE app_meta SET value='11' WHERE key='schema_version'")
    database.initialize()
    database.initialize()
    with database.connect() as connection:
        row = connection.execute(
            "SELECT * FROM practice_wiring_drafts WHERE workspace_id='legacy'"
        ).fetchone()
        version = connection.execute("SELECT value FROM app_meta WHERE key='schema_version'").fetchone()[0]
    assert version == "12"
    assert row["connections_json"] == '[{"from":"F-1","to":"F-2"}]'
    assert row["workspace_name"] == "기본 작업공간"
    assert row["created_at"] is not None
