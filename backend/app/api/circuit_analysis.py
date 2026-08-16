from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.domain import CircuitAttemptResult, CircuitAttemptSubmit, CircuitProgress, SchematicDiagram
from app.repositories import CircuitAttemptRepository, ProblemRepository
from app.services.circuit_attempt_service import CircuitAttemptService, CircuitAttemptValidationError


router = APIRouter(prefix="/api/problems", tags=["circuit-analysis"])


def _problems(request: Request) -> ProblemRepository:
    repository = getattr(request.app.state, "problem_repository", None)
    if repository is None:
        raise HTTPException(status_code=503, detail="문제 저장소를 준비할 수 없습니다.")
    return repository


def _attempts(request: Request) -> CircuitAttemptRepository:
    return CircuitAttemptRepository(request.app.state.database)


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
