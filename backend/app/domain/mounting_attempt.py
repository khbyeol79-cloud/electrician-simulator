from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MountDevice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mount_device_id: str = Field(pattern=r"^[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*$")
    label: str = Field(min_length=1, max_length=80)
    device_type_id: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
    graphic_type: Literal["relay", "timer", "contactor"]
    compatible_socket_type_ids: list[str] = Field(min_length=1, max_length=10)


class MountTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    socket_id: str = Field(pattern=r"^[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*$")
    socket_type_id: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
    enabled: bool = True
    allowed_device_type_ids: list[str] = Field(min_length=1, max_length=20)


class MountingDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    available_devices: list[MountDevice] = Field(default_factory=list, max_length=100)
    mount_targets: list[MountTarget] = Field(default_factory=list, max_length=100)


class MountingAnswerPlacement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mount_device_id: str
    socket_id: str


class MountingPlacement(MountingAnswerPlacement):
    pass


class MountingDraftUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_version: int = Field(ge=1)
    placements: list[MountingPlacement] = Field(default_factory=list, max_length=100)


class MountingDraftResponse(MountingDraftUpdate):
    problem_id: str
    updated_at: datetime | None = None


class MountingAttemptSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_version: int = Field(ge=1)
    placements: list[MountingPlacement] = Field(default_factory=list, max_length=100)


class WrongMountingPlacement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mount_device_id: str
    submitted_socket_id: str


class MountingAttemptResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_id: int | None = None
    gradable: bool
    overall_correct: bool | None
    required_count: int
    correct_count: int
    correct_device_ids: list[str]
    missing_device_ids: list[str]
    missing_socket_ids: list[str]
    wrong_placements: list[WrongMountingPlacement]
    extra_device_ids: list[str]
    message: str


class MountingProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_id: str
    attempt_count: int = 0
    last_submitted_at: datetime | None = None
    last_overall_correct: bool | None = None
    last_correct_count: int = 0
    required_count: int = 0
