from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .board_definition import BoardDefinition
from .operation_definition import OperationDefinition
from .operation_setup import DeviceLayoutDefinition
from .problem_definition import CircuitDefinition
from .problem_definition import WiringSemantics
from .wiring_attempt import WiringConnection


class FreeCircuitDevicePlacement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zone: Literal["internal_upper", "internal_lower", "external_top", "external_bottom"]
    row: int = Field(default=0, ge=0, le=3)
    column: int = Field(ge=0, le=19)


class FreeCircuitInstalledDevice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instance_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,40}$")
    palette_id: str = Field(min_length=1, max_length=80)
    model_id: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=80)
    placement: FreeCircuitDevicePlacement
    properties: dict[str, str | int | float | bool] = Field(default_factory=dict)


class FreeCircuitAssembly(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    mode: Literal["editable", "fixed"] = "editable"
    installed_devices: list[FreeCircuitInstalledDevice] = Field(default_factory=list, max_length=50)


class FreeCircuitMountingSlot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot_id: str
    zone: Literal["internal_upper", "internal_lower", "external_top", "external_bottom"]
    row: int = 0
    column: int
    x: float
    y: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class FreeCircuitPaletteItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    palette_id: str
    model_id: str
    device_type_id: str
    name: str
    category: str
    mounting_kind: Literal["internal", "external"]
    default_zone: Literal["internal_upper", "internal_lower", "external_top", "external_bottom"]
    socket_type_id: str | None = None
    definition_status: str
    capabilities: list[str] = Field(default_factory=list)
    default_properties: dict[str, str | int | float | bool] = Field(default_factory=dict)
    max_instances: int | None = Field(default=None, ge=1)
    enabled: bool = True
    disabled_reason: str | None = None


class FreeCircuitPaletteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[FreeCircuitPaletteItem]
    slots: list[FreeCircuitMountingSlot]


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
    assembly: FreeCircuitAssembly | None = None
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
    assembly: FreeCircuitAssembly | None = None
