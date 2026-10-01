from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .wiring_attempt import PracticeSafetyIssue, WireColor


class CaptureConnection(BaseModel):
    """A user-authored wire. Structural mistakes are retained and warned about."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    from_terminal: str = Field(alias="from", min_length=1, max_length=120)
    to: str = Field(min_length=1, max_length=120)
    wire_color: WireColor = "yellow"
    pair_display_color: str = Field(default="blue", max_length=30)

    @property
    def key(self) -> tuple[str, str]:
        return tuple(sorted((self.from_terminal, self.to)))


class StructuralWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    severity: Literal["warning", "blocking"] = "warning"
    connection_indexes: list[int] = Field(default_factory=list)


class WiringCaptureUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    problem_version: int = Field(ge=1)
    mode: Literal["graphic", "summary"] = "graphic"
    workspace_name: str | None = Field(default=None, min_length=1, max_length=80)
    connections: list[CaptureConnection] = Field(max_length=500)


class WiringCaptureDraftResponse(WiringCaptureUpdate):
    problem_id: str
    workspace_id: str
    workspace_name: str
    source: Literal["user_practice_draft"] = "user_practice_draft"
    verified_answer: bool = False
    gradable: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    latest_snapshot_id: str | None = None
    structural_warnings: list[StructuralWarning] = Field(default_factory=list)
    safety_status: Literal["safe", "attention", "blocked"] = "safe"
    safety_issues: list[PracticeSafetyIssue] = Field(default_factory=list)


class WiringWorkspaceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    problem_version: int = Field(ge=1)
    workspace_name: str = Field(min_length=1, max_length=80)


class WiringWorkspaceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    problem_id: str
    problem_version: int
    workspace_id: str
    workspace_name: str
    created_at: datetime
    updated_at: datetime
    connection_count: int
    latest_snapshot_id: str | None = None


class WiringSnapshotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str | None = Field(default=None, max_length=80)


class WiringSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snapshot_id: str
    problem_id: str
    problem_version: int
    workspace_id: str
    label: str | None = None
    created_at: datetime
    connections: list[CaptureConnection]
    structural_warnings: list[StructuralWarning] = Field(default_factory=list)


class WiringCaptureExport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    problem_id: str
    problem_version: int
    workspace_id: str
    workspace_name: str
    snapshot_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    connections: list[CaptureConnection] = Field(max_length=500)
    structural_warnings: list[StructuralWarning] = Field(default_factory=list)


class WiringCaptureImport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"]
    problem_id: str
    problem_version: int = Field(ge=1)
    workspace_id: str
    workspace_name: str = Field(min_length=1, max_length=80)
    snapshot_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    connections: list[CaptureConnection] = Field(max_length=500)
    structural_warnings: list[StructuralWarning] = Field(default_factory=list)
