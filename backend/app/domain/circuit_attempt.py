from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CircuitAttemptSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    problem_version: int = Field(ge=1)
    responses: dict[str, dict[str, int]]


class CircuitQuestionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: str
    correct: bool
    slot_results: dict[str, bool]


class CircuitAttemptResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attempt_id: int | None = None
    gradable: bool
    overall_correct: bool | None
    answered_count: int
    total_count: int
    correct_count: int
    message: str
    results: list[CircuitQuestionResult]


class CircuitProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")
    problem_id: str
    attempt_count: int
    last_submitted_at: datetime | None = None
    last_overall_correct: bool | None = None
    last_correct_count: int = 0
    total_count: int = 0
