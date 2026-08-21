from __future__ import annotations

import json
from datetime import datetime

from app.database import SQLiteDatabase
from app.domain.free_circuit import FreeCircuitWorkspaceResponse, FreeCircuitWorkspaceUpdate


class FreeCircuitRepository:
    def __init__(self, database: SQLiteDatabase):
        self.database = database

    def save(self, workspace_id: str, workspace: FreeCircuitWorkspaceUpdate) -> FreeCircuitWorkspaceResponse:
        payload = workspace.model_dump(by_alias=True, mode="json")
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO free_circuit_workspaces(
                       workspace_id, name, circuit_json, operation_json, connections_json, updated_at
                   ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(workspace_id) DO UPDATE SET
                       name=excluded.name,
                       circuit_json=excluded.circuit_json,
                       operation_json=excluded.operation_json,
                       connections_json=excluded.connections_json,
                       updated_at=CURRENT_TIMESTAMP""",
                (
                    workspace_id,
                    workspace.name,
                    json.dumps(payload["circuit"], ensure_ascii=False),
                    json.dumps(payload["operation"], ensure_ascii=False),
                    json.dumps(payload["connections"], ensure_ascii=False),
                ),
            )
        return self.get(workspace_id) or FreeCircuitWorkspaceResponse(
            workspace_id=workspace_id, **workspace.model_dump()
        )

    def get(self, workspace_id: str) -> FreeCircuitWorkspaceResponse | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM free_circuit_workspaces WHERE workspace_id = ?", (workspace_id,)
            ).fetchone()
        if row is None:
            return None
        return FreeCircuitWorkspaceResponse(
            workspace_id=workspace_id,
            name=row["name"],
            circuit=json.loads(row["circuit_json"]),
            operation=json.loads(row["operation_json"]),
            connections=json.loads(row["connections_json"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def delete(self, workspace_id: str) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "DELETE FROM free_circuit_workspaces WHERE workspace_id = ?", (workspace_id,)
            )
