from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


WireColor = Literal["brown", "black", "gray", "yellow"]


class WiringConnection(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    from_terminal: str = Field(alias="from")
    to: str
    wire_color: WireColor = "yellow"
    pair_display_color: str = Field(default="blue", max_length=30)

    @model_validator(mode="after")
    def reject_self_connection(self):
        if self.from_terminal == self.to:
            raise ValueError("같은 단자끼리는 연결할 수 없습니다.")
        return self

    @property
    def key(self) -> tuple[str, str]:
        return tuple(sorted((self.from_terminal, self.to)))


class WiringDraftUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    problem_version: int = Field(ge=1)
    mode: Literal["graphic", "summary"] = "graphic"
    connections: list[WiringConnection] = Field(max_length=500)


class WiringDraftResponse(WiringDraftUpdate):
    problem_id: str
    updated_at: datetime | None = None


class WiringAttemptSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    problem_version: int = Field(ge=1)
    connections: list[WiringConnection] = Field(max_length=500)


class WiringAttemptResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attempt_id: int | None = None
    gradable: bool
    overall_correct: bool | None
    required_count: int
    correct_count: int
    missing_connections: list[str]
    extra_connections: list[str]
    forbidden_connections: list[str]
    message: str
    electrically_equivalent: bool | None = None
    used_alternative_tb_numbers: bool = False
    required_net_count: int = 0
    correct_net_count: int = 0
    missing_net_count: int = 0
    merged_net_count: int = 0
    extra_connection_count: int = 0
    terminal_capacity_errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class WiringProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")
    problem_id: str
    attempt_count: int = 0
    last_submitted_at: datetime | None = None
    last_overall_correct: bool | None = None
    last_gradable: bool | None = None
    last_correct_count: int = 0
    required_count: int = 0
