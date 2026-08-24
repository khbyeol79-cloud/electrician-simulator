from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .mounting_attempt import MountingDefinition
from .operation_setup import DeviceLayoutDefinition
from .operation_definition import OperationDefinition


class WireColors(BaseModel):
    model_config = ConfigDict(extra="forbid")

    L1: Literal["brown"]
    L2: Literal["black"]
    L3: Literal["gray"]
    control: Literal["yellow"]


class PowerSupply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system: str = Field(min_length=1, max_length=60)
    voltage: float = Field(gt=0, le=1000)
    frequency: float = Field(gt=0, le=1000)
    wire_colors: WireColors


class SchematicReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: str
    format: Literal["svg"]
    view_box: str


class BoardReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout_id: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


class BoardPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row: int = Field(ge=0)
    column: int = Field(ge=0)
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class CircuitDevice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1, max_length=80)
    device_type_id: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
    label: str = Field(min_length=1, max_length=80)
    socket_type_id: str | None = None
    behavior_model_id: str | None = Field(
        default=None,
        pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$",
    )
    board_position: BoardPosition
    installed_initially: bool = False


TerminalType = Literal[
    "socket_pin", "screw_terminal", "coil_terminal", "contact_terminal",
    "power_terminal", "ground_terminal", "external_terminal",
]
ElectricalRole = Literal[
    "unassigned", "line", "neutral", "protective_earth", "control", "coil",
    "contact_common", "contact_no", "contact_nc", "load",
]


class CircuitTerminal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    terminal_id: str = Field(min_length=1, max_length=80)
    device_id: str = Field(min_length=1, max_length=80)
    pin_number: int | None = Field(default=None, ge=1)
    terminal_type: TerminalType
    electrical_role: ElectricalRole
    max_connections: int = Field(ge=1, le=20)
    enabled: bool = True


class CircuitContact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_id: str = Field(min_length=1, max_length=80)
    owner_device_id: str = Field(min_length=1, max_length=80)
    contact_type: Literal["NO", "NC", "CHANGEOVER"]
    common_terminal_id: str
    switched_terminal_id: str
    nc_terminal_id: str | None = None
    no_terminal_id: str | None = None
    controller_type: Literal["coil", "timer", "protection"] = "coil"
    controller_id: str | None = None
    controlled_by_coil_id: str | None = None
    normal_state: Literal["open", "closed"]

    @model_validator(mode="after")
    def normalize_controller(self):
        if self.controller_type == "coil":
            controller_id = self.controller_id or self.controlled_by_coil_id
            if not controller_id:
                raise ValueError("코일 접점에는 제어 코일 ID가 필요합니다.")
            if (
                self.controller_id
                and self.controlled_by_coil_id
                and self.controller_id != self.controlled_by_coil_id
            ):
                raise ValueError("접점의 controller_id와 제어 코일 ID가 일치하지 않습니다.")
            self.controller_id = controller_id
            self.controlled_by_coil_id = controller_id
        elif not self.controller_id:
            raise ValueError("타이머·보호 접점에는 controller_id가 필요합니다.")
        return self


class CircuitCoil(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coil_id: str = Field(min_length=1, max_length=80)
    owner_device_id: str = Field(min_length=1, max_length=80)
    terminal_a_id: str
    terminal_b_id: str
    rated_voltage: float = Field(gt=0, le=1000)
    voltage_type: Literal["AC", "DC"]
    frequency: float | None = Field(default=None, gt=0, le=1000)


class CircuitDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    definition_status: Literal["structure_only", "functional"] = "structure_only"
    devices: list[CircuitDevice] = Field(default_factory=list)
    terminals: list[CircuitTerminal] = Field(default_factory=list)
    contacts: list[CircuitContact] = Field(default_factory=list)
    coils: list[CircuitCoil] = Field(default_factory=list)


class AnswerSlot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot_id: str = Field(min_length=1, max_length=40)
    position: Literal["above", "below", "left", "right"]


class SocketQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1, max_length=80)
    target_element_type: Literal["contact", "coil"]
    target_element_id: str = Field(min_length=1, max_length=80)
    display_label: str = Field(min_length=1, max_length=80)
    answer_slots: list[AnswerSlot] = Field(min_length=1, max_length=4)


class ExternalWiringTerminal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    terminal_id: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=80)
    terminal_role: Literal["external"] = "external"
    operation_terminal_id: str | None = Field(default=None, max_length=80)
    max_connections: Literal[1, 2] = 1
    wire_color: Literal["brown", "black", "gray", "yellow"] = "yellow"


class ExternalWiringDevice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=120)
    placement: Literal["top", "bottom"] = "top"
    contact_type: Literal["NO", "NC"] | None = None
    terminals: list[ExternalWiringTerminal] = Field(min_length=1, max_length=20)


class WiringSemantics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    extra_jumper_policy: Literal["ignore", "warning", "reject"] = "warning"
    external_devices: list[ExternalWiringDevice] = Field(default_factory=list, max_length=50)


class ProblemDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    problem_id: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
    description: str = Field(min_length=1, max_length=2000)
    instructions: list[str] = Field(min_length=1, max_length=30)
    learning_objectives: list[str] = Field(default_factory=list, max_length=30)
    power_supply: PowerSupply
    schematic: SchematicReference
    board: BoardReference
    available_devices: list[dict[str, Any]] = Field(default_factory=list)
    circuit: CircuitDefinition
    socket_questions: list[SocketQuestion] = Field(default_factory=list)
    device_layout: DeviceLayoutDefinition | None = None
    mounting: MountingDefinition | None = None
    operation: OperationDefinition | None = None
    wiring_semantics: WiringSemantics | None = None
