"""FastAPI middleware: X-Request-Id injection and structured log context."""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from devhub.core.logging import get_logger, set_trace_id

logger = get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-Id"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assign a unique trace_id to every request.

    - Accepts an existing ``X-Request-Id`` from the client (useful for
      end-to-end tracing from the frontend).
    - Generates a new UUID if the header is absent.
    - Stores the id in the ``trace_id`` context var so structlog picks it up.
    - Echoes it back in the response header so the frontend can correlate.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        trace_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        set_trace_id(trace_id)

        logger.debug("request.start", method=request.method, path=request.url.path)

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = trace_id

        logger.debug(
            "request.end",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )
        return response
