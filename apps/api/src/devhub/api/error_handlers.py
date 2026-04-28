"""Centralised RFC 7807 error handlers for the FastAPI application."""

from __future__ import annotations

import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from devhub.core.errors import DevHubError, ErrorCode
from devhub.core.logging import get_logger, get_trace_id

logger = get_logger(__name__)

_PROBLEM_MEDIA_TYPE = "application/problem+json"
_ERROR_TYPE_BASE = "https://devhub.ai/errors"


def _problem(
    *,
    status: int,
    code: str,
    title: str,
    detail: str,
    instance: str,
    trace_id: str,
    retry_after: int | None = None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    body: dict[str, object] = {
        "type": f"{_ERROR_TYPE_BASE}/{code}",
        "title": title,
        "status": status,
        "code": code,
        "detail": detail,
        "instance": instance,
        "traceId": trace_id,
    }
    if retry_after is not None:
        body["retryAfter"] = retry_after
    if extra:
        body.update(extra)
    return body


def register_error_handlers(app: FastAPI) -> None:
    """Attach all exception handlers to *app*."""

    @app.exception_handler(DevHubError)
    async def devhub_error_handler(request: Request, exc: DevHubError) -> JSONResponse:
        trace_id = get_trace_id()
        logger.warning(
            "devhub.error",
            code=exc.code,
            status=exc.http_status,
            detail=exc.user_message,
            trace_id=trace_id,
        )
        return JSONResponse(
            status_code=exc.http_status,
            content=_problem(
                status=exc.http_status,
                code=exc.code,
                title=exc.code.replace("_", " ").title(),
                detail=exc.user_message,
                instance=str(request.url.path),
                trace_id=trace_id,
                retry_after=exc.retry_after,
            ),
            media_type=_PROBLEM_MEDIA_TYPE,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        trace_id = get_trace_id()
        errors = [
            {
                "path": ".".join(str(p) for p in e["loc"]),
                "message": e["msg"],
            }
            for e in exc.errors()
        ]
        logger.info(
            "validation.error",
            error_count=len(errors),
            trace_id=trace_id,
        )
        return JSONResponse(
            status_code=422,
            content=_problem(
                status=422,
                code=ErrorCode.VALIDATION_ERROR,
                title="Validation Error",
                detail="Request validation failed",
                instance=str(request.url.path),
                trace_id=trace_id,
                extra={"errors": errors},
            ),
            media_type=_PROBLEM_MEDIA_TYPE,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        trace_id = get_trace_id()
        logger.error(
            "unhandled.error",
            exc_type=type(exc).__name__,
            trace_id=trace_id,
            stack=traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content=_problem(
                status=500,
                code=ErrorCode.INTERNAL_ERROR,
                title="Internal Server Error",
                detail="An unexpected error occurred. Please try again later.",
                instance=str(request.url.path),
                trace_id=trace_id,
            ),
            media_type=_PROBLEM_MEDIA_TYPE,
        )
