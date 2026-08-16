from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logging.getLogger("electrician_simulator").exception(
        "처리되지 않은 서버 오류: %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "프로그램 처리 중 오류가 발생했습니다. 로그를 확인해 주세요."
        },
    )

