from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.domain import DeviceBehaviorModel, DeviceType, SocketType
from app.repositories import ProblemRepository


router = APIRouter(prefix="/api/catalog", tags=["catalog"])


def _repository(request: Request) -> ProblemRepository:
    repository = getattr(request.app.state, "problem_repository", None)
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="공통 카탈로그를 준비할 수 없습니다.",
        )
    return repository


@router.get("/socket-types", response_model=list[SocketType])
def socket_types(request: Request) -> list[SocketType]:
    return _repository(request).catalog.socket_types()


@router.get("/device-types", response_model=list[DeviceType])
def device_types(request: Request) -> list[DeviceType]:
    return _repository(request).catalog.device_types()


@router.get("/device-behaviors", response_model=list[DeviceBehaviorModel])
def device_behaviors(request: Request) -> list[DeviceBehaviorModel]:
    return _repository(request).catalog.device_behaviors()


@router.get("/device-behaviors/{model_id}", response_model=DeviceBehaviorModel)
def device_behavior(model_id: str, request: Request) -> DeviceBehaviorModel:
    model = _repository(request).catalog.get_device_behavior(model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="기구 동작 모델을 찾을 수 없습니다.")
    return model
