from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .wiring_attempt import PracticeSafetyIssue


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
    alternate_terminal_a_id: str | None = None
    alternate_terminal_b_id: str | None = None
    initial_active: bool = False

    @model_validator(mode="after")
    def validate_selector_pairs(self):
        alternate = (self.alternate_terminal_a_id, self.alternate_terminal_b_id)
        if any(alternate) and not all(alternate):
            raise ValueError("셀렉터의 대체 접점 단자는 두 개가 모두 필요합니다.")
        if any(alternate) and self.control_type != "selector":
            raise ValueError("대체 접점 단자는 셀렉터에만 사용할 수 있습니다.")
        return self


class OperationTimer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timer_id: str
    label: str
    coil_id: str
    mode: Literal["on_delay"] = "on_delay"
    delay_ms: int = Field(gt=0, le=3_600_000)
    timed_contact_ids: list[str] = Field(min_length=1)
    retentive: bool = False


class OperationFlasher(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flasher_id: str
    label: str
    coil_id: str
    interval_ms: int = Field(gt=0, le=3_600_000)
    contact_ids: list[str] = Field(min_length=1, max_length=20)


class OperationLevelRelay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level_relay_id: str
    label: str
    supply_terminal_a_id: str
    supply_terminal_b_id: str
    electrode_terminal_ids: list[str] = Field(min_length=3, max_length=3)
    external_electrode_terminal_ids: list[str] = Field(min_length=3, max_length=3)
    contact_ids: list[str] = Field(min_length=1, max_length=20)


class OperationAudibleOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output_id: str
    label: str
    terminal_a_id: str
    terminal_b_id: str


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
    supply_terminal_a_id: str | None = None
    supply_terminal_b_id: str | None = None
    reset_mode: Literal["manual", "automatic", "restart_required"] = "manual"
    allowed_fault_types: list[Literal["overload"]] = Field(default_factory=lambda: ["overload"], min_length=1)


class OperationFuseChannel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel_id: str
    label: str
    terminal_a_id: str
    terminal_b_id: str


class OperationDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    simulation_status: Literal["preview", "functional"] = "preview"
    simulation_mode: Literal["legacy_assisted", "actual_wiring"] = "legacy_assisted"
    power: OperationPower
    controls: list[OperationControl] = Field(default_factory=list, max_length=50)
    timers: list[OperationTimer] = Field(default_factory=list, max_length=20)
    flashers: list[OperationFlasher] = Field(default_factory=list, max_length=20)
    level_relays: list[OperationLevelRelay] = Field(default_factory=list, max_length=20)
    indicators: list[OperationIndicator] = Field(default_factory=list, max_length=30)
    audible_outputs: list[OperationAudibleOutput] = Field(default_factory=list, max_length=20)
    motors: list[OperationMotor] = Field(default_factory=list, max_length=10)
    contactors: list[OperationContactor] = Field(default_factory=list, max_length=30)
    interlocks: list[OperationInterlock] = Field(default_factory=list, max_length=30)
    protection_devices: list[OperationProtectionDevice] = Field(default_factory=list, max_length=20)
    fuse_channels: list[OperationFuseChannel] = Field(default_factory=list, max_length=40)
    requirements: list["OperationRequirement"] = Field(default_factory=list, max_length=100)
    direction_change_policy: Literal[
        "current_direction_first", "first_input_first", "block_both", "stop_before_reverse"
    ] = "block_both"
    internal_connections: list[TerminalPair] = Field(default_factory=list, max_length=500)


class OperationAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "set_power", "press_control", "release_control", "toggle_control", "advance_time",
        "trigger_fault", "reset_fault", "set_fuse_state", "set_level", "reset_operation",
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
        if self.action == "set_fuse_state" and (not self.target_id or self.value is None):
            raise ValueError("FUSE 채널과 정상 여부가 필요합니다.")
        if self.action == "set_level" and (not self.target_id or self.value is None):
            raise ValueError("수위계전기와 감지 상태가 필요합니다.")
        if self.action == "trigger_fault" and self.fault_type is None:
            raise ValueError("고장 종류가 필요합니다.")
        return self


class OperationExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(pattern=r"^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*$", max_length=160)
    expected: bool | int | str


class OperationRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(pattern=r"^[A-Z0-9_]+$", max_length=80)
    label: str = Field(min_length=1, max_length=240)
    scenario_id: str | None = Field(default=None, pattern=r"^[A-Z0-9_]+$", max_length=80)
    scenario_label: str | None = Field(default=None, min_length=1, max_length=120)
    next_action: str | None = Field(default=None, min_length=1, max_length=240)
    actions: list[OperationAction] = Field(default_factory=list, max_length=30)
    observations: list[OperationExpectation] = Field(default_factory=list, max_length=20)
    expectations: list[OperationExpectation] = Field(min_length=1, max_length=20)


class OperationSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_version: int = Field(ge=1)
    wiring_attempt_id: int | None = Field(default=None, ge=1)


class PracticeOperationSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    problem_version: int = Field(ge=1)
    workspace_id: str = Field(default="main", min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")


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


class FlasherState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    status: Literal["stopped", "on", "off"]
    elapsed_ms: int
    interval_ms: int


class LevelRelayState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    requested: bool
    powered: bool
    wiring_ready: bool
    detected: bool


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
    powered: bool = False
    operating_state: Literal["unpowered", "powered_normal", "tripped"] = "unpowered"


class FuseChannelState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    status: Literal["normal", "open"]
    terminal_a_id: str
    terminal_b_id: str


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
    session_type: Literal["verified_operation_session", "practice_preview_session", "free_circuit_session"] = "verified_operation_session"
    wiring_snapshot_id: int | None = None
    workspace_id: str | None = None
    gradable: bool = True
    safety_status: Literal["not_checked", "safe", "attention", "blocked"] = "not_checked"
    power_permitted: bool = True
    safety_issues: list["PracticeSafetyIssue"] = Field(default_factory=list)
    simulation_mode: Literal["legacy_assisted", "actual_wiring"] = "legacy_assisted"
    catalog_composed: bool = False
    powered: bool
    power_state: Literal["off", "on", "tripped"]
    controls: dict[str, ControlState]
    coils: dict[str, bool]
    contacts: dict[str, Literal["open", "closed"]]
    changeover_positions: dict[str, Literal["nc", "no"]] = Field(default_factory=dict)
    timers: dict[str, TimerState]
    flashers: dict[str, FlasherState] = Field(default_factory=dict)
    level_relays: dict[str, LevelRelayState] = Field(default_factory=dict)
    indicators: dict[str, Literal["off", "on", "error"]]
    audible_outputs: dict[str, Literal["off", "on", "error"]] = Field(default_factory=dict)
    motors: dict[str, Literal[
        "stopped", "forward", "reverse", "phase_loss", "phase_sequence_error",
        "simultaneous_fault", "connection_error", "power_off", "protection_trip", "undetermined",
    ]]
    protections: dict[str, ProtectionState]
    fuses: dict[str, FuseChannelState] = Field(default_factory=dict)
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


class BehaviorRequirementItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_id: str
    label: str
    status: Literal["not_run", "satisfied", "unsatisfied", "unavailable"]
    message: str


class BehaviorRequirementSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_id: str
    label: str
    scenario_id: str | None = None
    scenario_label: str | None = None
    next_action: str | None = None


class BehaviorScenarioItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    label: str
    status: Literal["not_run", "satisfied", "unsatisfied", "unavailable"]
    current_observation: str
    missing_conditions: list[str] = Field(default_factory=list, max_length=100)
    next_action: str


class BehaviorRequirementResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gradable: Literal[False] = False
    results: list[BehaviorRequirementItem]
    scenarios: list[BehaviorScenarioItem] = Field(default_factory=list)
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
