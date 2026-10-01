from __future__ import annotations

from secrets import token_urlsafe

from fastapi import APIRouter, HTTPException, Request, Response

from app.domain import (
    BehaviorRequirementItem,
    BehaviorRequirementResult,
    BehaviorRequirementSummary,
    BehaviorScenarioItem,
    OperationAction,
    OperationCheckItem,
    OperationCheckResult,
    OperationProgress,
    PracticeOperationSessionCreate,
    OperationSessionCreate,
    OperationSessionState,
    OperationSetupResponse,
)
from app.domain.operation_definition import OperationControl
from app.domain.problem_definition import CircuitTerminal
from app.repositories import OperationRepository, PracticeWiringRepository, ProblemRepository
from app.repositories.wiring_repository import WiringRepository
from app.simulation import OperationEngine, OperationSessionNotFound, SimulationDefinitionError, matches_expectation
from app.services import DeviceBehaviorRuntimeComposer, PracticeSafetyService, RuntimeCompositionError
from app.core.user_context import request_database, request_user_id
from app.services.qnet_requirements import reviewed_requirements


problem_router = APIRouter(prefix="/api/problems", tags=["operation"])
session_router = APIRouter(prefix="/api/operation-sessions", tags=["operation"])
QNET_SEQUENCE_PREVIEW_IDS = {
    f"qnet_electrician_practical_{number:03d}" for number in range(11, 18)
}
QNET_LEVEL_PREVIEW_IDS = {
    f"qnet_electrician_practical_{number:03d}" for number in (*range(1, 8), 9)
}
QNET_SEQUENCE_RUNTIME_REFERENCE = "qnet_electrician_practical_018"
QNET_LEVEL_RUNTIME_REFERENCE = "qnet_electrician_practical_008"


def _problems(request: Request) -> ProblemRepository:
    repository = getattr(request.app.state, "problem_repository", None)
    if repository is None:
        raise HTTPException(status_code=503, detail="문제 저장소를 준비할 수 없습니다.")
    return repository


def _engine(request: Request, session_id: str) -> OperationEngine:
    try:
        return request.app.state.operation_sessions.get(session_id, request_user_id(request))
    except OperationSessionNotFound as exc:
        raise HTTPException(status_code=404, detail="동작시험 세션을 찾을 수 없습니다.") from exc


def _runtime_definition(request: Request, circuit, operation):
    repository = _problems(request)
    try:
        return DeviceBehaviorRuntimeComposer(repository.catalog).compose(circuit, operation)
    except RuntimeCompositionError as exc:
        raise HTTPException(status_code=422, detail=f"동작 회로 구성을 확인해 주세요. {exc}") from exc


def _three_terminal_level_runtime(request: Request):
    """Adapt Q008's common level runtime to the C/A/M selector used by Q001~009."""
    reference = _problems(request)._get_package_internal(QNET_LEVEL_RUNTIME_REFERENCE)
    if reference is None or reference.problem.operation is None:
        raise HTTPException(status_code=503, detail="공통 수위제어 동작 정의를 준비할 수 없습니다.")
    circuit = reference.problem.circuit.model_copy(deep=True)
    operation = reference.problem.operation.model_copy(deep=True, update={"requirements": []})
    selector = next((item for item in circuit.devices if item.device_id == "SS"), None)
    if selector is None:
        raise HTTPException(status_code=503, detail="공통 수위제어 선택스위치를 준비할 수 없습니다.")
    selector.behavior_model_id = None
    circuit.terminals = [item for item in circuit.terminals if item.device_id != "SS"]
    circuit.contacts = [item for item in circuit.contacts if item.owner_device_id != "SS"]
    circuit.coils = [item for item in circuit.coils if item.owner_device_id != "SS"]
    circuit.terminals.extend([
        CircuitTerminal(
            terminal_id=f"SS-{suffix}", device_id="SS",
            terminal_type="external_terminal", electrical_role="control", max_connections=1,
        )
        for suffix in ("C", "A", "M")
    ])
    operation.controls = [item for item in operation.controls if item.control_id != "SS"]
    operation.controls.append(OperationControl(
        control_id="SS", label="SS 자동·수동", control_type="selector",
        mode="maintained", contact_type="NO", terminal_a_id="SS-C", terminal_b_id="SS-A",
        alternate_terminal_a_id="SS-C", alternate_terminal_b_id="SS-M", initial_active=True,
    ))
    return circuit, operation


def _base_practice_runtime_source(request: Request, package):
    """Return a public, ungraded common runtime for confirmed wiring candidates."""
    operation = package.problem.operation
    if operation is not None and operation.simulation_status == "functional":
        return package.problem.circuit, operation
    if package.manifest.problem_id in QNET_LEVEL_PREVIEW_IDS:
        circuit, operation = _three_terminal_level_runtime(request)
        if package.manifest.problem_id.endswith(("_004", "_007")):
            # PDF operation note requires T < FR interval. Equal defaults erase
            # the intermediate motor phase; these are explicit training times.
            for timer in operation.timers:
                timer.delay_ms = 500
        return circuit, operation
    if package.manifest.problem_id not in QNET_SEQUENCE_PREVIEW_IDS:
        return package.problem.circuit, operation
    reference = _problems(request)._get_package_internal(QNET_SEQUENCE_RUNTIME_REFERENCE)
    if reference is None or reference.problem.operation is None:
        raise HTTPException(status_code=503, detail="공통 시퀀스 동작 정의를 준비할 수 없습니다.")
    circuit = reference.problem.circuit.model_copy(deep=True)
    operation = reference.problem.operation.model_copy(deep=True, update={"requirements": []})
    return circuit, operation


def _practice_runtime_source(request: Request, package):
    circuit, operation = _base_practice_runtime_source(request, package)
    prefix = "qnet_electrician_practical_"
    problem_id = package.manifest.problem_id
    if operation is not None and problem_id.startswith(prefix):
        number = int(problem_id.removeprefix(prefix))
        if 1 <= number <= 18:
            operation = operation.model_copy(deep=True)
            if number == 5:
                # Allow observable alternating phases before both motors run.
                # These are training times, not a prescribed examination setting.
                for timer in operation.timers:
                    timer.delay_ms = 3000
            operation.requirements = reviewed_requirements(number, operation)
    return circuit, operation


@problem_router.get("/{problem_id}/operation-setup", response_model=OperationSetupResponse)
def get_operation_setup(problem_id: str, request: Request, workspace_id: str = "main") -> OperationSetupResponse:
    package = _problems(request)._get_package_internal(problem_id)
    if package is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    if package.board is None:
        raise HTTPException(status_code=404, detail="이 문제의 제어함 배치를 찾을 수 없습니다.")

    wiring_repository = WiringRepository(request_database(request))
    capabilities = _problems(request).capabilities(package)
    runtime_circuit, runtime_operation = _practice_runtime_source(request, package)
    practice_draft = PracticeWiringRepository(request_database(request)).get(problem_id, workspace_id) if capabilities.operation_previewable else None
    if practice_draft is not None and practice_draft.problem_version != package.manifest.version:
        practice_draft = None
    draft = practice_draft or wiring_repository.get_draft(problem_id)
    if draft is not None and draft.problem_version != package.manifest.version:
        draft = None
    accepted = wiring_repository.accepted_snapshot(problem_id, package.manifest.version)
    progress = wiring_repository.progress(problem_id)
    layout = package.problem.device_layout
    operation = (
        package.problem.operation
        if capabilities.operation_gradable
        else None
    )
    functional = runtime_operation is not None and runtime_operation.simulation_status == "functional"
    if practice_draft is not None:
        status, issues = PracticeSafetyService().inspect(
            package, practice_draft.connections,
            circuit=runtime_circuit, operation=runtime_operation,
        )
        draft = practice_draft.model_copy(update={"safety_status": status, "safety_issues": issues})
    operation_ready = accepted is not None and layout is not None and functional
    practice_ready = capabilities.operation_previewable and practice_draft is not None and functional
    operation_ready = operation_ready or practice_ready
    preview_allowed = capabilities.operation_previewable or (layout is not None and not operation_ready)
    wiring_source = "accepted_submission" if accepted else "practice_draft" if practice_draft is not None else "draft_preview" if draft and draft.connections else "none"
    wiring_exists = accepted is not None or bool(draft and draft.connections)

    if practice_ready:
        message = "사용자 연습 결선으로 무채점 동작시험을 시작할 수 있습니다. 안전 검사는 정답 채점이 아닙니다."
    elif capabilities.operation_previewable and functional and practice_draft is None:
        message = "현재 사용자 작업공간에 저장된 결선이 없습니다. 제어함 결선에서 작성하거나 JSON을 가져오세요."
    elif package.answer.verification.status == "unverified" and not capabilities.operation_previewable:
        message = "이 공식문제는 근거 검증 대기 상태이므로 동작시험을 사용할 수 없습니다."
    elif layout is None:
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
        behavior_requirements=[
            BehaviorRequirementSummary(
                requirement_id=item.requirement_id,
                label=item.label,
                scenario_id=item.scenario_id,
                scenario_label=item.scenario_label,
                next_action=item.next_action,
            )
            for item in (runtime_operation.requirements if runtime_operation else [])
        ],
    )


@problem_router.post("/{problem_id}/practice-sessions", response_model=OperationSessionState, status_code=201)
def create_practice_operation_session(problem_id: str, payload: PracticeOperationSessionCreate, request: Request):
    package = _problems(request)._get_package_internal(problem_id)
    if package is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    capabilities = _problems(request).capabilities(package)
    if not capabilities.operation_previewable or capabilities.operation_gradable:
        raise HTTPException(status_code=409, detail="이 문제는 무채점 연습 동작 세션 대상이 아닙니다.")
    if payload.problem_version != package.manifest.version:
        raise HTTPException(status_code=409, detail="문제 버전이 변경되었습니다. 다시 불러와 주세요.")
    runtime_circuit, operation = _practice_runtime_source(request, package)
    if operation is None or operation.simulation_status != "functional":
        raise HTTPException(status_code=409, detail="연습 동작 정의가 준비되지 않았습니다.")
    draft = PracticeWiringRepository(request_database(request)).get(problem_id, payload.workspace_id)
    if draft is None:
        raise HTTPException(status_code=409, detail="저장된 사용자 연습 결선이 없습니다.")
    if draft.problem_version != package.manifest.version:
        raise HTTPException(status_code=409, detail="연습 결선의 문제 버전이 오래되었습니다. 다시 저장해 주세요.")
    safety_status, safety_issues = PracticeSafetyService().inspect(
        package, draft.connections, circuit=runtime_circuit, operation=operation,
    )
    submitted_terminal_ids = {terminal for item in draft.connections for terminal in item.key}
    terminal_aliases = {
        terminal.operation_terminal_id: terminal.terminal_id
        for device in (package.problem.wiring_semantics.external_devices if package.problem.wiring_semantics else [])
        for terminal in device.terminals
        if terminal.operation_terminal_id and terminal.terminal_id in submitted_terminal_ids
    }
    runtime = _runtime_definition(request, runtime_circuit, operation)
    try:
        engine = OperationEngine(
            session_id=token_urlsafe(24), problem_id=problem_id, wiring_attempt_id=0,
            circuit=runtime.circuit, definition=runtime.operation, connections=draft.connections,
            terminal_aliases=terminal_aliases, catalog_composed=runtime.catalog_composed,
            composition_warnings=runtime.warnings, session_type="practice_preview_session",
            workspace_id=payload.workspace_id, gradable=False, safety_status=safety_status,
            power_permitted=safety_status != "blocked", safety_issues=safety_issues,
        )
    except SimulationDefinitionError as exc:
        raise HTTPException(status_code=422, detail=f"연습 동작 회로 정의를 확인해 주세요. {exc}") from exc
    request.app.state.operation_sessions.add(engine, request_user_id(request))
    return engine.state()


@problem_router.post("/{problem_id}/operation-sessions", response_model=OperationSessionState, status_code=201)
def create_operation_session(problem_id: str, payload: OperationSessionCreate, request: Request):
    package = _problems(request)._get_package_internal(problem_id)
    if package is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    if payload.problem_version != package.manifest.version:
        raise HTTPException(status_code=409, detail="문제 버전이 변경되었습니다. 다시 불러와 주세요.")
    if package.answer.verification.status == "unverified":
        raise HTTPException(status_code=409, detail="이 문제의 동작시험은 아직 검증되지 않아 사용할 수 없습니다.")
    if package.problem.operation is None or package.problem.operation.simulation_status != "functional":
        raise HTTPException(status_code=409, detail="이 문제의 동작 시뮬레이션 데이터가 준비되지 않았습니다.")
    snapshot = WiringRepository(request_database(request)).accepted_snapshot(
        problem_id, package.manifest.version, payload.wiring_attempt_id
    )
    if snapshot is None:
        raise HTTPException(status_code=409, detail="정상 결선을 제출한 후 동작시험을 진행해 주세요.")
    session_id = token_urlsafe(24)
    submitted_terminal_ids = {terminal for item in snapshot.connections for terminal in item.key}
    terminal_aliases = {
        terminal.operation_terminal_id: terminal.terminal_id
        for device in (package.problem.wiring_semantics.external_devices if package.problem.wiring_semantics else [])
        for terminal in device.terminals
        if terminal.operation_terminal_id and terminal.terminal_id in submitted_terminal_ids
    }
    runtime = _runtime_definition(request, package.problem.circuit, package.problem.operation)
    try:
        engine = OperationEngine(
            session_id=session_id,
            problem_id=problem_id,
            wiring_attempt_id=snapshot.attempt_id,
            circuit=runtime.circuit,
            definition=runtime.operation,
            connections=snapshot.connections,
            terminal_aliases=terminal_aliases,
            catalog_composed=runtime.catalog_composed,
            composition_warnings=runtime.warnings,
        )
    except SimulationDefinitionError as exc:
        raise HTTPException(status_code=422, detail=f"동작 회로 정의를 확인해 주세요. {exc}") from exc
    request.app.state.operation_sessions.add(engine, request_user_id(request))
    repository = OperationRepository(request_database(request))
    repository.start_manual_run(
        problem_id=problem_id,
        problem_version=package.manifest.version,
        wiring_attempt_id=snapshot.attempt_id,
    )
    state = engine.state()
    repository.observe_state(problem_id=problem_id, problem_version=package.manifest.version, state=state)
    return state


@problem_router.get("/{problem_id}/operation-progress", response_model=OperationProgress)
def get_operation_progress(problem_id: str, request: Request):
    if _problems(request)._get_package_internal(problem_id) is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    return OperationRepository(request_database(request)).progress(problem_id)


@session_router.get("/{session_id}", response_model=OperationSessionState)
def get_operation_session(session_id: str, request: Request):
    return _engine(request, session_id).state()


@session_router.post("/{session_id}/actions", response_model=OperationSessionState)
def apply_operation_action(session_id: str, payload: OperationAction, request: Request):
    try:
        engine = _engine(request, session_id)
        state = engine.apply(payload)
        package = _problems(request)._get_package_internal(engine.problem_id)
        if package is not None and engine.session_type == "verified_operation_session":
            OperationRepository(request_database(request)).observe_state(
                problem_id=engine.problem_id,
                problem_version=package.manifest.version,
                state=state,
            )
        return state
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@session_router.post("/{session_id}/reset", response_model=OperationSessionState)
def reset_operation_session(session_id: str, request: Request):
    return _engine(request, session_id).reset()


@session_router.post("/{session_id}/run-check", response_model=OperationCheckResult)
def run_operation_check(session_id: str, request: Request):
    manual = _engine(request, session_id)
    if manual.session_type == "practice_preview_session":
        raise HTTPException(status_code=409, detail="연습 동작 세션은 합격·불합격 채점을 제공하지 않습니다.")
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
        submitted_terminal_ids = {terminal for item in manual.connections for terminal in item.key}
        terminal_aliases = {
            terminal.operation_terminal_id: terminal.terminal_id
            for device in (package.problem.wiring_semantics.external_devices if package.problem.wiring_semantics else [])
            for terminal in device.terminals
            if terminal.operation_terminal_id and terminal.terminal_id in submitted_terminal_ids
        }
        runtime = _runtime_definition(request, package.problem.circuit, package.problem.operation)
        isolated = OperationEngine(
            session_id="isolated-check",
            problem_id=manual.problem_id,
            wiring_attempt_id=manual.wiring_attempt_id,
            circuit=runtime.circuit,
            definition=runtime.operation,
            connections=manual.connections,
            terminal_aliases=terminal_aliases,
            catalog_composed=runtime.catalog_composed,
            composition_warnings=runtime.warnings,
        )
        passed = True
        try:
            for step in test.get("steps", []):
                action_payload = {key: value for key, value in step.items() if key != "expect"}
                state = isolated.apply(OperationAction.model_validate(action_payload))
                if not matches_expectation(state, step.get("expect", {})):
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
    OperationRepository(request_database(request)).save_attempt(
        problem_id=manual.problem_id,
        problem_version=package.manifest.version,
        wiring_attempt_id=manual.wiring_attempt_id,
        result=result,
        fault_codes=all_fault_codes,
    )
    return result


def _requirement_value(state: OperationSessionState, path: str):
    value = state.model_dump(mode="json")
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(path)
        value = value[part]
    return value


@session_router.post("/{session_id}/run-requirements", response_model=BehaviorRequirementResult)
def run_behavior_requirements(session_id: str, request: Request):
    manual = _engine(request, session_id)
    requirements = manual.definition.requirements
    if not requirements:
        raise HTTPException(status_code=409, detail="공개 동작 요구사항이 준비되지 않았습니다.")

    results: list[BehaviorRequirementItem] = []
    for requirement in requirements:
        isolated = OperationEngine(
            session_id=f"requirement:{requirement.requirement_id}",
            problem_id=manual.problem_id,
            wiring_attempt_id=manual.wiring_attempt_id,
            circuit=manual.circuit,
            definition=manual.definition,
            connections=manual.connections,
            terminal_aliases=manual.terminal_aliases,
            catalog_composed=manual.catalog_composed,
            session_type="practice_preview_session",
            workspace_id=manual.workspace_id,
            gradable=False,
            safety_status=manual.safety_status,
            power_permitted=manual.power_permitted,
            safety_issues=manual.safety_issues,
        )
        status = "satisfied"
        message = "공개 요구 동작이 확인되었습니다."
        try:
            if not manual.power_permitted:
                raise PermissionError
            state = isolated.state()
            observed_states = [state]
            for action in requirement.actions:
                state = isolated.apply(action)
                observed_states.append(state)
            mismatches = [
                item.path
                for item in requirement.expectations
                if _requirement_value(state, item.path) != item.expected
            ]
            mismatches.extend(
                item.path
                for item in requirement.observations
                if not any(
                    _requirement_value(observed, item.path) == item.expected
                    for observed in observed_states
                )
            )
            if mismatches:
                status = "unsatisfied"
                message = "현재 결선에서는 요구된 동작 상태가 형성되지 않았습니다."
        except PermissionError:
            status = "unavailable"
            message = "안전 검사로 전원 투입이 차단되어 동작을 확인할 수 없습니다."
        except (KeyError, ValueError, SimulationDefinitionError):
            status = "unsatisfied"
            message = "현재 결선에서는 시험 순서를 완료할 수 없습니다."
        results.append(BehaviorRequirementItem(
            requirement_id=requirement.requirement_id,
            label=requirement.label,
            status=status,
            message=message,
        ))
    result_by_id = {item.requirement_id: item for item in results}
    grouped_requirements: dict[str, list] = {}
    for requirement in requirements:
        if requirement.scenario_id:
            grouped_requirements.setdefault(requirement.scenario_id, []).append(requirement)

    scenarios: list[BehaviorScenarioItem] = []
    for scenario_id, grouped in grouped_requirements.items():
        grouped_results = [result_by_id[item.requirement_id] for item in grouped]
        missing = [
            requirement.label
            for requirement, result in zip(grouped, grouped_results)
            if result.status != "satisfied"
        ]
        if all(item.status == "satisfied" for item in grouped_results):
            scenario_status = "satisfied"
            observation = f"세부 동작 {len(grouped_results)}/{len(grouped_results)}개가 확인되었습니다."
            next_action = "시험 초기화 후 다른 요구사항을 확인할 수 있습니다."
        elif any(item.status == "unavailable" for item in grouped_results):
            scenario_status = "unavailable"
            observation = "안전 검사로 전원 투입이 차단되어 현재 확인할 수 없습니다."
            next_action = "결선 화면에서 안전 경고를 먼저 해결하세요."
        else:
            scenario_status = "unsatisfied"
            satisfied_count = sum(item.status == "satisfied" for item in grouped_results)
            observation = f"세부 동작 {satisfied_count}/{len(grouped_results)}개가 확인되었습니다."
            next_action = grouped[0].next_action or "결선을 확인한 뒤 이 요구사항을 다시 실행하세요."
        scenarios.append(BehaviorScenarioItem(
            scenario_id=scenario_id,
            label=grouped[0].scenario_label or scenario_id,
            status=scenario_status,
            current_observation=observation,
            missing_conditions=missing,
            next_action=next_action,
        ))

    return BehaviorRequirementResult(
        results=results,
        scenarios=scenarios,
        message="저장 결선의 공개 동작사항 확인을 마쳤습니다. 공식 점수나 합격 판정은 제공하지 않습니다.",
    )


@session_router.delete("/{session_id}", status_code=204)
def delete_operation_session(session_id: str, request: Request):
    try:
        request.app.state.operation_sessions.delete(session_id, request_user_id(request))
    except OperationSessionNotFound as exc:
        raise HTTPException(status_code=404, detail="동작시험 세션을 찾을 수 없습니다.") from exc
    return Response(status_code=204)


router = problem_router
