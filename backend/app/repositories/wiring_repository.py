from __future__ import annotations

import json
from datetime import datetime

from app.database import SQLiteDatabase
from app.domain import WiringAttemptResult, WiringDraftResponse, WiringDraftUpdate, WiringProgress


class WiringRepository:
    def __init__(self, database: SQLiteDatabase):
        self.database = database

    def save_draft(self, problem_id: str, draft: WiringDraftUpdate) -> WiringDraftResponse:
        payload = json.dumps([item.model_dump(by_alias=True, mode="json") for item in draft.connections], ensure_ascii=False)
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO wiring_drafts(problem_id, problem_version, mode, connections_json, updated_at)
                   VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(problem_id) DO UPDATE SET problem_version=excluded.problem_version,
                   mode=excluded.mode, connections_json=excluded.connections_json, updated_at=CURRENT_TIMESTAMP""",
                (problem_id, draft.problem_version, draft.mode, payload),
            )
        return self.get_draft(problem_id) or WiringDraftResponse(problem_id=problem_id, **draft.model_dump())

    def get_draft(self, problem_id: str) -> WiringDraftResponse | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM wiring_drafts WHERE problem_id = ?", (problem_id,)).fetchone()
        if row is None:
            return None
        return WiringDraftResponse(
            problem_id=problem_id, problem_version=row["problem_version"], mode=row["mode"],
            connections=json.loads(row["connections_json"]), updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def delete_draft(self, problem_id: str) -> None:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM wiring_drafts WHERE problem_id = ?", (problem_id,))

    def save_attempt(self, problem_id: str, problem_version: int, answer_version: int, connections: list[dict], result: WiringAttemptResult) -> int:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO wiring_attempts(problem_id, problem_version, answer_version, required_count,
                   correct_count, overall_correct, gradable, connections_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (problem_id, problem_version, answer_version, result.required_count, result.correct_count,
                 None if result.overall_correct is None else int(result.overall_correct), int(result.gradable),
                 json.dumps(connections, ensure_ascii=False)),
            )
        return int(cursor.lastrowid)

    def progress(self, problem_id: str) -> WiringProgress:
        with self.database.connect() as connection:
            count = connection.execute("SELECT COUNT(*) AS count FROM wiring_attempts WHERE problem_id = ?", (problem_id,)).fetchone()["count"]
            row = connection.execute("SELECT submitted_at, overall_correct, correct_count, required_count FROM wiring_attempts WHERE problem_id = ? ORDER BY id DESC LIMIT 1", (problem_id,)).fetchone()
        if row is None:
            return WiringProgress(problem_id=problem_id, attempt_count=0)
        return WiringProgress(problem_id=problem_id, attempt_count=count, last_submitted_at=datetime.fromisoformat(row["submitted_at"]), last_overall_correct=None if row["overall_correct"] is None else bool(row["overall_correct"]), last_correct_count=row["correct_count"], required_count=row["required_count"])
