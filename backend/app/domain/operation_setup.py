from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .board_definition import BoardDefinition
from .operation_definition import BehaviorRequirementSummary, OperationDefinition
from .wiring_attempt import WiringConnection, WiringDraftResponse, WiringProgress


class FixedDevicePlacement(BaseModel):
    """문제지에 공개되는 고정 기구 위치다. 채점 정답이 아니다."""

    model_config = ConfigDict(extra="forbid")

    mount_device_id: str = Field(pattern=r"^[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*$")
    label: str = Field(min_length=1, max_length=80)
    device_type_id: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
    graphic_type: Literal["relay", "timer", "contactor"]
    socket_id: str = Field(pattern=r"^[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*$")
    socket_type_id: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


class DeviceLayoutDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    fixed_placements: list[FixedDevicePlacement] = Field(default_factory=list, max_length=100)


class OperationSetupResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_id: str
    problem_version: int
    board: BoardDefinition
    device_layout: DeviceLayoutDefinition | None
    wiring_draft: WiringDraftResponse | None
    wiring_source: Literal["accepted_submission", "draft_preview", "practice_draft", "none"]
    wiring_snapshot: "AcceptedWiringSnapshot | None"
    wiring_submission: WiringProgress
    wiring_exists: bool
    operation_ready: bool
    preview_allowed: bool
    message: str
    operation: OperationDefinition | None
    behavior_requirements: list[BehaviorRequirementSummary] = Field(default_factory=list)


class AcceptedWiringSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_id: int
    problem_version: int
    connections: list[WiringConnection]
