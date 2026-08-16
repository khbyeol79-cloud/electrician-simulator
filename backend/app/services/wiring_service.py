from __future__ import annotations

from collections import Counter

from app.domain import WiringAttemptResult, WiringAttemptSubmit, WiringDraftUpdate
from app.repositories.problem_repository import ProblemRepository
from app.repositories.wiring_repository import WiringRepository


class WiringValidationError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 422):
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


class WiringService:
    def __init__(self, problems: ProblemRepository, repository: WiringRepository):
        self.problems = problems
        self.repository = repository

    def _package(self, problem_id: str):
        package = self.problems._get_package_internal(problem_id)
        if package is None:
            raise WiringValidationError("problem_not_found", "문제를 찾을 수 없습니다.", 404)
        if package.board is None:
            raise WiringValidationError("board_not_found", "이 문제에는 제어함 배치가 없습니다.", 404)
        return package

    def validate(self, problem_id: str, problem_version: int, connections):
        package = self._package(problem_id)
        if problem_version != package.manifest.version:
            raise WiringValidationError("problem_version_mismatch", "문제 버전이 변경되었습니다. 다시 불러와 주세요.", 409)
        pins = {pin.terminal_id: pin for item in package.board.items for pin in item.pins}
        keys = [item.key for item in connections]
        if len(keys) != len(set(keys)):
            raise WiringValidationError("duplicate_connection", "같은 단자 연결이 중복되었습니다.")
        counts = Counter(terminal for key in keys for terminal in key)
        for connection in connections:
            for terminal in connection.key:
                pin = pins.get(terminal)
                if pin is None:
                    raise WiringValidationError("unknown_terminal", f"존재하지 않는 단자입니다: {terminal}")
                if not pin.enabled:
                    raise WiringValidationError("disabled_terminal", f"사용할 수 없는 단자입니다: {terminal}")
                if counts[terminal] > pin.max_connections:
                    raise WiringValidationError("too_many_connections", f"단자의 최대 연결 수를 초과했습니다: {terminal}")
        return package

    def save_draft(self, problem_id: str, draft: WiringDraftUpdate):
        self.validate(problem_id, draft.problem_version, draft.connections)
        return self.repository.save_draft(problem_id, draft)

    def submit(self, problem_id: str, submission: WiringAttemptSubmit) -> WiringAttemptResult:
        package = self.validate(problem_id, submission.problem_version, submission.connections)
        submitted = {item.key for item in submission.connections}
        required = {tuple(sorted((item.from_terminal, item.to))) for item in package.answer.wiring_connections}
        forbidden_rules = {tuple(sorted((item.from_terminal, item.to))) for item in package.answer.wiring_forbidden_connections}
        if package.answer.verification.status == "unverified":
            result = WiringAttemptResult(gradable=False, overall_correct=None, required_count=len(required), correct_count=0, missing_connections=[], extra_connections=[], forbidden_connections=[], message="이 문제의 배선 정답은 아직 검증되지 않아 채점할 수 없습니다.")
        else:
            missing = sorted(required - submitted)
            extras = sorted(submitted - required)
            forbidden = sorted(submitted & forbidden_rules)
            correct = len(required & submitted)
            overall = not missing and not extras and not forbidden
            label = lambda key: f"{key[0]}|{key[1]}"
            result = WiringAttemptResult(gradable=True, overall_correct=overall, required_count=len(required), correct_count=correct, missing_connections=[label(item) for item in missing], extra_connections=[label(item) for item in extras], forbidden_connections=[label(item) for item in forbidden], message="모든 결선이 정확합니다." if overall else "누락 또는 잘못 연결된 단자를 확인해 주세요.")
        attempt_id = self.repository.save_attempt(problem_id, package.manifest.version, package.answer.answer_version, [item.model_dump(by_alias=True, mode="json") for item in submission.connections], result)
        return result.model_copy(update={"attempt_id": attempt_id})
