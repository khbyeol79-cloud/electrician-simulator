from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError

from app.domain import (
    AnswerDefinition,
    ProblemDefinition,
    ProblemManifest,
    ProblemValidationIssue,
    ProblemValidationResult,
    SchematicDiagram,
)
from app.services.catalog_service import CatalogService
from app.services.circuit_reference_validator import CircuitReferenceValidator
from app.services.diagram_reference_validator import DiagramReferenceValidator


MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_SCHEMATIC_BYTES = 5 * 1024 * 1024


class ProblemPackageValidator:
    def __init__(self, schemas_dir: Path, catalog_dir: Path | None = None):
        self.schemas_dir = schemas_dir.resolve()
        self.catalog = CatalogService(
            catalog_dir or self.schemas_dir.parent / "catalog", self.schemas_dir
        )
        self.circuit_validator = CircuitReferenceValidator(self.catalog)
        self.diagram_validator = DiagramReferenceValidator()
        self._schemas = {
            "manifest.json": self._read_schema("manifest.schema.json"),
            "problem.json": self._read_schema("problem.schema.json"),
            "answer.json": self._read_schema("answer.schema.json"),
            "diagram.json": self._read_schema("diagram.schema.json"),
        }

    def _read_schema(self, name: str) -> dict[str, Any]:
        with (self.schemas_dir / name).open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _issue(
        severity: str,
        code: str,
        message: str,
        *,
        file: str | None = None,
        field: str | None = None,
        problem_id: str | None = None,
    ) -> ProblemValidationIssue:
        return ProblemValidationIssue(
            severity=severity,
            code=code,
            message=message,
            file=file,
            field=field,
            problem_id=problem_id,
        )

    def _safe_file(self, package_dir: Path, relative_path: str) -> Path | None:
        path = Path(relative_path)
        if path.is_absolute() or ".." in path.parts or path.drive:
            return None
        candidate = package_dir / path
        try:
            candidate.resolve(strict=False).relative_to(package_dir.resolve())
        except ValueError:
            return None
        return candidate

    def _load_json(
        self,
        package_dir: Path,
        relative_path: str,
        issues: list[ProblemValidationIssue],
        problem_id: str | None,
    ) -> dict[str, Any] | None:
        file_path = self._safe_file(package_dir, relative_path)
        if file_path is None:
            issues.append(
                self._issue(
                    "error",
                    "unsafe_path",
                    "문제 폴더 밖을 참조하는 경로는 사용할 수 없습니다.",
                    file=relative_path,
                    problem_id=problem_id,
                )
            )
            return None
        if not file_path.is_file():
            issues.append(
                self._issue(
                    "error",
                    "missing_file",
                    "필수 파일이 없습니다.",
                    file=relative_path,
                    problem_id=problem_id,
                )
            )
            return None
        if file_path.stat().st_size > MAX_JSON_BYTES:
            issues.append(
                self._issue(
                    "error",
                    "json_too_large",
                    "JSON 파일 크기가 허용 범위를 초과했습니다.",
                    file=relative_path,
                    problem_id=problem_id,
                )
            )
            return None
        try:
            with file_path.open("r", encoding="utf-8") as handle:
                value = json.load(handle)
        except (UnicodeError, json.JSONDecodeError) as exc:
            issues.append(
                self._issue(
                    "error",
                    "invalid_json",
                    f"JSON을 읽을 수 없습니다: {exc}",
                    file=relative_path,
                    problem_id=problem_id,
                )
            )
            return None
        if not isinstance(value, dict):
            issues.append(
                self._issue(
                    "error",
                    "invalid_json_root",
                    "JSON 최상위 값은 객체여야 합니다.",
                    file=relative_path,
                    problem_id=problem_id,
                )
            )
            return None
        return value

    def _validate_schema(
        self,
        data: dict[str, Any],
        schema_name: str,
        issues: list[ProblemValidationIssue],
        problem_id: str | None,
    ) -> bool:
        validator = Draft202012Validator(
            self._schemas[schema_name], format_checker=FormatChecker()
        )
        errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
        for error in errors:
            field = ".".join(str(part) for part in error.absolute_path) or None
            issues.append(
                self._issue(
                    "error",
                    "schema_error",
                    error.message,
                    file=schema_name,
                    field=field,
                    problem_id=problem_id,
                )
            )
        return not errors

    def validate(self, package_dir: Path) -> ProblemValidationResult:
        package_dir = package_dir.resolve()
        issues: list[ProblemValidationIssue] = []
        manifest_data = self._load_json(package_dir, "manifest.json", issues, None)
        manifest: ProblemManifest | None = None
        problem: ProblemDefinition | None = None
        answer: AnswerDefinition | None = None
        diagram: SchematicDiagram | None = None

        if manifest_data and self._validate_schema(
            manifest_data, "manifest.json", issues, manifest_data.get("problem_id")
        ):
            try:
                manifest = ProblemManifest.model_validate(manifest_data)
            except ValidationError as exc:
                issues.append(
                    self._issue(
                        "error",
                        "pydantic_error",
                        str(exc),
                        file="manifest.json",
                        problem_id=manifest_data.get("problem_id"),
                    )
                )

        if manifest is None:
            return ProblemValidationResult(package_dir=package_dir, issues=issues)

        problem_id = manifest.problem_id
        if package_dir.name != problem_id:
            issues.append(
                self._issue(
                    "error",
                    "folder_id_mismatch",
                    "폴더명과 problem_id가 일치하지 않습니다.",
                    file="manifest.json",
                    field="problem_id",
                    problem_id=problem_id,
                )
            )

        problem_data = self._load_json(
            package_dir, manifest.files.problem, issues, problem_id
        )
        answer_data = self._load_json(
            package_dir, manifest.files.answer, issues, problem_id
        )
        diagram_data = self._load_json(
            package_dir, manifest.files.diagram, issues, problem_id
        )

        if problem_data and self._validate_schema(
            problem_data, "problem.json", issues, problem_id
        ):
            try:
                problem = ProblemDefinition.model_validate(problem_data)
            except ValidationError as exc:
                issues.append(
                    self._issue(
                        "error", "pydantic_error", str(exc),
                        file="problem.json", problem_id=problem_id
                    )
                )

        if answer_data and self._validate_schema(
            answer_data, "answer.json", issues, problem_id
        ):
            try:
                answer = AnswerDefinition.model_validate(answer_data)
            except ValidationError as exc:
                issues.append(
                    self._issue(
                        "error", "pydantic_error", str(exc),
                        file="answer.json", problem_id=problem_id
                    )
                )

        if diagram_data and self._validate_schema(
            diagram_data, "diagram.json", issues, problem_id
        ):
            try:
                diagram = SchematicDiagram.model_validate(diagram_data)
            except ValidationError as exc:
                issues.append(
                    self._issue(
                        "error", "pydantic_error", str(exc),
                        file=manifest.files.diagram, problem_id=problem_id
                    )
                )

        for file_name, value in (
            (manifest.files.problem, problem),
            (manifest.files.answer, answer),
        ):
            if value is not None and value.problem_id != problem_id:
                issues.append(
                    self._issue(
                        "error",
                        "problem_id_mismatch",
                        "manifest.json과 problem_id가 일치하지 않습니다.",
                        file=file_name,
                        field="problem_id",
                        problem_id=problem_id,
                    )
                )

        schematic_path = self._safe_file(package_dir, manifest.files.schematic)
        if schematic_path is None:
            issues.append(
                self._issue(
                    "error", "unsafe_path", "안전하지 않은 회로도 경로입니다.",
                    file=manifest.files.schematic, problem_id=problem_id
                )
            )
        elif not schematic_path.is_file():
            issues.append(
                self._issue(
                    "error", "missing_schematic", "회로도 파일이 없습니다.",
                    file=manifest.files.schematic, problem_id=problem_id
                )
            )
        elif schematic_path.stat().st_size > MAX_SCHEMATIC_BYTES:
            issues.append(
                self._issue(
                    "error", "schematic_too_large", "회로도 파일 크기가 너무 큽니다.",
                    file=manifest.files.schematic, problem_id=problem_id
                )
            )

        if problem and problem.schematic.file != manifest.files.schematic:
            issues.append(
                self._issue(
                    "error",
                    "schematic_reference_mismatch",
                    "manifest와 problem의 회로도 파일명이 일치하지 않습니다.",
                    file=manifest.files.problem,
                    field="schematic.file",
                    problem_id=problem_id,
                )
            )

        if manifest.problem_type == "official" and not manifest.source.reference:
            issues.append(
                self._issue(
                    "warning", "official_source_missing",
                    "공식 문제의 출처 참조가 입력되지 않았습니다.",
                    file="manifest.json", field="source.reference", problem_id=problem_id
                )
            )
        if manifest.status == "verified" and manifest.source.verified_date is None:
            issues.append(
                self._issue(
                    "warning", "verified_date_missing",
                    "검증 완료 문제에 출처 검증일이 없습니다.",
                    file="manifest.json", field="source.verified_date", problem_id=problem_id
                )
            )

        if answer:
            if answer.verification.status == "unverified":
                issues.append(
                    self._issue(
                        "warning", "answer_unverified", "정답이 아직 검증되지 않았습니다.",
                        file=manifest.files.answer, field="verification.status", problem_id=problem_id
                    )
                )
            if answer.verification.status == "verified" and (
                not answer.verification.verified_by or not answer.verification.verified_at
            ):
                issues.append(
                    self._issue(
                        "warning", "answer_verifier_missing",
                        "검증 완료 정답에 검증자 또는 검증 시간이 없습니다.",
                        file=manifest.files.answer, field="verification", problem_id=problem_id
                    )
                )
            if manifest.status == "verified" and answer.verification.status != "verified":
                issues.append(
                    self._issue(
                        "error", "verification_status_mismatch",
                        "문제는 verified이지만 정답 검증이 완료되지 않았습니다.",
                        file=manifest.files.answer, field="verification.status", problem_id=problem_id
                    )
                )

        if problem and answer:
            issues.extend(self.circuit_validator.validate(problem, answer))
        if problem and diagram:
            issues.extend(self.diagram_validator.validate(problem, diagram))

        return ProblemValidationResult(
            package_dir=package_dir,
            issues=issues,
            manifest=manifest,
            problem=problem,
            answer=answer,
            diagram=diagram,
        )
