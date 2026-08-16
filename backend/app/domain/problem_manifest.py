from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ProblemType = Literal["official", "reconstructed", "variant", "practice", "original"]
ProblemStatus = Literal["draft", "reviewed", "verified"]
Difficulty = Literal["beginner", "intermediate", "advanced"]


class ProblemSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: ProblemType
    name: str = Field(min_length=1, max_length=160)
    reference: str | None = Field(default=None, max_length=500)
    verified_date: date | None = None


class ProblemFiles(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem: str
    answer: str
    schematic: str


class ProblemManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    problem_id: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$", min_length=3, max_length=80)
    title: str = Field(min_length=1, max_length=120)
    version: int = Field(ge=1)
    problem_type: ProblemType
    status: ProblemStatus
    difficulty: Difficulty
    estimated_minutes: int = Field(ge=1, le=600)
    tags: list[str] = Field(default_factory=list, max_length=20)
    source: ProblemSource
    files: ProblemFiles

