from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse

from app.domain import CircuitSummary, ProblemSummary, PublicProblemDetail
from app.repositories import ProblemRepository, ReloadStatistics


router = APIRouter(prefix="/api/problems", tags=["problems"])


def _repository(request: Request) -> ProblemRepository:
    repository = getattr(request.app.state, "problem_repository", None)
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="문제 저장소를 준비할 수 없습니다.",
        )
    return repository


@router.get("", response_model=list[ProblemSummary])
def list_problems(request: Request) -> list[ProblemSummary]:
    return _repository(request).list_summaries()


@router.post("/reload", response_model=ReloadStatistics)
def reload_problems(request: Request) -> ReloadStatistics:
    return _repository(request).reload()


@router.get("/{problem_id}/circuit-summary", response_model=CircuitSummary)
def get_circuit_summary(problem_id: str, request: Request) -> CircuitSummary:
    summary = _repository(request).get_circuit_summary(problem_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    return summary


@router.get("/{problem_id}/schematic", response_class=FileResponse)
def get_schematic(problem_id: str, request: Request):
    schematic = _repository(request).get_schematic_path(problem_id)
    if schematic is None:
        raise HTTPException(status_code=404, detail="회로도 원본을 찾을 수 없습니다.")
    return FileResponse(schematic, media_type="image/svg+xml")


@router.get("/{problem_id}", response_model=PublicProblemDetail)
def get_problem(problem_id: str, request: Request) -> PublicProblemDetail:
    problem = _repository(request).get_public(problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    return problem
