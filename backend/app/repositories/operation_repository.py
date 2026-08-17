from __future__ import annotations

import json

from app.database import SQLiteDatabase
from app.domain import OperationCheckResult, OperationProgress, OperationSessionState


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

    def start_manual_run(self, *, problem_id: str, problem_version: int, wiring_attempt_id: int) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO operation_progress_flags(
                    problem_id, problem_version, wiring_attempt_id, manual_run_count, last_run_at
                ) VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(problem_id) DO UPDATE SET
                    problem_version=excluded.problem_version,
                    wiring_attempt_id=excluded.wiring_attempt_id,
                    manual_run_count=operation_progress_flags.manual_run_count + 1,
                    last_run_at=CURRENT_TIMESTAMP
                """,
                (problem_id, problem_version, wiring_attempt_id),
            )

    def observe_state(self, *, problem_id: str, problem_version: int, state: OperationSessionState) -> None:
        forward = any(value == "forward" for value in state.motors.values())
        reverse = any(value == "reverse" for value in state.motors.values())
        interlock = any(value.status == "blocking" for value in state.interlocks.values())
        protection = any(value.status != "normal" for value in state.protections.values())
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO operation_progress_flags(
                    problem_id, problem_version, wiring_attempt_id, last_run_at,
                    forward_seen, reverse_seen, interlock_seen, protection_trip_seen
                ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)
                ON CONFLICT(problem_id) DO UPDATE SET
                    problem_version=excluded.problem_version,
                    wiring_attempt_id=excluded.wiring_attempt_id,
                    last_run_at=CURRENT_TIMESTAMP,
                    forward_seen=MAX(operation_progress_flags.forward_seen, excluded.forward_seen),
                    reverse_seen=MAX(operation_progress_flags.reverse_seen, excluded.reverse_seen),
                    interlock_seen=MAX(operation_progress_flags.interlock_seen, excluded.interlock_seen),
                    protection_trip_seen=MAX(operation_progress_flags.protection_trip_seen, excluded.protection_trip_seen)
                """,
                (problem_id, problem_version, state.wiring_attempt_id, int(forward), int(reverse), int(interlock), int(protection)),
            )

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
            flags = connection.execute(
                """SELECT manual_run_count, last_run_at, forward_seen, reverse_seen,
                          interlock_seen, protection_trip_seen
                   FROM operation_progress_flags WHERE problem_id = ?""",
                (problem_id,),
            ).fetchone()
        extras = {
            "manual_run_count": flags["manual_run_count"] if flags else 0,
            "last_run_at": flags["last_run_at"] if flags else None,
            "forward_seen": bool(flags["forward_seen"]) if flags else False,
            "reverse_seen": bool(flags["reverse_seen"]) if flags else False,
            "interlock_seen": bool(flags["interlock_seen"]) if flags else False,
            "protection_trip_seen": bool(flags["protection_trip_seen"]) if flags else False,
        }
        if row is None:
            return OperationProgress(problem_id=problem_id, **extras)
        return OperationProgress(
            problem_id=problem_id,
            attempt_count=count,
            last_submitted_at=row["submitted_at"],
            last_overall_passed=None if row["overall_passed"] is None else bool(row["overall_passed"]),
            last_gradable=bool(row["gradable"]),
            last_passed_count=row["passed_count"],
            total_count=row["total_count"],
            **extras,
        )
