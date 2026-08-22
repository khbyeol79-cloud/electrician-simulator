from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_VERSION = "9"


class _ClosingSQLiteConnection(sqlite3.Connection):
    """Commit or roll back a context block, then release the SQLite file handle.

    ``sqlite3.Connection`` normally leaves the connection open after ``with``.
    Repository code uses ``with database.connect()`` as the transaction and
    lifetime boundary, so keeping that handle alive prevents temporary user
    databases from being removed on Windows.
    """

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        try:
            return bool(super().__exit__(exc_type, exc_value, traceback))
        finally:
            self.close()


class SQLiteDatabase:
    def __init__(self, database_file: Path):
        self.database_file = database_file

    def connect(self) -> sqlite3.Connection:
        self.database_file.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            self.database_file,
            factory=_ClosingSQLiteConnection,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS app_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS learning_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id TEXT NOT NULL,
                    problem_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    score REAL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(profile_id, problem_id, stage)
                );

                CREATE TABLE IF NOT EXISTS circuit_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id TEXT NOT NULL,
                    problem_version INTEGER NOT NULL,
                    answer_version INTEGER NOT NULL,
                    submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    answered_count INTEGER NOT NULL,
                    total_count INTEGER NOT NULL,
                    correct_count INTEGER NOT NULL,
                    overall_correct INTEGER,
                    gradable INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS circuit_attempt_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id INTEGER NOT NULL,
                    question_id TEXT NOT NULL,
                    slot_id TEXT NOT NULL,
                    selected_pin INTEGER NOT NULL,
                    is_correct INTEGER,
                    FOREIGN KEY(attempt_id) REFERENCES circuit_attempts(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS wiring_drafts (
                    problem_id TEXT PRIMARY KEY,
                    problem_version INTEGER NOT NULL,
                    mode TEXT NOT NULL,
                    connections_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS wiring_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id TEXT NOT NULL,
                    problem_version INTEGER NOT NULL,
                    answer_version INTEGER NOT NULL,
                    submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    required_count INTEGER NOT NULL,
                    correct_count INTEGER NOT NULL,
                    overall_correct INTEGER,
                    gradable INTEGER NOT NULL,
                    connections_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS mounting_drafts (
                    problem_id TEXT PRIMARY KEY,
                    problem_version INTEGER NOT NULL,
                    placements_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS mounting_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id TEXT NOT NULL,
                    problem_version INTEGER NOT NULL,
                    answer_version INTEGER NOT NULL,
                    submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    required_count INTEGER NOT NULL,
                    correct_count INTEGER NOT NULL,
                    overall_correct INTEGER,
                    gradable INTEGER NOT NULL,
                    placements_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS operation_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id TEXT NOT NULL,
                    problem_version INTEGER NOT NULL,
                    wiring_attempt_id INTEGER NOT NULL,
                    submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    passed_count INTEGER NOT NULL,
                    total_count INTEGER NOT NULL,
                    overall_passed INTEGER,
                    gradable INTEGER NOT NULL,
                    fault_codes_json TEXT NOT NULL,
                    FOREIGN KEY(wiring_attempt_id) REFERENCES wiring_attempts(id)
                );

                CREATE TABLE IF NOT EXISTS operation_progress_flags (
                    problem_id TEXT PRIMARY KEY,
                    problem_version INTEGER NOT NULL,
                    wiring_attempt_id INTEGER NOT NULL,
                    manual_run_count INTEGER NOT NULL DEFAULT 0,
                    last_run_at TEXT,
                    forward_seen INTEGER NOT NULL DEFAULT 0,
                    reverse_seen INTEGER NOT NULL DEFAULT 0,
                    interlock_seen INTEGER NOT NULL DEFAULT 0,
                    protection_trip_seen INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(wiring_attempt_id) REFERENCES wiring_attempts(id)
                );

                CREATE TABLE IF NOT EXISTS free_circuit_workspaces (
                    workspace_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    circuit_json TEXT NOT NULL,
                    operation_json TEXT NOT NULL,
                    connections_json TEXT NOT NULL,
                    board_json TEXT,
                    device_layout_json TEXT,
                    wiring_semantics_json TEXT,
                    editor_json TEXT,
                    assembly_json TEXT,
                    schema_version TEXT NOT NULL DEFAULT '1.0',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(free_circuit_workspaces)").fetchall()
            }
            migrations = {
                "board_json": "ALTER TABLE free_circuit_workspaces ADD COLUMN board_json TEXT",
                "device_layout_json": "ALTER TABLE free_circuit_workspaces ADD COLUMN device_layout_json TEXT",
                "wiring_semantics_json": "ALTER TABLE free_circuit_workspaces ADD COLUMN wiring_semantics_json TEXT",
                "editor_json": "ALTER TABLE free_circuit_workspaces ADD COLUMN editor_json TEXT",
                "assembly_json": "ALTER TABLE free_circuit_workspaces ADD COLUMN assembly_json TEXT",
                "schema_version": "ALTER TABLE free_circuit_workspaces ADD COLUMN schema_version TEXT NOT NULL DEFAULT '1.0'",
            }
            for column, statement in migrations.items():
                if column not in columns:
                    connection.execute(statement)
            connection.execute(
                """
                INSERT INTO app_meta(key, value) VALUES('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (SCHEMA_VERSION,),
            )

    def is_ready(self) -> bool:
        try:
            with self.connect() as connection:
                rows = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            names = {row["name"] for row in rows}
            return {"app_meta", "user_settings", "learning_progress", "circuit_attempts", "circuit_attempt_responses", "wiring_drafts", "wiring_attempts", "mounting_drafts", "mounting_attempts", "operation_attempts", "operation_progress_flags", "free_circuit_workspaces"}.issubset(names)
        except sqlite3.Error:
            return False
