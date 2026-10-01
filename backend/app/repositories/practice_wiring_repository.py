from __future__ import annotations

import json
from datetime import datetime
from secrets import token_urlsafe

from app.database import SQLiteDatabase
from app.domain import (
    PracticeWiringDraftResponse, StructuralWarning, WiringCaptureDraftResponse,
    WiringCaptureUpdate, WiringConnection, WiringDraftUpdate, WiringSnapshotResponse,
    WiringWorkspaceSummary,
)


def _time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class PracticeWiringRepository:
    def __init__(self, database: SQLiteDatabase):
        self.database = database

    def save_capture(self, problem_id: str, workspace_id: str, draft: WiringCaptureUpdate, warnings=()):
        payload = json.dumps([item.model_dump(by_alias=True, mode="json") for item in draft.connections], ensure_ascii=False)
        warning_payload = json.dumps([item.model_dump(mode="json") for item in warnings], ensure_ascii=False)
        name = draft.workspace_name or ("기본 작업공간" if workspace_id == "main" else "사용자 작업공간")
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO practice_wiring_drafts(
                       problem_id, workspace_id, problem_version, mode, connections_json,
                       workspace_name, warnings_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(problem_id, workspace_id) DO UPDATE SET
                       problem_version=excluded.problem_version, mode=excluded.mode,
                       connections_json=excluded.connections_json,
                       workspace_name=CASE WHEN ? IS NULL THEN practice_wiring_drafts.workspace_name ELSE excluded.workspace_name END,
                       warnings_json=excluded.warnings_json, updated_at=CURRENT_TIMESTAMP""",
                (problem_id, workspace_id, draft.problem_version, draft.mode, payload, name, warning_payload, draft.workspace_name),
            )
        return self.get_capture(problem_id, workspace_id)

    def save(self, problem_id: str, workspace_id: str, draft: WiringDraftUpdate, *, safety_status="safe", safety_issues=()):
        capture = WiringCaptureUpdate.model_validate(draft.model_dump(mode="json"))
        warnings = [StructuralWarning(code=item.code, message=item.message, severity=item.severity) for item in safety_issues]
        self.save_capture(problem_id, workspace_id, capture, warnings)
        return self.get(problem_id, workspace_id, safety_status=safety_status, safety_issues=safety_issues)

    def get_capture(self, problem_id: str, workspace_id: str):
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM practice_wiring_drafts WHERE problem_id=? AND workspace_id=?",
                (problem_id, workspace_id),
            ).fetchone()
        if row is None:
            return None
        structural_warnings = [StructuralWarning.model_validate(item) for item in json.loads(row["warnings_json"])]
        safety_status = "blocked" if any(item.severity == "blocking" for item in structural_warnings) else "attention" if structural_warnings else "safe"
        return WiringCaptureDraftResponse(
            problem_id=problem_id, workspace_id=workspace_id, problem_version=row["problem_version"],
            workspace_name=row["workspace_name"], mode=row["mode"], connections=json.loads(row["connections_json"]),
            structural_warnings=structural_warnings,
            safety_status=safety_status,
            safety_issues=[{"code": item.code, "severity": item.severity, "message": item.message} for item in structural_warnings],
            created_at=_time(row["created_at"]),
            updated_at=_time(row["updated_at"]), latest_snapshot_id=row["latest_snapshot_id"],
        )

    def get(self, problem_id: str, workspace_id: str, *, safety_status="safe", safety_issues=()):
        draft = self.get_capture(problem_id, workspace_id)
        if draft is None:
            return None
        try:
            connections = [WiringConnection.model_validate(item.model_dump(by_alias=True)) for item in draft.connections]
        except ValueError:
            return None
        return PracticeWiringDraftResponse(
            problem_id=problem_id, workspace_id=workspace_id, problem_version=draft.problem_version,
            mode=draft.mode, connections=connections, updated_at=draft.updated_at,
            safety_status=safety_status, safety_issues=list(safety_issues),
        )

    def list_workspaces(self, problem_id: str) -> list[WiringWorkspaceSummary]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM practice_wiring_drafts WHERE problem_id=? ORDER BY updated_at DESC",
                (problem_id,),
            ).fetchall()
        return [WiringWorkspaceSummary(
            problem_id=problem_id, problem_version=row["problem_version"], workspace_id=row["workspace_id"],
            workspace_name=row["workspace_name"], created_at=_time(row["created_at"]), updated_at=_time(row["updated_at"]),
            connection_count=len(json.loads(row["connections_json"])), latest_snapshot_id=row["latest_snapshot_id"],
        ) for row in rows]

    def create_workspace(self, problem_id: str, problem_version: int, workspace_name: str):
        workspace_id = f"qws_{token_urlsafe(12)}"
        return self.save_capture(problem_id, workspace_id, WiringCaptureUpdate(
            problem_version=problem_version, workspace_name=workspace_name, connections=[]
        ))

    def create_snapshot(self, problem_id: str, workspace_id: str, label: str | None = None):
        draft = self.get_capture(problem_id, workspace_id)
        if draft is None:
            return None
        snapshot_id = f"qsn_{token_urlsafe(12)}"
        connections = json.dumps([item.model_dump(by_alias=True, mode="json") for item in draft.connections], ensure_ascii=False)
        warnings = json.dumps([item.model_dump(mode="json") for item in draft.structural_warnings], ensure_ascii=False)
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO practice_wiring_snapshots(
                       snapshot_id, problem_id, workspace_id, problem_version, label, connections_json, warnings_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (snapshot_id, problem_id, workspace_id, draft.problem_version, label, connections, warnings),
            )
            connection.execute(
                "UPDATE practice_wiring_drafts SET latest_snapshot_id=? WHERE problem_id=? AND workspace_id=?",
                (snapshot_id, problem_id, workspace_id),
            )
        return self.get_snapshot(problem_id, workspace_id, snapshot_id)

    def get_snapshot(self, problem_id: str, workspace_id: str, snapshot_id: str):
        with self.database.connect() as connection:
            row = connection.execute(
                """SELECT * FROM practice_wiring_snapshots
                   WHERE problem_id=? AND workspace_id=? AND snapshot_id=?""",
                (problem_id, workspace_id, snapshot_id),
            ).fetchone()
        if row is None:
            return None
        return WiringSnapshotResponse(
            snapshot_id=row["snapshot_id"], problem_id=problem_id, workspace_id=workspace_id,
            problem_version=row["problem_version"], label=row["label"], created_at=_time(row["created_at"]),
            connections=json.loads(row["connections_json"]), structural_warnings=json.loads(row["warnings_json"]),
        )

    def list_snapshots(self, problem_id: str, workspace_id: str):
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT snapshot_id FROM practice_wiring_snapshots
                   WHERE problem_id=? AND workspace_id=? ORDER BY created_at DESC, snapshot_id DESC""",
                (problem_id, workspace_id),
            ).fetchall()
        return [self.get_snapshot(problem_id, workspace_id, row["snapshot_id"]) for row in rows]

    def clone_snapshot(self, problem_id: str, workspace_id: str, snapshot_id: str, workspace_name: str | None = None):
        snapshot = self.get_snapshot(problem_id, workspace_id, snapshot_id)
        if snapshot is None:
            return None
        return self.save_capture(problem_id, f"qws_{token_urlsafe(12)}", WiringCaptureUpdate(
            problem_version=snapshot.problem_version,
            workspace_name=workspace_name or f"스냅샷 복원 {snapshot.created_at:%m-%d %H:%M}",
            connections=snapshot.connections,
        ), snapshot.structural_warnings)

    def delete(self, problem_id: str, workspace_id: str):
        with self.database.connect() as connection:
            connection.execute("DELETE FROM practice_wiring_snapshots WHERE problem_id=? AND workspace_id=?", (problem_id, workspace_id))
            connection.execute("DELETE FROM practice_wiring_drafts WHERE problem_id=? AND workspace_id=?", (problem_id, workspace_id))
