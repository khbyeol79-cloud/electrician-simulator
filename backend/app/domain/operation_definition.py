from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TerminalPair(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_terminal: str = Field(alias="from", min_length=1, max_length=80)
    to: str = Field(min_length=1, max_length=80)


class OperationPower(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_terminal_id: str
    return_terminal_id: str
    phase_terminal_ids: list[str] = Field(default_factory=list, max_length=3)


class OperationControl(BaseModel):
    model_config = ConfigDict(extra="forbid")

    control_id: str
    label: str
    control_type: Literal["pushbutton", "limit_switch", "selector"]
    mode: Literal["momentary", "maintained"]
    contact_type: Literal["NO", "NC"]
    terminal_a_id: str
    terminal_b_id: str
    initial_active: bool = False


class OperationTimer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timer_id: str
    label: str
    coil_id: str
    mode: Literal["on_delay"] = "on_delay"
    delay_ms: int = Field(gt=0, le=3_600_000)
    timed_contact_ids: list[str] = Field(min_length=1)
    retentive: bool = False


class OperationIndicator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indicator_id: str
    label: str
    display_color: Literal["red", "green", "yellow", "white"]
    terminal_a_id: str
    terminal_b_id: str


class OperationMotor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motor_id: str
    label: str
    forward_coil_id: str | None = None
    reverse_coil_id: str | None = None
    phase_terminal_ids: list[str] = Field(default_factory=list, max_length=3)
    phase_source_terminal_ids: list[str] = Field(default_factory=list, max_length=3)
    forward_phase_order: list[int] = Field(default_factory=lambda: [0, 1, 2], min_length=3, max_length=3)


class OperationContactor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contactor_id: str
    label: str
    coil_id: str
    role: Literal["forward", "reverse", "general"] = "general"
    start_control_id: str | None = None
    motor_id: str | None = None


class OperationInterlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interlock_id: str
    label: str
    type: Literal["electrical", "mechanical"]
    contactor_ids: list[str] = Field(min_length=2, max_length=2)
    contact_ids: list[str] = Field(default_factory=list, max_length=10)
    policy: Literal["prevent_simultaneous_activation"] = "prevent_simultaneous_activation"


class OperationProtectionDevice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protection_device_id: str
    label: str
    protection_type: Literal["eocr"] = "eocr"
    protected_coil_ids: list[str] = Field(default_factory=list, max_length=20)
    protected_motor_ids: list[str] = Field(default_factory=list, max_length=10)
    protection_contact_ids: list[str] = Field(default_factory=list, max_length=20)
    reset_mode: Literal["manual", "automatic", "restart_required"] = "manual"
    allowed_fault_types: list[Literal["overload"]] = Field(default_factory=lambda: ["overload"], min_length=1)


class OperationDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    simulation_status: Literal["preview", "functional"] = "preview"
    simulation_mode: Literal["legacy_assisted", "actual_wiring"] = "legacy_assisted"
    power: OperationPower
    controls: list[OperationControl] = Field(default_factory=list, max_length=50)
    timers: list[OperationTimer] = Field(default_factory=list, max_length=20)
    indicators: list[OperationIndicator] = Field(default_factory=list, max_length=30)
    motors: list[OperationMotor] = Field(default_factory=list, max_length=10)
    contactors: list[OperationContactor] = Field(default_factory=list, max_length=30)
    interlocks: list[OperationInterlock] = Field(default_factory=list, max_length=30)
    protection_devices: list[OperationProtectionDevice] = Field(default_factory=list, max_length=20)
    direction_change_policy: Literal[
        "current_direction_first", "first_input_first", "block_both", "stop_before_reverse"
    ] = "block_both"
    internal_connections: list[TerminalPair] = Field(default_factory=list, max_length=500)


class OperationAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "set_power", "press_control", "release_control", "toggle_control", "advance_time",
        "trigger_fault", "reset_fault", "reset_operation",
    ]
    value: bool | None = None
    control_id: str | None = None
    milliseconds: int | None = Field(default=None, ge=0, le=60_000)
    target_id: str | None = None
    fault_type: Literal["overload"] | None = None

    @model_validator(mode="after")
    def validate_payload(self):
        if self.action == "set_power" and self.value is None:
            raise ValueError("전원 상태 값이 필요합니다.")
        if self.action in {"press_control", "release_control", "toggle_control"} and not self.control_id:
            raise ValueError("조작할 입력기구 ID가 필요합니다.")
        if self.action == "advance_time" and self.milliseconds is None:
            raise ValueError("진행할 시간이 필요합니다.")
        if self.action in {"trigger_fault", "reset_fault"} and not self.target_id:
            raise ValueError("보호장치 ID가 필요합니다.")
        if self.action == "trigger_fault" and self.fault_type is None:
            raise ValueError("고장 종류가 필요합니다.")
        return self


class OperationSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_version: int = Field(ge=1)
    wiring_attempt_id: int | None = Field(default=None, ge=1)


class OperationFault(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    severity: Literal["warning", "error", "danger"]
    trip_required: bool = False


class TimerState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["stopped", "timing", "completed", "reset"]
    elapsed_ms: int
    delay_ms: int


class ControlState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    control_type: str
    mode: str
    contact_type: str
    active: bool


class ProtectionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    protection_type: str
    status: Literal["normal", "tripped", "reset_required"]
    reset_mode: str


class InterlockState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    type: Literal["electrical", "mechanical"]
    status: Literal["ready", "blocking", "fault"]
    blocked_contactor_id: str | None = None


class OperationSessionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    problem_id: str
    wiring_attempt_id: int
    simulation_mode: Literal["legacy_assisted", "actual_wiring"] = "legacy_assisted"
    catalog_composed: bool = False
    powered: bool
    power_state: Literal["off", "on", "tripped"]
    controls: dict[str, ControlState]
    coils: dict[str, bool]
    contacts: dict[str, Literal["open", "closed"]]
    timers: dict[str, TimerState]
    indicators: dict[str, Literal["off", "on", "error"]]
    motors: dict[str, Literal[
        "stopped", "forward", "reverse", "phase_loss", "phase_sequence_error",
        "simultaneous_fault", "connection_error", "power_off", "protection_trip", "undetermined",
    ]]
    protections: dict[str, ProtectionState]
    interlocks: dict[str, InterlockState]
    active_faults: list[str]
    faults: list[OperationFault]
    stable: bool
    elapsed_ms: int
    events: list[str]


class OperationCheckItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_id: str
    label: str
    passed: bool
    message: str


class OperationCheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gradable: bool
    overall_passed: bool | None
    passed_count: int
    total_count: int
    results: list[OperationCheckItem]
    message: str


class OperationProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_id: str
    attempt_count: int = 0
    last_submitted_at: str | None = None
    last_overall_passed: bool | None = None
    last_gradable: bool | None = None
    last_passed_count: int = 0
    total_count: int = 0
    manual_run_count: int = 0
    last_run_at: str | None = None
    forward_seen: bool = False
    reverse_seen: bool = False
    interlock_seen: bool = False
    protection_trip_seen: bool = False
