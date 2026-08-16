from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class WireColors(BaseModel):
    model_config = ConfigDict(extra="forbid")

    L1: Literal["brown"]
    L2: Literal["black"]
    L3: Literal["gray"]
    PE: Literal["green"]
    control: Literal["yellow"]


class PowerSupply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system: str = Field(min_length=1, max_length=60)
    voltage: float = Field(gt=0, le=1000)
    frequency: float = Field(gt=0, le=1000)
    wire_colors: WireColors


class SchematicReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: str
    format: Literal["svg"]
    view_box: str


class BoardReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout_id: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


class CircuitPlaceholder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    devices: list[dict[str, Any]] = Field(default_factory=list)
    terminals: list[dict[str, Any]] = Field(default_factory=list)
    contacts: list[dict[str, Any]] = Field(default_factory=list)
    coils: list[dict[str, Any]] = Field(default_factory=list)


class ProblemDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    problem_id: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
    description: str = Field(min_length=1, max_length=2000)
    instructions: list[str] = Field(min_length=1, max_length=30)
    learning_objectives: list[str] = Field(default_factory=list, max_length=30)
    power_supply: PowerSupply
    schematic: SchematicReference
    board: BoardReference
    available_devices: list[dict[str, Any]] = Field(default_factory=list)
    circuit: CircuitPlaceholder
    socket_questions: list[dict[str, Any]] = Field(default_factory=list)

