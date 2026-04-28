from fastapi import FastAPI

from devhub.core.settings import get_settings

settings = get_settings()

app = FastAPI(
    title="DevHub AI API",
    version="0.1.0",
    # Only expose OpenAPI schema in development (used by pnpm gen:types)
    openapi_url="/openapi.json" if settings.app_env == "development" else None,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
