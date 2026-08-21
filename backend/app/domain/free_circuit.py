from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .operation_definition import OperationDefinition
from .problem_definition import CircuitDefinition
from .wiring_attempt import WiringConnection


class FreeCircuitWorkspaceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    circuit: CircuitDefinition
    operation: OperationDefinition
    connections: list[WiringConnection] = Field(default_factory=list, max_length=500)


class FreeCircuitWorkspaceResponse(FreeCircuitWorkspaceUpdate):
    workspace_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    updated_at: datetime | None = None
