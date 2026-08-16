from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from app.domain import (
    MountingAttemptResult, MountingAttemptSubmit, MountingDefinition,
    MountingDraftResponse, MountingDraftUpdate, MountingProgress,
)
from app.repositories import ProblemRepository
from app.repositories.mounting_repository import MountingRepository
from app.services.mounting_service import MountingService, MountingValidationError


# 0.6.0 이전 클라이언트의 데이터 호환을 위해 유지한다. 새 UI에서는 사용하지 않는다.
router = APIRouter(prefix="/api/problems", tags=["mounting-deprecated"], deprecated=True)


def _problems(request: Request) -> ProblemRepository:
    repository = getattr(request.app.state, "problem_repository", None)
    if repository is None:
        raise HTTPException(status_code=503, detail="문제 저장소를 준비할 수 없습니다.")
    return repository


def _repository(request: Request) -> MountingRepository:
    return MountingRepository(request.app.state.database)


def _raise(exc: MountingValidationError):
    raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.get("/{problem_id}/mounting", response_model=MountingDefinition | None)
def get_mounting(problem_id: str, request: Request):
    package = _problems(request)._get_package_internal(problem_id)
    if package is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    return package.problem.mounting


@router.get("/{problem_id}/mounting-draft", response_model=MountingDraftResponse | None)
def get_draft(problem_id: str, request: Request):
    if _problems(request)._get_package_internal(problem_id) is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    return _repository(request).get_draft(problem_id)


@router.put("/{problem_id}/mounting-draft", response_model=MountingDraftResponse)
def save_draft(problem_id: str, draft: MountingDraftUpdate, request: Request):
    try:
        return MountingService(_problems(request), _repository(request)).save_draft(problem_id, draft)
    except MountingValidationError as exc:
        _raise(exc)


@router.delete("/{problem_id}/mounting-draft", status_code=204)
def delete_draft(problem_id: str, request: Request):
    if _problems(request)._get_package_internal(problem_id) is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    _repository(request).delete_draft(problem_id)
    return Response(status_code=204)


@router.get("/{problem_id}/mounting-progress", response_model=MountingProgress)
def get_progress(problem_id: str, request: Request):
    if _problems(request)._get_package_internal(problem_id) is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    return _repository(request).progress(problem_id)


@router.post("/{problem_id}/mounting-attempts/submit", response_model=MountingAttemptResult)
def submit(problem_id: str, submission: MountingAttemptSubmit, request: Request):
    try:
        return MountingService(_problems(request), _repository(request)).submit(problem_id, submission)
    except MountingValidationError as exc:
        _raise(exc)
