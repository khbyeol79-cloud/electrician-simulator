from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.domain import OperationSetupResponse
from app.repositories import ProblemRepository
from app.repositories.wiring_repository import WiringRepository


router = APIRouter(prefix="/api/problems", tags=["operation"])


def _problems(request: Request) -> ProblemRepository:
    repository = getattr(request.app.state, "problem_repository", None)
    if repository is None:
        raise HTTPException(status_code=503, detail="문제 저장소를 준비할 수 없습니다.")
    return repository


@router.get("/{problem_id}/operation-setup", response_model=OperationSetupResponse)
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
    progress = wiring_repository.progress(problem_id)
    layout = package.problem.device_layout
    wiring_exists = bool(draft and draft.connections)
    operation_ready = progress.last_overall_correct is True and layout is not None
    preview_allowed = progress.last_gradable is False and layout is not None

    if layout is None:
        message = "이 문제의 기구 배치 정보가 준비되지 않았습니다."
    elif operation_ready:
        message = "결선 확인이 완료되어 동작시험을 준비했습니다."
    elif preview_allowed:
        message = "가상 학습 문제이므로 동작시험 준비 화면만 미리 볼 수 있습니다."
    elif not wiring_exists:
        message = "저장된 결선이 없습니다. 제어함 결선부터 진행해 주세요."
    elif progress.attempt_count == 0:
        message = "결선을 제출한 뒤 동작시험을 진행해 주세요."
    else:
        message = "결선 결과를 다시 확인한 뒤 동작시험을 진행해 주세요."

    return OperationSetupResponse(
        problem_id=problem_id,
        problem_version=package.manifest.version,
        board=package.board,
        device_layout=layout,
        wiring_draft=draft,
        wiring_submission=progress,
        wiring_exists=wiring_exists,
        operation_ready=operation_ready,
        preview_allowed=preview_allowed,
        message=message,
    )
