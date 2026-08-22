from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .board_definition import BoardDefinition
from .operation_definition import OperationDefinition
from .operation_setup import DeviceLayoutDefinition
from .problem_definition import CircuitDefinition
from .problem_definition import WiringSemantics
from .wiring_attempt import WiringConnection


class FreeCircuitEditorState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="1.0", pattern=r"^1\.0$")
    mode: str = Field(default="graphic", pattern=r"^(graphic|summary)$")
    template_id: str | None = Field(default=None, max_length=80)


class FreeCircuitWorkspaceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="1.0", pattern=r"^1\.0$")
    name: str = Field(min_length=1, max_length=120)
    circuit: CircuitDefinition
    operation: OperationDefinition
    connections: list[WiringConnection] = Field(default_factory=list, max_length=500)
    board: BoardDefinition | None = None
    device_layout: DeviceLayoutDefinition | None = None
    wiring_semantics: WiringSemantics | None = None
    editor: FreeCircuitEditorState = Field(default_factory=FreeCircuitEditorState)


class FreeCircuitWorkspaceResponse(FreeCircuitWorkspaceUpdate):
    workspace_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    updated_at: datetime | None = None


class FreeCircuitWorkspaceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    name: str
    schema_version: str = "1.0"
    template_id: str | None = None
    connection_count: int = 0
    updated_at: datetime | None = None


class FreeCircuitTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: str
    name: str
    description: str
    board: BoardDefinition
    circuit: CircuitDefinition
    operation: OperationDefinition
    device_layout: DeviceLayoutDefinition | None = None
    wiring_semantics: WiringSemantics | None = None
