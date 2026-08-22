from __future__ import annotations

from secrets import token_urlsafe
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Path, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.user_context import request_database, request_user_id
from app.domain import OperationSessionState
from app.domain.free_circuit import (
    FreeCircuitEditorState,
    FreeCircuitTemplate,
    FreeCircuitWorkspaceResponse,
    FreeCircuitWorkspaceSummary,
    FreeCircuitWorkspaceUpdate,
)
from app.repositories.free_circuit_repository import FreeCircuitRepository
from app.simulation import OperationEngine, SimulationDefinitionError


router = APIRouter(prefix="/api/free-circuits", tags=["free-circuit"])
WorkspaceId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
TEMPLATE_IDS = (
    "operation_demo_001",
    "forward_reverse_interlock_demo_001",
    "eocr_sequence_demo_001",
)


class CreateFromTemplateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("작업공간 이름을 입력해 주세요.")
        return normalized


class FreeCircuitDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid")
    severity: str
    code: str
    message: str


class FreeCircuitDiagnosticsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    diagnostics: list[FreeCircuitDiagnostic]


def _repository(request: Request) -> FreeCircuitRepository:
    return FreeCircuitRepository(request_database(request))


def _template(request: Request, template_id: str) -> FreeCircuitTemplate:
    if template_id not in TEMPLATE_IDS:
        raise HTTPException(status_code=404, detail="자유회로 시작 템플릿을 찾을 수 없습니다.")
    package = request.app.state.problem_repository._get_package_internal(template_id)
    if package is None or package.board is None or package.problem.operation is None:
        raise HTTPException(status_code=409, detail="자유회로 시작 템플릿이 준비되지 않았습니다.")
    descriptions = {
        "operation_demo_001": "자기유지·릴레이·타이머·표시등·모터 기초 실험",
        "forward_reverse_interlock_demo_001": "정·역회전 자기유지와 전기·기계 인터록 실험",
        "eocr_sequence_demo_001": "EOCR 과부하 트립·복귀와 모터 보호 실험",
    }
    return FreeCircuitTemplate(
        template_id=template_id,
        name=package.manifest.title.replace("연습", "실험 보드"),
        description=descriptions[template_id],
        board=package.board,
        circuit=package.problem.circuit,
        operation=package.problem.operation,
        device_layout=package.problem.device_layout,
        wiring_semantics=package.problem.wiring_semantics,
    )


def _workspace_from_template(template: FreeCircuitTemplate, name: str) -> FreeCircuitWorkspaceUpdate:
    return FreeCircuitWorkspaceUpdate(
        name=name,
        circuit=template.circuit,
        operation=template.operation,
        connections=[],
        board=template.board,
        device_layout=template.device_layout,
        wiring_semantics=template.wiring_semantics,
        editor=FreeCircuitEditorState(template_id=template.template_id),
    )


def _new_workspace_id(repository: FreeCircuitRepository) -> str:
    for _ in range(16):
        workspace_id = f"fc_{token_urlsafe(12)}"
        if repository.get(workspace_id) is None:
            return workspace_id
    raise HTTPException(status_code=503, detail="새 작업공간 ID를 생성할 수 없습니다. 잠시 후 다시 시도해 주세요.")


def _validate_workspace(workspace: FreeCircuitWorkspaceUpdate) -> None:
    if workspace.board is None:
        return
    board_pins = {pin.terminal_id: pin for item in workspace.board.items for pin in item.pins}
    external_ids = {
        terminal.terminal_id
        for device in (workspace.wiring_semantics.external_devices if workspace.wiring_semantics else [])
        for terminal in device.terminals
    }
    known = set(board_pins) | external_ids
    seen: set[tuple[str, str]] = set()
    total_counts: dict[str, int] = {}
    bank_counts: dict[tuple[str, str], int] = {}
    for connection in workspace.connections:
        left, right = connection.from_terminal, connection.to
        if left not in known or right not in known:
            missing = left if left not in known else right
            raise HTTPException(status_code=422, detail=f"존재하지 않는 자유회로 단자입니다: {missing}")
        if left == right:
            raise HTTPException(status_code=422, detail="같은 단자끼리는 연결할 수 없습니다.")
        key = tuple(sorted((left, right)))
        if key in seen:
            raise HTTPException(status_code=422, detail=f"중복 전선이 있습니다: {left} - {right}")
        seen.add(key)
        for terminal_id, other in ((left, right), (right, left)):
            pin = board_pins.get(terminal_id)
            free = bool(pin and (pin.terminal_role == "free_junction" or terminal_id.startswith(("TB5-", "TB6-"))))
            if free:
                bank = "external" if other in external_ids else "internal"
                bank_key = (terminal_id, bank)
                bank_counts[bank_key] = bank_counts.get(bank_key, 0) + 1
                maximum = pin.max_connections
                if bank_counts[bank_key] > maximum:
                    side = "외부측" if bank == "external" else "내부측"
                    raise HTTPException(status_code=422, detail=f"{terminal_id} {side} 연결은 최대 {maximum}가닥입니다.")
            else:
                total_counts[terminal_id] = total_counts.get(terminal_id, 0) + 1
                maximum = pin.max_connections if pin else next(
                    terminal.max_connections
                    for device in workspace.wiring_semantics.external_devices
                    for terminal in device.terminals
                    if terminal.terminal_id == terminal_id
                )
                if total_counts[terminal_id] > maximum:
                    raise HTTPException(status_code=422, detail=f"{terminal_id} 연결은 최대 {maximum}가닥입니다.")


@router.get("", response_model=list[FreeCircuitWorkspaceSummary])
def list_workspaces(request: Request):
    return _repository(request).list()


@router.get("/templates", response_model=list[FreeCircuitTemplate])
def list_templates(request: Request):
    templates: list[FreeCircuitTemplate] = []
    for template_id in TEMPLATE_IDS:
        package = request.app.state.problem_repository._get_package_internal(template_id)
        if package is not None and package.board is not None and package.problem.operation is not None:
            templates.append(_template(request, template_id))
    return templates


@router.post("/templates/{template_id}/workspaces/{workspace_id}", response_model=FreeCircuitWorkspaceResponse, status_code=201)
def create_from_template_with_id(
    template_id: str,
    workspace_id: WorkspaceId,
    request: Request,
    payload: CreateFromTemplateRequest = Body(...),
):
    template = _template(request, template_id)
    repository = _repository(request)
    if repository.get(workspace_id) is not None:
        raise HTTPException(status_code=409, detail="같은 ID의 자유회로 작업공간이 이미 있습니다.")
    return repository.save(workspace_id, _workspace_from_template(template, payload.name))


@router.post("/templates/{template_id}/workspaces", response_model=FreeCircuitWorkspaceResponse, status_code=201)
def create_from_template(template_id: str, request: Request, payload: CreateFromTemplateRequest = Body(...)):
    template = _template(request, template_id)
    repository = _repository(request)
    workspace_id = _new_workspace_id(repository)
    return repository.save(workspace_id, _workspace_from_template(template, payload.name))


@router.get("/{workspace_id}", response_model=FreeCircuitWorkspaceResponse)
def get_workspace(workspace_id: WorkspaceId, request: Request):
    workspace = _repository(request).get(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="자유회로 작업공간을 찾을 수 없습니다.")
    return workspace


@router.put("/{workspace_id}", response_model=FreeCircuitWorkspaceResponse)
def save_workspace(workspace_id: WorkspaceId, payload: FreeCircuitWorkspaceUpdate, request: Request):
    _validate_workspace(payload)
    return _repository(request).save(workspace_id, payload)


@router.delete("/{workspace_id}", status_code=204)
def delete_workspace(workspace_id: WorkspaceId, request: Request):
    _repository(request).delete(workspace_id)
    return Response(status_code=204)


@router.post("/{workspace_id}/sessions", response_model=OperationSessionState, status_code=201)
def create_free_circuit_session(workspace_id: WorkspaceId, request: Request):
    workspace = _repository(request).get(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="자유회로 작업공간을 찾을 수 없습니다.")
    session_id = token_urlsafe(24)
    submitted_terminal_ids = {
        terminal_id
        for item in workspace.connections
        for terminal_id in (item.from_terminal, item.to)
    }
    terminal_aliases = {
        terminal.operation_terminal_id: terminal.terminal_id
        for device in (workspace.wiring_semantics.external_devices if workspace.wiring_semantics else [])
        for terminal in device.terminals
        if terminal.operation_terminal_id and terminal.terminal_id in submitted_terminal_ids
    }
    try:
        engine = OperationEngine(
            session_id=session_id,
            problem_id=f"free:{workspace_id}",
            wiring_attempt_id=0,
            circuit=workspace.circuit,
            definition=workspace.operation,
            connections=workspace.connections,
            terminal_aliases=terminal_aliases,
        )
    except SimulationDefinitionError as exc:
        raise HTTPException(status_code=422, detail=f"자유회로 정의를 확인해 주세요. {exc}") from exc
    request.app.state.operation_sessions.add(engine, request_user_id(request))
    return engine.state()


@router.get("/{workspace_id}/diagnostics", response_model=FreeCircuitDiagnosticsResponse)
def get_diagnostics(workspace_id: WorkspaceId, request: Request):
    workspace = _repository(request).get(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="자유회로 작업공간을 찾을 수 없습니다.")
    diagnostics: list[FreeCircuitDiagnostic] = []
    if not workspace.connections:
        diagnostics.append(FreeCircuitDiagnostic(severity="warning", code="empty_wiring", message="아직 연결된 전선이 없습니다."))
    connected = {item.from_terminal for item in workspace.connections} | {item.to for item in workspace.connections}
    for coil in workspace.circuit.coils:
        if coil.terminal_a_id not in connected or coil.terminal_b_id not in connected:
            diagnostics.append(FreeCircuitDiagnostic(
                severity="info", code=f"open_coil:{coil.coil_id}",
                message=f"{coil.coil_id} 코일의 전원 경로가 아직 완성되지 않았을 수 있습니다.",
            ))
    try:
        engine = OperationEngine(
            session_id="diagnostic", problem_id=f"free:{workspace_id}", wiring_attempt_id=0,
            circuit=workspace.circuit, definition=workspace.operation, connections=workspace.connections,
        )
        diagnostics.extend(FreeCircuitDiagnostic(
            severity=fault.severity, code=fault.code,
            message=fault.message.replace("감지되었습니다", "가능성이 확인되었습니다"),
        ) for fault in engine.faults)
    except SimulationDefinitionError as exc:
        diagnostics.append(FreeCircuitDiagnostic(severity="error", code="invalid_definition", message=str(exc)))
    status = "normal" if not diagnostics else "attention"
    return FreeCircuitDiagnosticsResponse(status=status, diagnostics=diagnostics)
