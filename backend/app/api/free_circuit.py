from __future__ import annotations

from secrets import token_urlsafe
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Request, Response

from app.core.user_context import request_database, request_user_id
from app.domain import OperationSessionState
from app.domain.free_circuit import FreeCircuitWorkspaceResponse, FreeCircuitWorkspaceUpdate
from app.repositories.free_circuit_repository import FreeCircuitRepository
from app.simulation import OperationEngine, SimulationDefinitionError


router = APIRouter(prefix="/api/free-circuits", tags=["free-circuit"])
WorkspaceId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,64}$")]


def _repository(request: Request) -> FreeCircuitRepository:
    return FreeCircuitRepository(request_database(request))


@router.get("/{workspace_id}", response_model=FreeCircuitWorkspaceResponse)
def get_workspace(workspace_id: WorkspaceId, request: Request):
    workspace = _repository(request).get(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="자유회로 작업공간을 찾을 수 없습니다.")
    return workspace


@router.put("/{workspace_id}", response_model=FreeCircuitWorkspaceResponse)
def save_workspace(workspace_id: WorkspaceId, payload: FreeCircuitWorkspaceUpdate, request: Request):
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
    try:
        engine = OperationEngine(
            session_id=session_id,
            problem_id=f"free:{workspace_id}",
            wiring_attempt_id=0,
            circuit=workspace.circuit,
            definition=workspace.operation,
            connections=workspace.connections,
        )
    except SimulationDefinitionError as exc:
        raise HTTPException(status_code=422, detail=f"자유회로 정의를 확인해 주세요. {exc}") from exc
    request.app.state.operation_sessions.add(engine, request_user_id(request))
    return engine.state()
