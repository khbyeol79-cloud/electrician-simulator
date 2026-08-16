from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_VERSION = "4"


class SQLiteDatabase:
    def __init__(self, database_file: Path):
        self.database_file = database_file

    def connect(self) -> sqlite3.Connection:
        self.database_file.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_file)
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
                """
            )
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
            return {"app_meta", "user_settings", "learning_progress", "circuit_attempts", "circuit_attempt_responses", "wiring_drafts", "wiring_attempts", "mounting_drafts", "mounting_attempts"}.issubset(names)
        except sqlite3.Error:
            return False
