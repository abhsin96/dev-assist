"""Structured JSON logging via structlog.

Call `configure_logging()` once at application startup.
Use `get_logger()` everywhere else — it returns a structlog BoundLogger
that automatically picks up `trace_id`, `run_id`, and `user_id` from
context vars set by the request-id middleware.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

import structlog

# ─── Per-request context vars ────────────────────────────────────────────────
_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_run_id: ContextVar[str] = ContextVar("run_id", default="")
_user_id: ContextVar[str] = ContextVar("user_id", default="")

# Redact these header names from log output
_REDACTED_HEADERS = frozenset(
    {
        "authorization",
        "cookie",
        "x-api-key",
        "x-auth-token",
        "set-cookie",
    }
)


def set_trace_id(value: str) -> None:
    _trace_id.set(value)


def set_run_id(value: str) -> None:
    _run_id.set(value)


def set_user_id(value: str) -> None:
    _user_id.set(value)


def get_trace_id() -> str:
    return _trace_id.get()


def get_run_id() -> str:
    return _run_id.get()


def _add_context(
    logger: object, method: str, event_dict: structlog.types.EventDict
) -> structlog.types.EventDict:
    """Processor: inject per-request context vars into every log line."""
    if trace_id := _trace_id.get():
        event_dict["trace_id"] = trace_id
    if run_id := _run_id.get():
        event_dict["run_id"] = run_id
    if user_id := _user_id.get():
        event_dict["user_id"] = user_id
    return event_dict


def configure_logging(log_level: str = "INFO", json_logs: bool = True) -> None:
    """Configure structlog and stdlib logging. Call once at startup."""
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        _add_context,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level.upper())

    # Quieten noisy third-party loggers
    for name in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]
