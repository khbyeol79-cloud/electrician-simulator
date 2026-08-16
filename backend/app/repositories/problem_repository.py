from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from app.domain import (
    CircuitSummary,
    ProblemPackage,
    ProblemSummary,
    ProblemValidationIssue,
    PublicProblemDetail,
)
from app.services.problem_validator import ProblemPackageValidator


STATUS_ORDER = {"verified": 0, "reviewed": 1, "draft": 2}


class ReloadStatistics(BaseModel):
    loaded: int
    excluded: int
    warnings: int


class ProblemRepository:
    def __init__(self, problems_dir: Path, schemas_dir: Path, catalog_dir: Path | None = None):
        self.problems_dir = problems_dir.resolve()
        self.validator = ProblemPackageValidator(schemas_dir, catalog_dir)
        self.catalog = self.validator.catalog
        self._packages: dict[str, ProblemPackage] = {}
        self._issues: list[ProblemValidationIssue] = []
        self._excluded = 0
        self._logger = logging.getLogger("electrician_simulator")

    def reload(self) -> ReloadStatistics:
        self._packages.clear()
        self._issues.clear()
        self._excluded = 0
        self.problems_dir.mkdir(parents=True, exist_ok=True)

        results = []
        for package_dir in sorted(self.problems_dir.iterdir()):
            if not package_dir.is_dir() or package_dir.name.startswith("_"):
                continue
            result = self.validator.validate(package_dir)
            results.append(result)

        ids = [result.manifest.problem_id for result in results if result.manifest]
        duplicates = {problem_id for problem_id, count in Counter(ids).items() if count > 1}

        for result in results:
            if result.manifest and result.manifest.problem_id in duplicates:
                result.issues.append(
                    ProblemValidationIssue(
                        severity="error",
                        code="duplicate_problem_id",
                        message="다른 문제 폴더와 problem_id가 중복됩니다.",
                        file="manifest.json",
                        field="problem_id",
                        problem_id=result.manifest.problem_id,
                    )
                )

            self._issues.extend(result.issues)
            if not result.is_valid or not (result.manifest and result.problem and result.answer and result.diagram):
                self._excluded += 1
                for issue in result.issues:
                    self._logger.warning(
                        "문제 제외 | id=%s code=%s file=%s message=%s",
                        issue.problem_id or result.package_dir.name,
                        issue.code,
                        issue.file or "-",
                        issue.message,
                    )
                continue

            package = ProblemPackage(
                package_dir=result.package_dir,
                manifest=result.manifest,
                problem=result.problem,
                answer=result.answer,
                diagram=result.diagram,
                board=result.board,
                warnings=[issue for issue in result.issues if issue.severity == "warning"],
            )
            self._packages[package.manifest.problem_id] = package

        return ReloadStatistics(
            loaded=len(self._packages),
            excluded=self._excluded,
            warnings=sum(issue.severity == "warning" for issue in self._issues),
        )

    def list_summaries(self) -> list[ProblemSummary]:
        packages = sorted(
            self._packages.values(),
            key=lambda package: (
                STATUS_ORDER[package.manifest.status],
                package.manifest.title,
                package.manifest.problem_id,
            ),
        )
        return [self._summary(package) for package in packages]

    def get_public(self, problem_id: str) -> PublicProblemDetail | None:
        package = self._packages.get(problem_id)
        if package is None:
            return None
        manifest = package.manifest
        problem = package.problem
        return PublicProblemDetail(
            problem_id=manifest.problem_id,
            title=manifest.title,
            version=manifest.version,
            problem_type=manifest.problem_type,
            status=manifest.status,
            difficulty=manifest.difficulty,
            estimated_minutes=manifest.estimated_minutes,
            tags=manifest.tags,
            source_type=manifest.source.type,
            source_name=manifest.source.name,
            description=problem.description,
            instructions=problem.instructions,
            learning_objectives=problem.learning_objectives,
            power_supply=problem.power_supply.model_dump(mode="json"),
            schematic=problem.schematic.model_dump(mode="json"),
            board=problem.board.model_dump(mode="json"),
            available_devices=problem.available_devices,
            circuit=problem.circuit.model_dump(mode="json"),
            socket_questions=[question.model_dump(mode="json") for question in problem.socket_questions],
            device_layout=problem.device_layout.model_dump(mode="json") if problem.device_layout else None,
            warning_count=len(package.warnings),
        )

    def _get_package_internal(self, problem_id: str) -> ProblemPackage | None:
        return self._packages.get(problem_id)

    def get_diagram(self, problem_id: str):
        package = self._packages.get(problem_id)
        return package.diagram if package else None

    def get_board(self, problem_id: str):
        package = self._packages.get(problem_id)
        return package.board if package else None

    def get_circuit_summary(self, problem_id: str) -> CircuitSummary | None:
        package = self._packages.get(problem_id)
        if package is None:
            return None
        circuit = package.problem.circuit
        return CircuitSummary(
            problem_id=problem_id,
            problem_title=package.manifest.title,
            device_count=len(circuit.devices),
            terminal_count=len(circuit.terminals),
            contact_count=len(circuit.contacts),
            coil_count=len(circuit.coils),
            socket_type_ids=sorted(
                {device.socket_type_id for device in circuit.devices if device.socket_type_id}
            ),
            reference_integrity="valid",
            warning_count=len(package.warnings),
            definition_status=circuit.definition_status,
        )

    def issues(self) -> list[ProblemValidationIssue]:
        return list(self._issues)

    @staticmethod
    def _summary(package: ProblemPackage) -> ProblemSummary:
        manifest = package.manifest
        return ProblemSummary(
            problem_id=manifest.problem_id,
            title=manifest.title,
            version=manifest.version,
            problem_type=manifest.problem_type,
            status=manifest.status,
            difficulty=manifest.difficulty,
            estimated_minutes=manifest.estimated_minutes,
            tags=manifest.tags,
            source_type=manifest.source.type,
            selectable=True,
            warning_count=len(package.warnings),
        )
