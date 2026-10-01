from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .problem_definition import WireColors
from .mounting_attempt import MountingAnswerPlacement


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


class TerminalSwap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left: list[str] = Field(min_length=1, max_length=20)
    right: list[str] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_sides(self):
        if len(self.left) != len(self.right):
            raise ValueError("교환 단자 목록의 길이가 일치해야 합니다.")
        terminals = [*self.left, *self.right]
        if len(terminals) != len(set(terminals)):
            raise ValueError("한 대체 규칙에서 단자를 중복할 수 없습니다.")
        return self


class AllowedAlternative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alternative_id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    label: str = Field(min_length=1, max_length=120)
    terminal_swaps: list[TerminalSwap] = Field(min_length=1, max_length=10)


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
    allowed_alternatives: list[AllowedAlternative] = Field(default_factory=list)
    forbidden_connections: list[ForbiddenConnection] = Field(default_factory=list)
    wiring_connections: list[RequiredConnection] = Field(default_factory=list)
    wiring_forbidden_connections: list[ForbiddenConnection] = Field(default_factory=list)
    mounting_answer: list[MountingAnswerPlacement] = Field(default_factory=list)
    wire_color_rules: WireColors
    operation_tests: list[dict[str, Any]] = Field(default_factory=list)
