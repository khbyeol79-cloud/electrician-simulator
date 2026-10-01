from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .answer_definition import AnswerDefinition
from .problem_definition import ProblemDefinition
from .problem_manifest import Difficulty, ProblemCapabilities, ProblemManifest, ProblemStatus, ProblemType
from .schematic_diagram import SchematicDiagram
from .board_definition import BoardDefinition


class ProblemValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Literal["error", "warning"]
    code: str
    message: str
    file: str | None = None
    field: str | None = None
    problem_id: str | None = None


class ProblemValidationResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    package_dir: Path
    issues: list[ProblemValidationIssue] = Field(default_factory=list)
    manifest: ProblemManifest | None = None
    problem: ProblemDefinition | None = None
    answer: AnswerDefinition | None = None
    diagram: SchematicDiagram | None = None
    board: BoardDefinition | None = None

    @property
    def is_valid(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def warning_count(self) -> int:
        return sum(issue.severity == "warning" for issue in self.issues)


class ProblemPackage(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    package_dir: Path
    manifest: ProblemManifest
    problem: ProblemDefinition
    answer: AnswerDefinition
    diagram: SchematicDiagram
    board: BoardDefinition | None = None
    warnings: list[ProblemValidationIssue] = Field(default_factory=list)


class ProblemSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_id: str
    title: str
    version: int
    problem_type: ProblemType
    status: ProblemStatus
    difficulty: Difficulty
    estimated_minutes: int
    tags: list[str]
    source_type: ProblemType
    selectable: bool
    warning_count: int


class PublicProblemDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_id: str
    title: str
    version: int
    problem_type: ProblemType
    status: ProblemStatus
    difficulty: Difficulty
    estimated_minutes: int
    tags: list[str]
    source_type: ProblemType
    source_name: str
    description: str
    instructions: list[str]
    learning_objectives: list[str]
    power_supply: dict[str, object]
    schematic: dict[str, str]
    board: dict[str, str]
    available_devices: list[dict[str, object]]
    circuit: dict[str, object]
    socket_questions: list[dict[str, object]]
    device_layout: dict[str, object] | None
    operation: dict[str, object] | None
    wiring_semantics: dict[str, object] | None
    warning_count: int
    capabilities: ProblemCapabilities


class CircuitSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_id: str
    problem_title: str
    device_count: int
    terminal_count: int
    contact_count: int
    coil_count: int
    socket_type_ids: list[str]
    reference_integrity: Literal["valid"]
    warning_count: int
    definition_status: Literal["structure_only", "functional"]
