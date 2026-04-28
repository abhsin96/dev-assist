from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str = Field(default="change_me")

    # Postgres
    database_url: str = Field(
        default="postgresql+asyncpg://devhub_app:devhub_app_password@localhost:5432/devhub"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # MCP servers
    mcp_github_url: str = Field(default="http://localhost:3001")
    github_token: str = Field(default="")

    # LLM
    anthropic_api_key: str = Field(default="")

    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_api_key: str = Field(default="")
    langchain_project: str = "devhub-ai"

    # Auth
    api_jwt_secret: str = Field(default="change_me_jwt_secret")

    # Sentry
    sentry_dsn: str = Field(default="")
    git_sha: str = Field(default="unknown")

    # OpenTelemetry (optional; set to enable OTLP export)
    otel_exporter_otlp_endpoint: str = Field(default="")


@lru_cache
def get_settings() -> Settings:
    return Settings()
