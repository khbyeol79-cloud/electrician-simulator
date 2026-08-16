from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_VERSION = "1"


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
            return {"app_meta", "user_settings", "learning_progress"}.issubset(names)
        except sqlite3.Error:
            return False

