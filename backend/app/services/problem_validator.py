from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError

from app.domain import (
    AnswerDefinition,
    BoardDefinition,
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
            "board.json": self._read_schema("board.schema.json"),
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
        board: BoardDefinition | None = None

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
        board_data = self._load_json(
            package_dir, manifest.files.board, issues, problem_id
        ) if manifest.files.board else None

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

        if board_data and self._validate_schema(
            board_data, "board.json", issues, problem_id
        ):
            try:
                board = BoardDefinition.model_validate(board_data)
            except ValidationError as exc:
                issues.append(
                    self._issue(
                        "error", "pydantic_error", str(exc),
                        file=manifest.files.board, problem_id=problem_id
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
        if board:
            item_ids = [item.item_id for item in board.items]
            terminal_ids = [pin.terminal_id for item in board.items for pin in item.pins]
            for value, code, label in ((item_ids, "duplicate_board_item_id", "보드 장치 ID"), (terminal_ids, "duplicate_board_terminal_id", "보드 단자 ID")):
                duplicates = {item for item in value if value.count(item) > 1}
                for duplicate in duplicates:
                    issues.append(self._issue("error", code, f"{label}가 중복됩니다: {duplicate}", file=manifest.files.board, problem_id=problem_id))
            for item in board.items:
                if item.x < 0 or item.y < 0 or item.x + item.width > board.width or item.y + item.height > board.height:
                    issues.append(self._issue("error", "board_item_out_of_bounds", f"장치가 보드 영역을 벗어납니다: {item.item_id}", file=manifest.files.board, problem_id=problem_id))
                if item.socket_type_id:
                    socket = self.catalog.get_socket_type(item.socket_type_id)
                    if socket is None:
                        issues.append(self._issue("error", "unknown_board_socket_type", f"존재하지 않는 소켓 유형입니다: {item.socket_type_id}", file=manifest.files.board, problem_id=problem_id))
                    elif {pin.number for pin in item.pins if pin.number is not None} != set(socket.pins):
                        issues.append(self._issue("error", "board_socket_pin_mismatch", f"소켓 핀 배열이 카탈로그와 일치하지 않습니다: {item.item_id}", file=manifest.files.board, problem_id=problem_id))
            if answer:
                terminals = board.terminal_ids
                for connection in [*answer.wiring_connections, *answer.wiring_forbidden_connections]:
                    if connection.from_terminal not in terminals or connection.to not in terminals:
                        issues.append(self._issue("error", "unknown_board_answer_terminal", "배선 답안이 보드에 없는 단자를 참조합니다.", file=manifest.files.answer, problem_id=problem_id))

        if problem and problem.mounting:
            mounting = problem.mounting
            device_ids = [item.mount_device_id for item in mounting.available_devices]
            target_ids = [item.socket_id for item in mounting.mount_targets]
            for values, code, label in (
                (device_ids, "duplicate_mount_device_id", "장착 기구 ID"),
                (target_ids, "duplicate_mount_target_id", "장착 대상 ID"),
            ):
                for duplicate in {item for item in values if values.count(item) > 1}:
                    issues.append(self._issue("error", code, f"{label}가 중복됩니다: {duplicate}", file=manifest.files.problem, problem_id=problem_id))
            board_items = {item.item_id: item for item in board.items} if board else {}
            mount_devices = {item.mount_device_id: item for item in mounting.available_devices}
            mount_targets = {item.socket_id: item for item in mounting.mount_targets}
            for device in mounting.available_devices:
                catalog_device = self.catalog.get_device_type(device.device_type_id)
                if catalog_device is None:
                    issues.append(self._issue("error", "unknown_mount_device_type", f"존재하지 않는 기구 유형입니다: {device.device_type_id}", file=manifest.files.problem, problem_id=problem_id))
                for socket_type_id in device.compatible_socket_type_ids:
                    if self.catalog.get_socket_type(socket_type_id) is None:
                        issues.append(self._issue("error", "unknown_mount_socket_type", f"존재하지 않는 호환 소켓 유형입니다: {socket_type_id}", file=manifest.files.problem, problem_id=problem_id))
            for target in mounting.mount_targets:
                board_item = board_items.get(target.socket_id)
                if board_item is None or board_item.item_type not in ("socket_8p", "socket_12p"):
                    issues.append(self._issue("error", "unknown_mount_board_target", f"장착 대상이 보드의 소켓이 아닙니다: {target.socket_id}", file=manifest.files.problem, problem_id=problem_id))
                elif board_item.socket_type_id != target.socket_type_id:
                    issues.append(self._issue("error", "mount_target_socket_mismatch", f"장착 대상의 소켓 유형이 보드와 다릅니다: {target.socket_id}", file=manifest.files.problem, problem_id=problem_id))
                for device_type_id in target.allowed_device_type_ids:
                    if self.catalog.get_device_type(device_type_id) is None:
                        issues.append(self._issue("error", "unknown_allowed_mount_device_type", f"허용 기구 유형이 카탈로그에 없습니다: {device_type_id}", file=manifest.files.problem, problem_id=problem_id))
            if answer:
                answer_device_ids = [item.mount_device_id for item in answer.mounting_answer]
                answer_socket_ids = [item.socket_id for item in answer.mounting_answer]
                if len(answer_device_ids) != len(set(answer_device_ids)) or len(answer_socket_ids) != len(set(answer_socket_ids)):
                    issues.append(self._issue("error", "duplicate_mounting_answer", "기구 장착 정답에 중복된 기구 또는 소켓이 있습니다.", file=manifest.files.answer, problem_id=problem_id))
                for placement in answer.mounting_answer:
                    device = mount_devices.get(placement.mount_device_id)
                    target = mount_targets.get(placement.socket_id)
                    if device is None or target is None:
                        issues.append(self._issue("error", "unknown_mounting_answer_reference", "기구 장착 정답이 공개 데이터에 없는 기구 또는 소켓을 참조합니다.", file=manifest.files.answer, problem_id=problem_id))
                    elif target.socket_type_id not in device.compatible_socket_type_ids or device.device_type_id not in target.allowed_device_type_ids:
                        issues.append(self._issue("error", "incompatible_mounting_answer", "기구 장착 정답의 기구와 소켓이 호환되지 않습니다.", file=manifest.files.answer, problem_id=problem_id))

        if problem and problem.device_layout:
            placements = problem.device_layout.fixed_placements
            device_ids = [item.mount_device_id for item in placements]
            socket_ids = [item.socket_id for item in placements]
            if len(device_ids) != len(set(device_ids)) or len(socket_ids) != len(set(socket_ids)):
                issues.append(self._issue("error", "duplicate_fixed_device_placement", "고정 기구 배치에 중복된 기구 또는 소켓이 있습니다.", file=manifest.files.problem, problem_id=problem_id))
            board_items = {item.item_id: item for item in board.items} if board else {}
            for placement in placements:
                board_item = board_items.get(placement.socket_id)
                if board_item is None or board_item.item_type not in ("socket_8p", "socket_12p"):
                    issues.append(self._issue("error", "unknown_fixed_device_socket", f"고정 기구 위치가 보드의 소켓이 아닙니다: {placement.socket_id}", file=manifest.files.problem, problem_id=problem_id))
                elif board_item.socket_type_id != placement.socket_type_id:
                    issues.append(self._issue("error", "fixed_device_socket_mismatch", f"고정 기구의 소켓 유형이 보드와 다릅니다: {placement.socket_id}", file=manifest.files.problem, problem_id=problem_id))
                catalog_device = self.catalog.get_device_type(placement.device_type_id)
                if catalog_device is None:
                    issues.append(self._issue("error", "unknown_fixed_device_type", f"존재하지 않는 고정 기구 유형입니다: {placement.device_type_id}", file=manifest.files.problem, problem_id=problem_id))
                elif catalog_device.socket_type_id != placement.socket_type_id:
                    issues.append(self._issue("error", "incompatible_fixed_device", f"기구와 소켓 유형이 호환되지 않습니다: {placement.mount_device_id}", file=manifest.files.problem, problem_id=problem_id))

        return ProblemValidationResult(
            package_dir=package_dir,
            issues=issues,
            manifest=manifest,
            problem=problem,
            answer=answer,
            diagram=diagram,
            board=board,
        )
