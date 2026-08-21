from __future__ import annotations

import sqlite3

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
    assert version == "7"

    with database.connect() as connection:
        tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"circuit_attempts", "circuit_attempt_responses", "wiring_drafts", "wiring_attempts", "mounting_drafts", "mounting_attempts", "operation_attempts", "operation_progress_flags", "free_circuit_workspaces"}.issubset(tables)


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
    assert version == "7"
    assert selected == "operation_demo_001"
    assert database.is_ready() is True
