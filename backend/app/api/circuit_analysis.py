from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from app.domain import CircuitAnalysisDraftResponse, CircuitAnalysisDraftUpdate, CircuitAttemptResult, CircuitAttemptSubmit, CircuitProgress, SchematicDiagram
from app.repositories import CircuitAnalysisDraftRepository, CircuitAttemptRepository, ProblemRepository
from app.services.circuit_attempt_service import CircuitAttemptService, CircuitAttemptValidationError
from app.core.user_context import request_database


router = APIRouter(prefix="/api/problems", tags=["circuit-analysis"])


def _problems(request: Request) -> ProblemRepository:
    repository = getattr(request.app.state, "problem_repository", None)
    if repository is None:
        raise HTTPException(status_code=503, detail="문제 저장소를 준비할 수 없습니다.")
    return repository


def _attempts(request: Request) -> CircuitAttemptRepository:
    return CircuitAttemptRepository(request_database(request))


def _drafts(request: Request) -> CircuitAnalysisDraftRepository:
    return CircuitAnalysisDraftRepository(request_database(request))


def _problem(problem_id: str, request: Request):
    package = _problems(request)._get_package_internal(problem_id)
    if package is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    return package


@router.get("/{problem_id}/diagram", response_model=SchematicDiagram)
def get_diagram(problem_id: str, request: Request) -> SchematicDiagram:
    diagram = _problems(request).get_diagram(problem_id)
    if diagram is None:
        raise HTTPException(status_code=404, detail="회로도를 찾을 수 없습니다.")
    return diagram


@router.post("/{problem_id}/circuit-attempts/submit", response_model=CircuitAttemptResult)
def submit_attempt(problem_id: str, submission: CircuitAttemptSubmit, request: Request):
    try:
        return CircuitAttemptService(_problems(request), _attempts(request)).submit(problem_id, submission)
    except CircuitAttemptValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.get("/{problem_id}/circuit-progress", response_model=CircuitProgress)
def get_progress(problem_id: str, request: Request) -> CircuitProgress:
    if _problems(request)._get_package_internal(problem_id) is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    return _attempts(request).progress(problem_id)


@router.get("/{problem_id}/analysis-draft", response_model=CircuitAnalysisDraftResponse | None)
def get_analysis_draft(problem_id: str, request: Request):
    _problem(problem_id, request)
    return _drafts(request).get(problem_id)


@router.put("/{problem_id}/analysis-draft", response_model=CircuitAnalysisDraftResponse)
def save_analysis_draft(problem_id: str, draft: CircuitAnalysisDraftUpdate, request: Request):
    package = _problem(problem_id, request)
    if package.manifest.version != draft.problem_version:
        raise HTTPException(status_code=409, detail="문제 버전이 변경되었습니다. 분석 메모를 다시 확인해 주세요.")
    return _drafts(request).save(problem_id, draft)


@router.delete("/{problem_id}/analysis-draft", status_code=204)
def delete_analysis_draft(problem_id: str, request: Request):
    _problem(problem_id, request)
    _drafts(request).delete(problem_id)
    return Response(status_code=204)
