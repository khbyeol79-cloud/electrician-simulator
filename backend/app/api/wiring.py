from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from app.domain import BoardDefinition, WiringAttemptResult, WiringAttemptSubmit, WiringDraftResponse, WiringDraftUpdate, WiringProgress
from app.repositories import ProblemRepository
from app.repositories.wiring_repository import WiringRepository
from app.services.wiring_service import WiringService, WiringValidationError
from app.core.user_context import request_database


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
    try:
        return WiringService(_problems(request), _repository(request)).submit(problem_id, submission)
    except WiringValidationError as exc:
        _raise(exc)


@router.get("/{problem_id}/wiring-progress", response_model=WiringProgress)
def get_progress(problem_id: str, request: Request):
    if _problems(request)._get_package_internal(problem_id) is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    return _repository(request).progress(problem_id)
