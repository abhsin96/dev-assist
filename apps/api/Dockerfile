# ── Build stage ───────────────────────────────────────────────────────────────
# Install all dependencies + the project as a non-editable wheel so the runtime
# stage only needs the finished .venv — no uv, no source tree.
FROM python:3.12-slim AS builder

WORKDIR /build

COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Deps layer (cached unless pyproject.toml / uv.lock change)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Project layer (README.md required by pyproject.toml)
COPY README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /build/.venv /app/.venv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')"

CMD ["uvicorn", "devhub.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--access-log"]
