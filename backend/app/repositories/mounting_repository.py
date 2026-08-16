from __future__ import annotations

import json
from datetime import datetime

from app.database import SQLiteDatabase
from app.domain import (
    MountingAttemptResult, MountingDraftResponse, MountingDraftUpdate,
    MountingProgress,
)


class MountingRepository:
    def __init__(self, database: SQLiteDatabase):
        self.database = database

    def save_draft(self, problem_id: str, draft: MountingDraftUpdate) -> MountingDraftResponse:
        payload = json.dumps([item.model_dump(mode="json") for item in draft.placements], ensure_ascii=False)
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO mounting_drafts(problem_id, problem_version, placements_json, updated_at)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(problem_id) DO UPDATE SET problem_version=excluded.problem_version,
                   placements_json=excluded.placements_json, updated_at=CURRENT_TIMESTAMP""",
                (problem_id, draft.problem_version, payload),
            )
        return self.get_draft(problem_id) or MountingDraftResponse(problem_id=problem_id, **draft.model_dump())

    def get_draft(self, problem_id: str) -> MountingDraftResponse | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM mounting_drafts WHERE problem_id = ?", (problem_id,)).fetchone()
        if row is None:
            return None
        return MountingDraftResponse(
            problem_id=problem_id,
            problem_version=row["problem_version"],
            placements=json.loads(row["placements_json"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def delete_draft(self, problem_id: str) -> None:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM mounting_drafts WHERE problem_id = ?", (problem_id,))

    def save_attempt(
        self,
        problem_id: str,
        problem_version: int,
        answer_version: int,
        placements: list[dict],
        result: MountingAttemptResult,
    ) -> int:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO mounting_attempts(problem_id, problem_version, answer_version,
                   required_count, correct_count, overall_correct, gradable, placements_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    problem_id, problem_version, answer_version, result.required_count,
                    result.correct_count,
                    None if result.overall_correct is None else int(result.overall_correct),
                    int(result.gradable), json.dumps(placements, ensure_ascii=False),
                ),
            )
        return int(cursor.lastrowid)

    def progress(self, problem_id: str) -> MountingProgress:
        with self.database.connect() as connection:
            count = connection.execute(
                "SELECT COUNT(*) AS count FROM mounting_attempts WHERE problem_id = ?", (problem_id,)
            ).fetchone()["count"]
            row = connection.execute(
                """SELECT submitted_at, overall_correct, correct_count, required_count
                   FROM mounting_attempts WHERE problem_id = ? ORDER BY id DESC LIMIT 1""",
                (problem_id,),
            ).fetchone()
        if row is None:
            return MountingProgress(problem_id=problem_id, attempt_count=0)
        return MountingProgress(
            problem_id=problem_id,
            attempt_count=count,
            last_submitted_at=datetime.fromisoformat(row["submitted_at"]),
            last_overall_correct=None if row["overall_correct"] is None else bool(row["overall_correct"]),
            last_correct_count=row["correct_count"],
            required_count=row["required_count"],
        )
