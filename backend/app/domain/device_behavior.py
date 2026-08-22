from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .operation_definition import (
    OperationContactor,
    OperationControl,
    OperationIndicator,
    OperationTimer,
    TerminalPair,
)
from .problem_definition import (
    BoardPosition,
    CircuitCoil,
    CircuitContact,
    CircuitDevice,
    CircuitTerminal,
    ElectricalRole,
    TerminalType,
)


DefinitionStatus = Literal["unverified", "reviewed", "verified"]
DeviceCapability = Literal[
    "terminal_block",
    "switching",
    "overcurrent_isolation",
    "power_source",
    "manual_control",
    "limit_control",
    "coil",
    "relay_contacts",
    "timed_contacts",
    "contactor",
    "overload_protection",
    "indicator",
    "three_phase_load",
    "socket",
]
ContactActuation = Literal["coil", "timer", "manual", "protection"]
SettingValue = bool | int | float | str


class BehaviorTerminal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    terminal_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=50)
    terminal_suffix: str = Field(pattern=r"^[A-Za-z0-9]+$", max_length=20)
    pin_number: int | None = Field(default=None, ge=1, le=100)
    terminal_type: TerminalType
    electrical_role: ElectricalRole
    max_connections: int = Field(ge=1, le=20)
    enabled: bool = True


class BehaviorCoil(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coil_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=50)
    id_suffix: str = Field(pattern=r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$", max_length=30)
    terminal_a_key: str
    terminal_b_key: str
    rated_voltage_property_key: str
    voltage_type_property_key: str
    frequency_property_key: str | None = None


class BehaviorContact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=50)
    id_suffix: str = Field(pattern=r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$", max_length=30)
    contact_type: Literal["NO", "NC", "CHANGEOVER"]
    common_terminal_key: str
    switched_terminal_key: str
    nc_terminal_key: str | None = None
    no_terminal_key: str | None = None
    actuation: ContactActuation
    controlled_by_key: str
    normal_state: Literal["open", "closed"]


class BehaviorIntrinsicConnection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_terminal_key: str
    to_terminal_key: str


class BehaviorConfigurableProperty(BaseModel):
    model_config = ConfigDict(extra="forbid")

    property_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=50)
    value_type: Literal["boolean", "integer", "number", "string", "color", "voltage_type"]
    required: bool = False
    default: SettingValue | None = None
    minimum: float | None = None
    maximum: float | None = None
    choices: list[SettingValue] = Field(default_factory=list, max_length=30)


class BehaviorControl(BaseModel):
    model_config = ConfigDict(extra="forbid")

    control_type: Literal["pushbutton", "limit_switch", "selector"]
    mode: Literal["momentary", "maintained"]
    contact_key: str
    initial_active: bool = False


class BehaviorTimer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timer_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=50)
    id_suffix: str = Field(pattern=r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$", max_length=30)
    coil_key: str
    mode: Literal["on_delay"] = "on_delay"
    delay_property_key: str
    timed_contact_keys: list[str] = Field(min_length=1, max_length=20)
    retentive: bool = False


class BehaviorIndicator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    terminal_a_key: str
    terminal_b_key: str
    display_color_property_key: str


class BehaviorMotor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase_terminal_keys: list[str] = Field(min_length=3, max_length=3)


class BehaviorProtection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protection_type: Literal["eocr"] = "eocr"
    reset_modes: list[Literal["manual", "automatic", "restart_required"]] = Field(
        min_length=1, max_length=3
    )
    default_reset_mode: Literal["manual", "automatic", "restart_required"]
    allowed_fault_types: list[Literal["overload"]] = Field(min_length=1, max_length=3)
    contact_keys: list[str] = Field(default_factory=list, max_length=20)


class DeviceBehaviorModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
    device_type_id: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=120)
    definition_status: DefinitionStatus
    source_note: str = Field(min_length=1, max_length=1000)
    compatible_socket_type_ids: list[str] = Field(default_factory=list, max_length=10)
    capabilities: list[DeviceCapability] = Field(min_length=1, max_length=20)
    terminals: list[BehaviorTerminal] = Field(min_length=1, max_length=100)
    coils: list[BehaviorCoil] = Field(default_factory=list, max_length=20)
    contacts: list[BehaviorContact] = Field(default_factory=list, max_length=50)
    intrinsic_connections: list[BehaviorIntrinsicConnection] = Field(
        default_factory=list, max_length=100
    )
    configurable_properties: list[BehaviorConfigurableProperty] = Field(
        default_factory=list, max_length=30
    )
    control: BehaviorControl | None = None
    timer: BehaviorTimer | None = None
    indicator: BehaviorIndicator | None = None
    motor: BehaviorMotor | None = None
    protection: BehaviorProtection | None = None


class DeviceBehaviorCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    models: list[DeviceBehaviorModel]


class DeviceInstanceDefinition(BaseModel):
    """카탈로그 한 모델을 회로에 배치했을 때 생성되는 독립 fragment."""

    model_config = ConfigDict(extra="forbid")

    model_id: str
    instance_id: str
    device: CircuitDevice
    terminals: list[CircuitTerminal]
    coils: list[CircuitCoil]
    contacts: list[CircuitContact]
    controls: list[OperationControl] = Field(default_factory=list)
    timers: list[OperationTimer] = Field(default_factory=list)
    indicators: list[OperationIndicator] = Field(default_factory=list)
    contactors: list[OperationContactor] = Field(default_factory=list)
    intrinsic_connections: list[TerminalPair] = Field(default_factory=list)
    terminal_ids: dict[str, str]
    coil_ids: dict[str, str]
    contact_ids: dict[str, str]
    settings: dict[str, SettingValue]
    deferred_operation_capabilities: list[str] = Field(default_factory=list)


class DeviceInstanceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str
    instance_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,39}$")
    label: str = Field(min_length=1, max_length=80)
    board_position: BoardPosition
    settings: dict[str, Any] = Field(default_factory=dict)
    socket_type_id: str | None = None
    installed_initially: bool = False
