from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.domain import (
    BoardDefinition, WiringAttemptResult, WiringAttemptSubmit, WiringCaptureDraftResponse,
    WiringCaptureExport, WiringCaptureImport, WiringCaptureUpdate, WiringDraftResponse,
    WiringDraftUpdate, WiringProgress, WiringSnapshotCreate, WiringSnapshotResponse,
    WiringWorkspaceCreate, WiringWorkspaceSummary,
)
from app.repositories import PracticeWiringRepository, ProblemRepository
from app.repositories.wiring_repository import WiringRepository
from app.services.wiring_service import WiringService, WiringValidationError
from app.core.user_context import request_database
from app.services import WiringCaptureService


router = APIRouter(prefix="/api/problems", tags=["wiring"])


def _problems(request: Request) -> ProblemRepository:
    repository = getattr(request.app.state, "problem_repository", None)
    if repository is None:
        raise HTTPException(status_code=503, detail="문제 저장소를 준비할 수 없습니다.")
    return repository


def _repository(request: Request) -> WiringRepository:
    return WiringRepository(request_database(request))


def _raise(exc: WiringValidationError):
    raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.get("/{problem_id}/board", response_model=BoardDefinition)
def get_board(problem_id: str, request: Request):
    capabilities = _problems(request).get_capabilities(problem_id)
    if capabilities is not None and not capabilities.board_visible:
        raise HTTPException(status_code=409, detail="이 문제의 제어함은 아직 공개되지 않았습니다.")
    board = _problems(request).get_board(problem_id)
    if board is None:
        raise HTTPException(status_code=404, detail="이 문제의 제어함 배치를 찾을 수 없습니다.")
    return board


@router.get("/{problem_id}/wiring-draft", response_model=WiringDraftResponse | None)
def get_draft(problem_id: str, request: Request):
    if _problems(request)._get_package_internal(problem_id) is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    return _repository(request).get_draft(problem_id)


@router.put("/{problem_id}/wiring-draft", response_model=WiringDraftResponse)
def save_draft(problem_id: str, draft: WiringDraftUpdate, request: Request):
    try:
        return WiringService(_problems(request), _repository(request)).save_draft(problem_id, draft)
    except WiringValidationError as exc:
        _raise(exc)


@router.delete("/{problem_id}/wiring-draft", status_code=204)
def delete_draft(problem_id: str, request: Request):
    if _problems(request)._get_package_internal(problem_id) is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    _repository(request).delete_draft(problem_id)
    return Response(status_code=204)


@router.post("/{problem_id}/wiring-attempts/submit", response_model=WiringAttemptResult)
def submit_wiring(problem_id: str, submission: WiringAttemptSubmit, request: Request):
    package = _problems(request)._get_package_internal(problem_id)
    capabilities = _problems(request).get_capabilities(problem_id)
    if package is not None and package.manifest.capabilities is not None and capabilities is not None and not capabilities.wiring_gradable:
        raise HTTPException(status_code=409, detail="이 문제는 연습 전용이며 결선 채점을 제공하지 않습니다.")
    try:
        return WiringService(_problems(request), _repository(request)).submit(problem_id, submission)
    except WiringValidationError as exc:
        _raise(exc)


@router.get("/{problem_id}/wiring-progress", response_model=WiringProgress)
def get_progress(problem_id: str, request: Request):
    if _problems(request)._get_package_internal(problem_id) is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    return _repository(request).progress(problem_id)


def _practice(problem_id: str, workspace_id: str, request: Request):
    package = _problems(request)._get_package_internal(problem_id)
    if package is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    if not _problems(request).capabilities(package).wiring_editable:
        raise HTTPException(status_code=409, detail="이 문제는 연습 결선을 지원하지 않습니다.")
    repository = PracticeWiringRepository(request_database(request))
    return package, repository, repository.get_capture(problem_id, workspace_id)


@router.get("/{problem_id}/practice-drafts/{workspace_id}", response_model=WiringCaptureDraftResponse | None)
def get_practice_draft(problem_id: str, workspace_id: str, request: Request):
    return _practice(problem_id, workspace_id, request)[2]


@router.put("/{problem_id}/practice-drafts/{workspace_id}", response_model=WiringCaptureDraftResponse)
def save_practice_draft(problem_id: str, workspace_id: str, draft: WiringCaptureUpdate, request: Request):
    package, repository, _ = _practice(problem_id, workspace_id, request)
    if draft.problem_version != package.manifest.version:
        raise HTTPException(status_code=409, detail="문제 버전이 변경되었습니다. 다시 불러와 주세요.")
    warnings = WiringCaptureService().inspect(package, draft.connections)
    return repository.save_capture(problem_id, workspace_id, draft, warnings)


@router.delete("/{problem_id}/practice-drafts/{workspace_id}", status_code=204)
def delete_practice_draft(problem_id: str, workspace_id: str, request: Request):
    _, repository, _ = _practice(problem_id, workspace_id, request)
    repository.delete(problem_id, workspace_id)
    return Response(status_code=204)


@router.get("/{problem_id}/practice-workspaces", response_model=list[WiringWorkspaceSummary])
def list_practice_workspaces(problem_id: str, request: Request):
    _, repository, _ = _practice(problem_id, "__list__", request)
    return repository.list_workspaces(problem_id)


@router.post("/{problem_id}/practice-workspaces", response_model=WiringCaptureDraftResponse, status_code=201)
def create_practice_workspace(problem_id: str, payload: WiringWorkspaceCreate, request: Request):
    package, repository, _ = _practice(problem_id, "__create__", request)
    if payload.problem_version != package.manifest.version:
        raise HTTPException(status_code=409, detail="문제 버전이 변경되었습니다. 다시 불러와 주세요.")
    return repository.create_workspace(problem_id, payload.problem_version, payload.workspace_name)


@router.get("/{problem_id}/practice-drafts/{workspace_id}/snapshots", response_model=list[WiringSnapshotResponse])
def list_practice_snapshots(problem_id: str, workspace_id: str, request: Request):
    _, repository, draft = _practice(problem_id, workspace_id, request)
    if draft is None:
        raise HTTPException(status_code=404, detail="작업공간을 찾을 수 없습니다.")
    return repository.list_snapshots(problem_id, workspace_id)


@router.post("/{problem_id}/practice-drafts/{workspace_id}/snapshots", response_model=WiringSnapshotResponse, status_code=201)
def create_practice_snapshot(problem_id: str, workspace_id: str, payload: WiringSnapshotCreate, request: Request):
    _, repository, draft = _practice(problem_id, workspace_id, request)
    if draft is None:
        raise HTTPException(status_code=404, detail="작업공간을 찾을 수 없습니다.")
    return repository.create_snapshot(problem_id, workspace_id, payload.label)


@router.post("/{problem_id}/practice-drafts/{workspace_id}/snapshots/{snapshot_id}/clone", response_model=WiringCaptureDraftResponse, status_code=201)
def clone_practice_snapshot(problem_id: str, workspace_id: str, snapshot_id: str, request: Request):
    _, repository, _ = _practice(problem_id, workspace_id, request)
    clone = repository.clone_snapshot(problem_id, workspace_id, snapshot_id)
    if clone is None:
        raise HTTPException(status_code=404, detail="스냅샷을 찾을 수 없습니다.")
    return clone


@router.get("/{problem_id}/practice-drafts/{workspace_id}/export")
def export_practice_wiring(problem_id: str, workspace_id: str, request: Request, snapshot_id: str | None = None):
    _, repository, draft = _practice(problem_id, workspace_id, request)
    if draft is None:
        raise HTTPException(status_code=404, detail="작업공간을 찾을 수 없습니다.")
    source = repository.get_snapshot(problem_id, workspace_id, snapshot_id) if snapshot_id else None
    if snapshot_id and source is None:
        raise HTTPException(status_code=404, detail="스냅샷을 찾을 수 없습니다.")
    payload = WiringCaptureExport(
        problem_id=problem_id, problem_version=source.problem_version if source else draft.problem_version,
        workspace_id=workspace_id, workspace_name=draft.workspace_name,
        snapshot_id=source.snapshot_id if source else draft.latest_snapshot_id,
        created_at=source.created_at if source else draft.created_at,
        updated_at=source.created_at if source else draft.updated_at,
        connections=source.connections if source else draft.connections,
        structural_warnings=source.structural_warnings if source else draft.structural_warnings,
    )
    filename = f"{problem_id}-{workspace_id}-wiring.json".replace('"', "")
    return JSONResponse(
        payload.model_dump(by_alias=True, mode="json"),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{problem_id}/practice-imports", response_model=WiringCaptureDraftResponse, status_code=201)
def import_practice_wiring(problem_id: str, payload: WiringCaptureImport, request: Request):
    package, repository, _ = _practice(problem_id, "__import__", request)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 1_000_000:
        raise HTTPException(status_code=413, detail="가져오기 파일은 1MB 이하여야 합니다.")
    if payload.problem_id != problem_id:
        raise HTTPException(status_code=422, detail="현재 문제와 가져오기 파일의 문제 ID가 다릅니다.")
    if payload.problem_version != package.manifest.version:
        raise HTTPException(status_code=409, detail="가져오기 파일의 문제 버전이 현재 버전과 다릅니다.")
    warnings = WiringCaptureService().inspect(package, payload.connections)
    draft = repository.create_workspace(problem_id, payload.problem_version, f"가져오기 · {payload.workspace_name}")
    draft = repository.save_capture(problem_id, draft.workspace_id, WiringCaptureUpdate(
        problem_version=payload.problem_version, workspace_name=draft.workspace_name,
        connections=payload.connections,
    ), warnings)
    repository.create_snapshot(problem_id, draft.workspace_id, "가져온 원본")
    return repository.get_capture(problem_id, draft.workspace_id)
