from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .problem_definition import WireColors


class AnswerVerification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["unverified", "reviewed", "verified"]
    verified_by: str | None = Field(default=None, max_length=120)
    verified_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)


class RequiredConnection(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    connection_id: str
    from_terminal: str = Field(alias="from")
    to: str
    wire_color: Literal["brown", "black", "gray", "yellow"]


class ExpectedNet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    net_id: str
    terminals: list[str] = Field(min_length=2)


class ForbiddenConnection(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_terminal: str = Field(alias="from")
    to: str


class AnswerDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    problem_id: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
    answer_version: int = Field(ge=1)
    verification: AnswerVerification
    socket_pin_answers: dict[str, dict[str, int]] = Field(default_factory=dict)
    required_connections: list[RequiredConnection] = Field(default_factory=list)
    expected_nets: list[ExpectedNet] = Field(default_factory=list)
    allowed_alternatives: list[dict[str, Any]] = Field(default_factory=list)
    forbidden_connections: list[ForbiddenConnection] = Field(default_factory=list)
    wire_color_rules: WireColors
    operation_tests: list[dict[str, Any]] = Field(default_factory=list)
