from __future__ import annotations

import json

from app.database import SQLiteDatabase
from app.domain import OperationCheckResult, OperationProgress


class OperationRepository:
    def __init__(self, database: SQLiteDatabase):
        self.database = database

    def save_attempt(
        self,
        *,
        problem_id: str,
        problem_version: int,
        wiring_attempt_id: int,
        result: OperationCheckResult,
        fault_codes: list[str],
    ) -> int:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO operation_attempts(
                    problem_id, problem_version, wiring_attempt_id, passed_count, total_count,
                    overall_passed, gradable, fault_codes_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    problem_id,
                    problem_version,
                    wiring_attempt_id,
                    result.passed_count,
                    result.total_count,
                    None if result.overall_passed is None else int(result.overall_passed),
                    int(result.gradable),
                    json.dumps(sorted(set(fault_codes)), ensure_ascii=False),
                ),
            )
        return int(cursor.lastrowid)

    def progress(self, problem_id: str) -> OperationProgress:
        with self.database.connect() as connection:
            count = connection.execute(
                "SELECT COUNT(*) AS count FROM operation_attempts WHERE problem_id = ?", (problem_id,)
            ).fetchone()["count"]
            row = connection.execute(
                """SELECT submitted_at, overall_passed, gradable, passed_count, total_count
                   FROM operation_attempts WHERE problem_id = ? ORDER BY id DESC LIMIT 1""",
                (problem_id,),
            ).fetchone()
        if row is None:
            return OperationProgress(problem_id=problem_id)
        return OperationProgress(
            problem_id=problem_id,
            attempt_count=count,
            last_submitted_at=row["submitted_at"],
            last_overall_passed=None if row["overall_passed"] is None else bool(row["overall_passed"]),
            last_gradable=bool(row["gradable"]),
            last_passed_count=row["passed_count"],
            total_count=row["total_count"],
        )
