from __future__ import annotations

from app.domain import (
    CircuitAttemptResult,
    CircuitAttemptSubmit,
    CircuitQuestionResult,
)
from app.repositories.circuit_attempt_repository import CircuitAttemptRepository
from app.repositories.problem_repository import ProblemRepository


class CircuitAttemptValidationError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 422):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class CircuitAttemptService:
    def __init__(self, problems: ProblemRepository, attempts: CircuitAttemptRepository):
        self.problems = problems
        self.attempts = attempts

    def submit(self, problem_id: str, submission: CircuitAttemptSubmit) -> CircuitAttemptResult:
        package = self.problems._get_package_internal(problem_id)
        if package is None:
            raise CircuitAttemptValidationError("problem_not_found", "문제를 찾을 수 없습니다.", 404)
        if submission.problem_version != package.manifest.version:
            raise CircuitAttemptValidationError("problem_version_mismatch", "문제 버전이 변경되었습니다. 문제를 다시 불러와 주세요.", 409)

        questions = {item.question_id: item for item in package.problem.socket_questions}
        devices = {item.device_id: item for item in package.problem.circuit.devices}
        contacts = {item.contact_id: item for item in package.problem.circuit.contacts}
        coils = {item.coil_id: item for item in package.problem.circuit.coils}
        terminals = package.problem.circuit.terminals

        for question_id, slots in submission.responses.items():
            question = questions.get(question_id)
            if question is None:
                raise CircuitAttemptValidationError("unknown_question", f"존재하지 않는 질문입니다: {question_id}")
            allowed_slots = {slot.slot_id for slot in question.answer_slots}
            unknown_slots = set(slots) - allowed_slots
            if unknown_slots:
                raise CircuitAttemptValidationError("unknown_slot", f"존재하지 않는 슬롯입니다: {sorted(unknown_slots)[0]}")
            if len(slots.values()) != len(set(slots.values())):
                raise CircuitAttemptValidationError("duplicate_pin", "같은 질문의 슬롯에는 서로 다른 핀 번호를 선택해야 합니다.")
            element = contacts.get(question.target_element_id) if question.target_element_type == "contact" else coils.get(question.target_element_id)
            owner_id = element.owner_device_id if element else ""
            device = devices.get(owner_id)
            socket = self.problems.catalog.get_socket_type(device.socket_type_id or "") if device else None
            if socket is None:
                raise CircuitAttemptValidationError("socket_not_found", "질문 대상의 소켓 규격을 찾을 수 없습니다.")
            for pin in slots.values():
                if pin not in socket.pins:
                    raise CircuitAttemptValidationError("invalid_socket_pin", f"소켓에 존재하지 않는 핀 번호입니다: {pin}")
                matching = [item for item in terminals if item.device_id == owner_id and item.pin_number == pin]
                if matching and not any(item.enabled for item in matching):
                    raise CircuitAttemptValidationError("disabled_terminal", f"사용할 수 없는 단자입니다: {owner_id}-{pin}")

        total = len(questions)
        answered = sum(
            1 for question_id, question in questions.items()
            if set(submission.responses.get(question_id, {})) == {slot.slot_id for slot in question.answer_slots}
        )
        verification = package.answer.verification.status
        if verification == "unverified":
            result = CircuitAttemptResult(
                gradable=False, overall_correct=None, answered_count=answered,
                total_count=total, correct_count=0,
                message="이 문제의 정답은 아직 검증되지 않아 채점할 수 없습니다.", results=[],
            )
        else:
            results: list[CircuitQuestionResult] = []
            correct_count = 0
            for question_id, question in questions.items():
                expected = package.answer.socket_pin_answers.get(question_id, {})
                submitted = submission.responses.get(question_id, {})
                slot_results = {
                    slot.slot_id: submitted.get(slot.slot_id) == expected.get(slot.slot_id)
                    for slot in question.answer_slots
                }
                correct = bool(slot_results) and all(slot_results.values())
                correct_count += int(correct)
                results.append(CircuitQuestionResult(question_id=question_id, correct=correct, slot_results=slot_results))
            overall = total > 0 and answered == total and correct_count == total
            result = CircuitAttemptResult(
                gradable=True, overall_correct=overall, answered_count=answered,
                total_count=total, correct_count=correct_count,
                message="모든 답이 정확합니다." if overall else "입력한 소켓번호를 다시 확인해 주세요.",
                results=results,
            )

        attempt_id = self.attempts.save(
            problem_id=problem_id, problem_version=package.manifest.version,
            answer_version=package.answer.answer_version,
            responses=submission.responses, result=result,
        )
        return result.model_copy(update={"attempt_id": attempt_id})
