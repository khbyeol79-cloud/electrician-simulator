from __future__ import annotations

from collections import Counter

from app.domain import WiringAttemptResult, WiringAttemptSubmit, WiringDraftUpdate
from app.repositories.problem_repository import ProblemRepository
from app.repositories.wiring_repository import WiringRepository
from app.services.wiring_network_service import build_network_components, compare_networks


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
        external_terminals = {
            terminal.terminal_id: terminal
            for device in (package.problem.wiring_semantics.external_devices if package.problem.wiring_semantics else [])
            for terminal in device.terminals
        }
        keys = [item.key for item in connections]
        if len(keys) != len(set(keys)):
            raise WiringValidationError("duplicate_connection", "같은 단자 연결이 중복되었습니다.")
        counts = Counter(terminal for key in keys for terminal in key)
        for connection in connections:
            for terminal in connection.key:
                pin = pins.get(terminal) or external_terminals.get(terminal)
                if pin is None:
                    raise WiringValidationError("unknown_terminal", f"존재하지 않는 단자입니다: {terminal}")
                if not getattr(pin, "enabled", True):
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
        elif package.answer.expected_nets:
            roles = {
                pin.terminal_id: pin.terminal_role
                for item in package.board.items
                for pin in item.pins
            }
            if package.problem.wiring_semantics:
                roles.update({
                    terminal.terminal_id: "external"
                    for device in package.problem.wiring_semantics.external_devices
                    for terminal in device.terminals
                })
            external_ids = {terminal for terminal, role in roles.items() if role == "external"}
            legacy_exact = submitted == required and not any(terminal in external_ids for edge in submitted for terminal in edge)
            if legacy_exact:
                result = WiringAttemptResult(
                    gradable=True,
                    overall_correct=True,
                    required_count=len(required),
                    correct_count=len(required),
                    missing_connections=[],
                    extra_connections=[],
                    forbidden_connections=[],
                    message="기존 버전의 정확한 결선으로 정상 처리되었습니다.",
                    electrically_equivalent=True,
                    required_net_count=len(package.answer.expected_nets),
                    correct_net_count=len(package.answer.expected_nets),
                )
                attempt_id = self.repository.save_attempt(problem_id, package.manifest.version, package.answer.answer_version, [item.model_dump(by_alias=True, mode="json") for item in submission.connections], result)
                return result.model_copy(update={"attempt_id": attempt_id})
            components = build_network_components(submitted, roles)
            expected = {item.net_id: frozenset(item.terminals) for item in package.answer.expected_nets}
            comparison = compare_networks(components, expected)
            forbidden = sorted(
                rule for rule in forbidden_rules
                if any(set(rule).issubset(component.terminals) for component in components)
            )
            policy = package.problem.wiring_semantics.extra_jumper_policy if package.problem.wiring_semantics else "warning"
            warnings: list[str] = []
            if comparison.isolated_junction_count:
                warnings.append(f"동작에 사용되지 않는 TB 점퍼 네트워크가 {comparison.isolated_junction_count}개 있습니다.")
            if comparison.loop_count:
                warnings.append(f"불필요한 TB 결선 루프가 {comparison.loop_count}개 있습니다.")
            policy_rejects = policy == "reject" and bool(comparison.isolated_junction_count or comparison.loop_count)
            equivalent = comparison.electrically_equivalent and not forbidden
            overall = equivalent and not policy_rejects
            alternative = overall and submitted != required
            if overall and alternative:
                message = "정답 예시와 다른 TB 번호를 사용했지만 전기적 연결관계가 정확합니다."
            elif overall:
                message = "모든 기능 단자의 전기적 연결관계가 정확합니다."
            elif comparison.merged_component_count:
                message = "서로 분리되어야 하는 회로가 연결되었습니다."
            elif comparison.missing_net_ids:
                message = "완성되지 않은 기능 회로가 있습니다. 회로도와 관련 기구를 다시 확인해 주세요."
            else:
                message = "불필요한 기능 단자 연결을 확인해 주세요."
            result = WiringAttemptResult(
                gradable=True,
                overall_correct=overall,
                required_count=len(expected),
                correct_count=len(comparison.correct_net_ids),
                missing_connections=comparison.missing_net_ids,
                extra_connections=[f"extra-network-{index + 1}" for index in range(comparison.extra_component_count + comparison.isolated_junction_count)],
                forbidden_connections=[f"{left}|{right}" for left, right in forbidden],
                message=message,
                electrically_equivalent=equivalent,
                used_alternative_tb_numbers=alternative,
                required_net_count=len(expected),
                correct_net_count=len(comparison.correct_net_ids),
                missing_net_count=len(comparison.missing_net_ids),
                merged_net_count=comparison.merged_component_count,
                extra_connection_count=comparison.extra_component_count + comparison.isolated_junction_count,
                warnings=warnings,
            )
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
