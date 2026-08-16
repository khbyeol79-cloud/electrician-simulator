from __future__ import annotations

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
    assert version == "4"

    with database.connect() as connection:
        tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"circuit_attempts", "circuit_attempt_responses", "wiring_drafts", "wiring_attempts", "mounting_drafts", "mounting_attempts"}.issubset(tables)
