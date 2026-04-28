"""Application entry point.

Boot order:
1. Load settings (reads .env)
2. Push LangSmith env vars so langchain picks them up at import time
3. Configure structlog
4. Init Sentry
5. Build FastAPI app and attach middleware
"""

from __future__ import annotations

import os

# ── 1. Settings ───────────────────────────────────────────────────────────────
from devhub.core.settings import get_settings

settings = get_settings()

# ── 2. LangSmith – must be set before any langchain import ───────────────────
if settings.langchain_tracing_v2:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project

# ── 3. Structured logging ─────────────────────────────────────────────────────
from devhub.core.logging import configure_logging, get_logger  # noqa: E402

configure_logging(
    log_level=settings.log_level,
    json_logs=settings.app_env != "development",
)

logger = get_logger(__name__)

# ── 4. Sentry ─────────────────────────────────────────────────────────────────
if settings.sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        release=settings.git_sha,
        environment=settings.app_env,
        traces_sample_rate=0.2,
        integrations=[
            StarletteIntegration(transaction_style="url"),
            FastApiIntegration(transaction_style="url"),
        ],
        # Never send secrets
        send_default_pii=False,
    )
    logger.info("sentry.initialized", release=settings.git_sha)

# ── 5. FastAPI app ────────────────────────────────────────────────────────────
from fastapi import FastAPI  # noqa: E402

from devhub.api.middleware import RequestIdMiddleware  # noqa: E402

app = FastAPI(
    title="DevHub AI API",
    version="0.1.0",
    openapi_url="/openapi.json" if settings.app_env == "development" else None,
)

app.add_middleware(RequestIdMiddleware)

logger.info(
    "app.started",
    env=settings.app_env,
    langsmith_tracing=settings.langchain_tracing_v2,
    sentry_enabled=bool(settings.sentry_dsn),
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
