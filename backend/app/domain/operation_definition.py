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


class OperationDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    simulation_status: Literal["preview", "functional"] = "preview"
    power: OperationPower
    controls: list[OperationControl] = Field(default_factory=list, max_length=50)
    timers: list[OperationTimer] = Field(default_factory=list, max_length=20)
    indicators: list[OperationIndicator] = Field(default_factory=list, max_length=30)
    motors: list[OperationMotor] = Field(default_factory=list, max_length=10)
    internal_connections: list[TerminalPair] = Field(default_factory=list, max_length=500)


class OperationAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["set_power", "press_control", "release_control", "toggle_control", "advance_time"]
    value: bool | None = None
    control_id: str | None = None
    milliseconds: int | None = Field(default=None, ge=0, le=60_000)

    @model_validator(mode="after")
    def validate_payload(self):
        if self.action == "set_power" and self.value is None:
            raise ValueError("전원 상태 값이 필요합니다.")
        if self.action in {"press_control", "release_control", "toggle_control"} and not self.control_id:
            raise ValueError("조작할 입력기구 ID가 필요합니다.")
        if self.action == "advance_time" and self.milliseconds is None:
            raise ValueError("진행할 시간이 필요합니다.")
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


class OperationSessionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    problem_id: str
    wiring_attempt_id: int
    powered: bool
    power_state: Literal["off", "on", "tripped"]
    controls: dict[str, ControlState]
    coils: dict[str, bool]
    contacts: dict[str, Literal["open", "closed"]]
    timers: dict[str, TimerState]
    indicators: dict[str, Literal["off", "on", "error"]]
    motors: dict[str, Literal["stopped", "forward", "reverse", "phase_loss", "simultaneous_fault", "connection_error"]]
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

