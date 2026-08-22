from __future__ import annotations

import json
from datetime import datetime

from app.database import SQLiteDatabase
from app.domain.free_circuit import (
    FreeCircuitWorkspaceResponse,
    FreeCircuitWorkspaceSummary,
    FreeCircuitWorkspaceUpdate,
)


class FreeCircuitRepository:
    def __init__(self, database: SQLiteDatabase):
        self.database = database

    def save(self, workspace_id: str, workspace: FreeCircuitWorkspaceUpdate) -> FreeCircuitWorkspaceResponse:
        payload = workspace.model_dump(by_alias=True, mode="json")
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO free_circuit_workspaces(
                       workspace_id, name, circuit_json, operation_json, connections_json,
                       board_json, device_layout_json, wiring_semantics_json, editor_json,
                       assembly_json, schema_version, updated_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(workspace_id) DO UPDATE SET
                       name=excluded.name,
                       circuit_json=excluded.circuit_json,
                       operation_json=excluded.operation_json,
                       connections_json=excluded.connections_json,
                       board_json=excluded.board_json,
                       device_layout_json=excluded.device_layout_json,
                       wiring_semantics_json=excluded.wiring_semantics_json,
                       editor_json=excluded.editor_json,
                       assembly_json=excluded.assembly_json,
                       schema_version=excluded.schema_version,
                       updated_at=CURRENT_TIMESTAMP""",
                (
                    workspace_id,
                    workspace.name,
                    json.dumps(payload["circuit"], ensure_ascii=False),
                    json.dumps(payload["operation"], ensure_ascii=False),
                    json.dumps(payload["connections"], ensure_ascii=False),
                    json.dumps(payload["board"], ensure_ascii=False) if payload["board"] else None,
                    json.dumps(payload["device_layout"], ensure_ascii=False) if payload["device_layout"] else None,
                    json.dumps(payload["wiring_semantics"], ensure_ascii=False) if payload["wiring_semantics"] else None,
                    json.dumps(payload["editor"], ensure_ascii=False),
                    json.dumps(payload["assembly"], ensure_ascii=False) if payload["assembly"] else None,
                    payload["schema_version"],
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
            schema_version=row["schema_version"] if "schema_version" in row.keys() else "1.0",
            circuit=json.loads(row["circuit_json"]),
            operation=json.loads(row["operation_json"]),
            connections=json.loads(row["connections_json"]),
            board=json.loads(row["board_json"]) if "board_json" in row.keys() and row["board_json"] else None,
            device_layout=json.loads(row["device_layout_json"]) if "device_layout_json" in row.keys() and row["device_layout_json"] else None,
            wiring_semantics=json.loads(row["wiring_semantics_json"]) if "wiring_semantics_json" in row.keys() and row["wiring_semantics_json"] else None,
            editor=json.loads(row["editor_json"]) if "editor_json" in row.keys() and row["editor_json"] else {},
            assembly=json.loads(row["assembly_json"]) if "assembly_json" in row.keys() and row["assembly_json"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def list(self) -> list[FreeCircuitWorkspaceSummary]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT workspace_id, name, connections_json, editor_json, schema_version, updated_at "
                "FROM free_circuit_workspaces ORDER BY updated_at DESC, workspace_id"
            ).fetchall()
        summaries: list[FreeCircuitWorkspaceSummary] = []
        for row in rows:
            editor = json.loads(row["editor_json"]) if row["editor_json"] else {}
            summaries.append(FreeCircuitWorkspaceSummary(
                workspace_id=row["workspace_id"],
                name=row["name"],
                schema_version=row["schema_version"] or "1.0",
                template_id=editor.get("template_id"),
                connection_count=len(json.loads(row["connections_json"])),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            ))
        return summaries

    def delete(self, workspace_id: str) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "DELETE FROM free_circuit_workspaces WHERE workspace_id = ?", (workspace_id,)
            )
