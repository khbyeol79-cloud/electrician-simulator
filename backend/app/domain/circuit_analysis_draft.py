from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CircuitAnalysisDraftUpdate(BaseModel):
    problem_version: int = Field(ge=1)
    memo: str = Field(default="", max_length=20_000)
    selected_device_ids: list[str] = Field(default_factory=list, max_length=200)
    selected_socket_ids: list[str] = Field(default_factory=list, max_length=200)
    selected_terminal_ids: list[str] = Field(default_factory=list, max_length=500)
    annotations: dict[str, str] = Field(default_factory=dict)


class CircuitAnalysisDraftResponse(CircuitAnalysisDraftUpdate):
    problem_id: str
    updated_at: datetime | None = None
