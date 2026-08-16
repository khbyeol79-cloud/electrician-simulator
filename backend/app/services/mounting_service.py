from __future__ import annotations

from app.domain import (
    MountingAttemptResult, MountingAttemptSubmit, MountingDraftUpdate,
    WrongMountingPlacement,
)
from app.repositories.mounting_repository import MountingRepository
from app.repositories.problem_repository import ProblemRepository


class MountingValidationError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 422):
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


class MountingService:
    def __init__(self, problems: ProblemRepository, repository: MountingRepository):
        self.problems = problems
        self.repository = repository

    def _package(self, problem_id: str):
        package = self.problems._get_package_internal(problem_id)
        if package is None:
            raise MountingValidationError("problem_not_found", "문제를 찾을 수 없습니다.", 404)
        if package.board is None:
            raise MountingValidationError("board_not_found", "이 문제에는 제어함 배치가 없습니다.", 404)
        if package.problem.mounting is None:
            raise MountingValidationError("mounting_not_ready", "이 문제의 기구 장착 데이터는 아직 준비되지 않았습니다.", 404)
        return package

    def validate(self, problem_id: str, problem_version: int, placements):
        package = self._package(problem_id)
        if problem_version != package.manifest.version:
            raise MountingValidationError("problem_version_mismatch", "문제 버전이 변경되었습니다. 다시 불러와 주세요.", 409)
        mounting = package.problem.mounting
        devices = {item.mount_device_id: item for item in mounting.available_devices}
        targets = {item.socket_id: item for item in mounting.mount_targets}
        device_ids = [item.mount_device_id for item in placements]
        socket_ids = [item.socket_id for item in placements]
        if len(device_ids) != len(set(device_ids)):
            raise MountingValidationError("duplicate_device", "같은 기구를 둘 이상의 소켓에 장착할 수 없습니다.")
        if len(socket_ids) != len(set(socket_ids)):
            raise MountingValidationError("duplicate_socket", "이미 다른 기구가 장착된 소켓입니다.")
        for placement in placements:
            device = devices.get(placement.mount_device_id)
            if device is None:
                raise MountingValidationError("unknown_mount_device", f"존재하지 않는 장착 기구입니다: {placement.mount_device_id}")
            target = targets.get(placement.socket_id)
            if target is None:
                raise MountingValidationError("unknown_mount_target", f"기구 장착 대상이 아닌 위치입니다: {placement.socket_id}")
            if not target.enabled:
                raise MountingValidationError("disabled_mount_target", f"사용할 수 없는 장착 위치입니다: {placement.socket_id}")
            if target.socket_type_id not in device.compatible_socket_type_ids:
                raise MountingValidationError("incompatible_socket_type", f"{device.label} 기구는 {target.socket_id} 소켓에 장착할 수 없습니다.")
            if device.device_type_id not in target.allowed_device_type_ids:
                raise MountingValidationError("device_type_not_allowed", f"{target.socket_id} 위치에는 {device.label} 기구를 장착할 수 없습니다.")
        return package

    def save_draft(self, problem_id: str, draft: MountingDraftUpdate):
        self.validate(problem_id, draft.problem_version, draft.placements)
        return self.repository.save_draft(problem_id, draft)

    def submit(self, problem_id: str, submission: MountingAttemptSubmit) -> MountingAttemptResult:
        package = self.validate(problem_id, submission.problem_version, submission.placements)
        expected = {item.mount_device_id: item.socket_id for item in package.answer.mounting_answer}
        submitted = {item.mount_device_id: item.socket_id for item in submission.placements}
        if package.answer.verification.status == "unverified":
            result = MountingAttemptResult(
                gradable=False, overall_correct=None, required_count=len(expected), correct_count=0,
                correct_device_ids=[], missing_device_ids=[], missing_socket_ids=[], wrong_placements=[],
                extra_device_ids=[], message="이 문제의 기구 장착 정답은 아직 검증되지 않아 채점할 수 없습니다.",
            )
        else:
            correct_ids = sorted(device_id for device_id, socket_id in submitted.items() if expected.get(device_id) == socket_id)
            missing_ids = sorted(set(expected) - set(submitted))
            extra_ids = sorted(set(submitted) - set(expected))
            wrong = sorted(
                (WrongMountingPlacement(mount_device_id=device_id, submitted_socket_id=socket_id)
                 for device_id, socket_id in submitted.items()
                 if device_id in expected and expected[device_id] != socket_id),
                key=lambda item: item.mount_device_id,
            )
            occupied_correctly = {submitted[item] for item in correct_ids}
            missing_sockets = sorted(set(expected.values()) - occupied_correctly)
            overall = len(correct_ids) == len(expected) and not extra_ids and len(submitted) == len(expected)
            result = MountingAttemptResult(
                gradable=True, overall_correct=overall, required_count=len(expected), correct_count=len(correct_ids),
                correct_device_ids=correct_ids, missing_device_ids=missing_ids, missing_socket_ids=missing_sockets,
                wrong_placements=wrong, extra_device_ids=extra_ids,
                message="모든 기구의 장착 위치가 정확합니다." if overall else "장착 위치를 다시 확인해 주세요.",
            )
        attempt_id = self.repository.save_attempt(
            problem_id, package.manifest.version, package.answer.answer_version,
            [item.model_dump(mode="json") for item in submission.placements], result,
        )
        return result.model_copy(update={"attempt_id": attempt_id})
