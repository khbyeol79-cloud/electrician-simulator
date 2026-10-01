from __future__ import annotations

import json
from datetime import datetime

from app.database import SQLiteDatabase
from app.domain.circuit_analysis_draft import CircuitAnalysisDraftResponse, CircuitAnalysisDraftUpdate


class CircuitAnalysisDraftRepository:
    def __init__(self, database: SQLiteDatabase):
        self.database = database

    def get(self, problem_id: str) -> CircuitAnalysisDraftResponse | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM circuit_analysis_drafts WHERE problem_id = ?", (problem_id,)
            ).fetchone()
        if row is None:
            return None
        return CircuitAnalysisDraftResponse(
            problem_id=problem_id,
            problem_version=row["problem_version"],
            memo=row["memo"],
            selected_device_ids=json.loads(row["selected_device_ids_json"]),
            selected_socket_ids=json.loads(row["selected_socket_ids_json"]),
            selected_terminal_ids=json.loads(row["selected_terminal_ids_json"]),
            annotations=json.loads(row["annotations_json"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def save(self, problem_id: str, draft: CircuitAnalysisDraftUpdate) -> CircuitAnalysisDraftResponse:
        values = (
            problem_id, draft.problem_version, draft.memo,
            json.dumps(draft.selected_device_ids, ensure_ascii=False),
            json.dumps(draft.selected_socket_ids, ensure_ascii=False),
            json.dumps(draft.selected_terminal_ids, ensure_ascii=False),
            json.dumps(draft.annotations, ensure_ascii=False),
        )
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO circuit_analysis_drafts(
                       problem_id, problem_version, memo, selected_device_ids_json,
                       selected_socket_ids_json, selected_terminal_ids_json, annotations_json, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(problem_id) DO UPDATE SET
                       problem_version=excluded.problem_version, memo=excluded.memo,
                       selected_device_ids_json=excluded.selected_device_ids_json,
                       selected_socket_ids_json=excluded.selected_socket_ids_json,
                       selected_terminal_ids_json=excluded.selected_terminal_ids_json,
                       annotations_json=excluded.annotations_json, updated_at=CURRENT_TIMESTAMP""",
                values,
            )
        return self.get(problem_id) or CircuitAnalysisDraftResponse(problem_id=problem_id, **draft.model_dump())

    def delete(self, problem_id: str) -> None:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM circuit_analysis_drafts WHERE problem_id = ?", (problem_id,))
