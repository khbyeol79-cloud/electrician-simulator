from __future__ import annotations

from secrets import token_urlsafe

from fastapi import APIRouter, HTTPException, Request, Response

from app.domain import (
    OperationAction,
    OperationCheckItem,
    OperationCheckResult,
    OperationProgress,
    OperationSessionCreate,
    OperationSessionState,
    OperationSetupResponse,
)
from app.repositories import OperationRepository, ProblemRepository
from app.repositories.wiring_repository import WiringRepository
from app.simulation import OperationEngine, OperationSessionNotFound, SimulationDefinitionError


problem_router = APIRouter(prefix="/api/problems", tags=["operation"])
session_router = APIRouter(prefix="/api/operation-sessions", tags=["operation"])


def _problems(request: Request) -> ProblemRepository:
    repository = getattr(request.app.state, "problem_repository", None)
    if repository is None:
        raise HTTPException(status_code=503, detail="문제 저장소를 준비할 수 없습니다.")
    return repository


def _engine(request: Request, session_id: str) -> OperationEngine:
    try:
        return request.app.state.operation_sessions.get(session_id)
    except OperationSessionNotFound as exc:
        raise HTTPException(status_code=404, detail="동작시험 세션을 찾을 수 없습니다.") from exc


@problem_router.get("/{problem_id}/operation-setup", response_model=OperationSetupResponse)
def get_operation_setup(problem_id: str, request: Request) -> OperationSetupResponse:
    package = _problems(request)._get_package_internal(problem_id)
    if package is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    if package.board is None:
        raise HTTPException(status_code=404, detail="이 문제의 제어함 배치를 찾을 수 없습니다.")

    wiring_repository = WiringRepository(request.app.state.database)
    draft = wiring_repository.get_draft(problem_id)
    if draft is not None and draft.problem_version != package.manifest.version:
        draft = None
    accepted = wiring_repository.accepted_snapshot(problem_id, package.manifest.version)
    progress = wiring_repository.progress(problem_id)
    layout = package.problem.device_layout
    operation = package.problem.operation
    functional = operation is not None and operation.simulation_status == "functional"
    operation_ready = accepted is not None and layout is not None and functional
    preview_allowed = layout is not None and not operation_ready
    wiring_source = "accepted_submission" if accepted else "draft_preview" if draft and draft.connections else "none"
    wiring_exists = accepted is not None or bool(draft and draft.connections)

    if layout is None:
        message = "이 문제의 기구 배치 정보가 준비되지 않았습니다."
    elif operation_ready:
        message = "정상 결선 제출 스냅샷으로 동작시험을 시작할 수 있습니다."
    elif operation is None or operation.simulation_status != "functional":
        message = "이 문제에는 실제 동작 데이터가 없어 읽기 전용 미리보기만 제공합니다."
    elif accepted is None and progress.attempt_count:
        message = "정상 결선을 제출한 후 동작시험을 진행해 주세요."
    elif not wiring_exists:
        message = "저장된 결선이 없습니다. 제어함 결선부터 진행해 주세요."
    else:
        message = "결선을 제출한 뒤 동작시험을 진행해 주세요."

    return OperationSetupResponse(
        problem_id=problem_id,
        problem_version=package.manifest.version,
        board=package.board,
        device_layout=layout,
        wiring_draft=draft,
        wiring_source=wiring_source,
        wiring_snapshot=accepted,
        wiring_submission=progress,
        wiring_exists=wiring_exists,
        operation_ready=operation_ready,
        preview_allowed=preview_allowed,
        message=message,
        operation=operation,
    )


@problem_router.post("/{problem_id}/operation-sessions", response_model=OperationSessionState, status_code=201)
def create_operation_session(problem_id: str, payload: OperationSessionCreate, request: Request):
    package = _problems(request)._get_package_internal(problem_id)
    if package is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    if payload.problem_version != package.manifest.version:
        raise HTTPException(status_code=409, detail="문제 버전이 변경되었습니다. 다시 불러와 주세요.")
    if package.problem.operation is None or package.problem.operation.simulation_status != "functional":
        raise HTTPException(status_code=409, detail="이 문제의 동작 시뮬레이션 데이터가 준비되지 않았습니다.")
    snapshot = WiringRepository(request.app.state.database).accepted_snapshot(
        problem_id, package.manifest.version, payload.wiring_attempt_id
    )
    if snapshot is None:
        raise HTTPException(status_code=409, detail="정상 결선을 제출한 후 동작시험을 진행해 주세요.")
    session_id = token_urlsafe(24)
    try:
        engine = OperationEngine(
            session_id=session_id,
            problem_id=problem_id,
            wiring_attempt_id=snapshot.attempt_id,
            circuit=package.problem.circuit,
            definition=package.problem.operation,
            connections=snapshot.connections,
        )
    except SimulationDefinitionError as exc:
        raise HTTPException(status_code=422, detail=f"동작 회로 정의를 확인해 주세요. {exc}") from exc
    request.app.state.operation_sessions.add(engine)
    return engine.state()


@problem_router.get("/{problem_id}/operation-progress", response_model=OperationProgress)
def get_operation_progress(problem_id: str, request: Request):
    if _problems(request)._get_package_internal(problem_id) is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    return OperationRepository(request.app.state.database).progress(problem_id)


@session_router.get("/{session_id}", response_model=OperationSessionState)
def get_operation_session(session_id: str, request: Request):
    return _engine(request, session_id).state()


@session_router.post("/{session_id}/actions", response_model=OperationSessionState)
def apply_operation_action(session_id: str, payload: OperationAction, request: Request):
    try:
        return _engine(request, session_id).apply(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@session_router.post("/{session_id}/reset", response_model=OperationSessionState)
def reset_operation_session(session_id: str, request: Request):
    return _engine(request, session_id).reset()


def _matches_expectation(state: OperationSessionState, expected: dict) -> bool:
    payload = state.model_dump(mode="json")
    for group, value in expected.items():
        actual = payload.get(group)
        if isinstance(value, dict):
            if not isinstance(actual, dict):
                return False
            for key, expected_value in value.items():
                actual_value = actual.get(key)
                if isinstance(expected_value, dict):
                    if not isinstance(actual_value, dict) or any(actual_value.get(k) != v for k, v in expected_value.items()):
                        return False
                elif actual_value != expected_value:
                    return False
        elif actual != value:
            return False
    return True


@session_router.post("/{session_id}/run-check", response_model=OperationCheckResult)
def run_operation_check(session_id: str, request: Request):
    manual = _engine(request, session_id)
    package = _problems(request)._get_package_internal(manual.problem_id)
    if package is None or package.problem.operation is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    tests = package.answer.operation_tests
    if package.answer.verification.status == "unverified" or not tests:
        return OperationCheckResult(
            gradable=False, overall_passed=None, passed_count=0, total_count=0, results=[],
            message="이 문제의 동작시험 정답은 아직 검증되지 않아 채점할 수 없습니다.",
        )

    results: list[OperationCheckItem] = []
    all_fault_codes: list[str] = []
    for test in tests:
        isolated = OperationEngine(
            session_id="isolated-check",
            problem_id=manual.problem_id,
            wiring_attempt_id=manual.wiring_attempt_id,
            circuit=package.problem.circuit,
            definition=package.problem.operation,
            connections=manual.connections,
        )
        passed = True
        try:
            for step in test.get("steps", []):
                action_payload = {key: value for key, value in step.items() if key != "expect"}
                state = isolated.apply(OperationAction.model_validate(action_payload))
                if not _matches_expectation(state, step.get("expect", {})):
                    passed = False
                    break
        except (ValueError, SimulationDefinitionError):
            passed = False
        all_fault_codes.extend(item.code for item in isolated.faults)
        results.append(OperationCheckItem(
            test_id=str(test.get("test_id", "UNKNOWN")),
            label=str(test.get("label", "동작 확인")),
            passed=passed,
            message="정상" if passed else "동작 조건을 다시 확인해 주세요.",
        ))

    passed_count = sum(item.passed for item in results)
    result = OperationCheckResult(
        gradable=True,
        overall_passed=passed_count == len(results),
        passed_count=passed_count,
        total_count=len(results),
        results=results,
        message="모든 시험 조건이 정상적으로 작동했습니다." if passed_count == len(results) else "일부 동작을 다시 확인해 주세요.",
    )
    OperationRepository(request.app.state.database).save_attempt(
        problem_id=manual.problem_id,
        problem_version=package.manifest.version,
        wiring_attempt_id=manual.wiring_attempt_id,
        result=result,
        fault_codes=all_fault_codes,
    )
    return result


@session_router.delete("/{session_id}", status_code=204)
def delete_operation_session(session_id: str, request: Request):
    try:
        request.app.state.operation_sessions.delete(session_id)
    except OperationSessionNotFound as exc:
        raise HTTPException(status_code=404, detail="동작시험 세션을 찾을 수 없습니다.") from exc
    return Response(status_code=204)


router = problem_router
