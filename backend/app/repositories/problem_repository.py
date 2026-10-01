from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from app.domain import (
    CircuitSummary,
    ProblemPackage,
    ProblemCapabilities,
    ProblemSummary,
    ProblemValidationIssue,
    PublicProblemDetail,
)
from app.services.problem_validator import ProblemPackageValidator


STATUS_ORDER = {"verified": 0, "reviewed": 1, "draft": 2}
QNET_COMMON_PREVIEW_IDS = {
    *(f"qnet_electrician_practical_{number:03d}" for number in (*range(1, 8), 9)),
    *(f"qnet_electrician_practical_{number:03d}" for number in range(11, 18)),
}


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
        capabilities = self.capabilities(package)
        expose_operation = capabilities.operation_gradable
        wiring_semantics = problem.wiring_semantics.model_dump(mode="json") if problem.wiring_semantics else None
        if wiring_semantics is not None and problem.operation:
            public_contact_types = {
                control.control_id: control.contact_type
                for control in problem.operation.controls
                if control.control_type in {"pushbutton", "limit_switch"}
            }
            for device in wiring_semantics["external_devices"]:
                if device.get("contact_type") is None and device["device_id"] in public_contact_types:
                    device["contact_type"] = public_contact_types[device["device_id"]]
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
            operation=(
                problem.operation.model_dump(by_alias=True, mode="json")
                if problem.operation and expose_operation else None
            ),
            wiring_semantics=wiring_semantics,
            warning_count=len(package.warnings),
            capabilities=capabilities,
        )

    def capabilities(self, package: ProblemPackage) -> ProblemCapabilities:
        declared = package.manifest.capabilities
        if declared is not None:
            if not declared.wiring_gradable and not declared.operation_gradable:
                return declared
            verified_answer = package.answer.verification.status != "unverified"
            return declared.model_copy(update={
                "wiring_gradable": declared.wiring_gradable and verified_answer,
                "operation_gradable": declared.operation_gradable and verified_answer,
            })
        is_qnet_capture = (
            package.manifest.problem_type == "official"
            and package.manifest.problem_id.startswith("qnet_electrician_practical_")
            and package.board is not None
        )
        if is_qnet_capture:
            return ProblemCapabilities(
                board_visible=True,
                wiring_editable=True,
                wiring_gradable=False,
                operation_previewable=package.manifest.problem_id in QNET_COMMON_PREVIEW_IDS,
                operation_gradable=False,
            )
        verified_answer = package.answer.verification.status != "unverified"
        legacy_visible = not (
            package.manifest.problem_type == "official" and package.manifest.status == "draft"
        )
        functional_operation = bool(
            package.problem.operation
            and package.problem.operation.simulation_status == "functional"
        )
        return ProblemCapabilities(
            board_visible=legacy_visible,
            wiring_editable=legacy_visible,
            wiring_gradable=verified_answer,
            operation_previewable=legacy_visible and verified_answer and functional_operation,
            operation_gradable=verified_answer and functional_operation and bool(package.answer.operation_tests),
        )

    def get_capabilities(self, problem_id: str) -> ProblemCapabilities | None:
        package = self._packages.get(problem_id)
        return self.capabilities(package) if package else None

    def _get_package_internal(self, problem_id: str) -> ProblemPackage | None:
        return self._packages.get(problem_id)

    def get_diagram(self, problem_id: str):
        package = self._packages.get(problem_id)
        return package.diagram if package else None

    def get_schematic_path(self, problem_id: str) -> Path | None:
        package = self._packages.get(problem_id)
        if package is None:
            return None
        path = (package.package_dir / package.manifest.files.schematic).resolve()
        try:
            path.relative_to(package.package_dir.resolve())
        except ValueError:
            return None
        return path if path.is_file() else None

    def get_layout_reference_path(self, problem_id: str) -> Path | None:
        """Return the audited PDF page-5 layout reference bundled with a problem."""
        package = self._packages.get(problem_id)
        if package is None:
            return None
        path = (package.package_dir / "layout-reference.png").resolve()
        try:
            path.relative_to(package.package_dir.resolve())
        except ValueError:
            return None
        return path if path.is_file() else None

    def get_board(self, problem_id: str):
        package = self._packages.get(problem_id)
        return package.board if package else None

    def get_analysis_reference_path(self, problem_id: str, reference_id: str) -> Path | None:
        # Only bundled public PDF renders; never resolve arbitrary filenames.
        if reference_id not in {"operation", "internal", "mc", "eocr", "timer", "relay",
                                "fr", "fls", "ss", "socket8", "socket12"}:
            return None
        package = self._packages.get(problem_id)
        if package is None:
            return None
        path = (package.package_dir / "study-references" / f"{reference_id}.png").resolve()
        if not path.is_relative_to(package.package_dir.resolve()):
            return None
        return path if path.is_file() else None

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
