from __future__ import annotations

from datetime import datetime

from app.database import SQLiteDatabase
from app.domain import CircuitAttemptResult, CircuitProgress


class CircuitAttemptRepository:
    def __init__(self, database: SQLiteDatabase):
        self.database = database

    def save(
        self,
        *,
        problem_id: str,
        problem_version: int,
        answer_version: int,
        responses: dict[str, dict[str, int]],
        result: CircuitAttemptResult,
    ) -> int:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO circuit_attempts(
                    problem_id, problem_version, answer_version, answered_count,
                    total_count, correct_count, overall_correct, gradable
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    problem_id, problem_version, answer_version,
                    result.answered_count, result.total_count, result.correct_count,
                    None if result.overall_correct is None else int(result.overall_correct),
                    int(result.gradable),
                ),
            )
            attempt_id = int(cursor.lastrowid)
            result_by_question = {item.question_id: item for item in result.results}
            for question_id, slots in responses.items():
                question_result = result_by_question.get(question_id)
                for slot_id, selected_pin in slots.items():
                    is_correct = None
                    if question_result is not None:
                        is_correct = int(question_result.slot_results.get(slot_id, False))
                    connection.execute(
                        """
                        INSERT INTO circuit_attempt_responses(
                            attempt_id, question_id, slot_id, selected_pin, is_correct
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (attempt_id, question_id, slot_id, selected_pin, is_correct),
                    )
        return attempt_id

    def progress(self, problem_id: str) -> CircuitProgress:
        with self.database.connect() as connection:
            count = connection.execute(
                "SELECT COUNT(*) AS count FROM circuit_attempts WHERE problem_id = ?",
                (problem_id,),
            ).fetchone()["count"]
            row = connection.execute(
                """
                SELECT submitted_at, overall_correct, correct_count, total_count
                FROM circuit_attempts WHERE problem_id = ? ORDER BY id DESC LIMIT 1
                """,
                (problem_id,),
            ).fetchone()
        if row is None:
            return CircuitProgress(problem_id=problem_id, attempt_count=0)
        return CircuitProgress(
            problem_id=problem_id,
            attempt_count=count,
            last_submitted_at=datetime.fromisoformat(row["submitted_at"]),
            last_overall_correct=None if row["overall_correct"] is None else bool(row["overall_correct"]),
            last_correct_count=row["correct_count"],
            total_count=row["total_count"],
        )
