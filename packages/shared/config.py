"""Application configuration shared by server and all clients.

Lives in `packages/shared` so clients don't import `services/mcp_server`.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    log_level: str = "INFO"
    otel_service_name: str = "scai-mcp-admissions"

    # Database
    database_url: str = "postgresql+psycopg://scai:scai@localhost:5433/scai_admissions"

    # MCP
    mcp_server_url: str = "http://localhost:8010/mcp"
    mcp_protocol_version: str = "2026-07-28"
    mcp_port: int = 8010

    # Auth
    jwt_signing_key: str = "dev-only-do-not-use-in-production-replace-me"
    jwt_audience: str = "scai-admissions"
    jwt_issuer: str = "scai-dev"
    # Approval/quote TTLs (seconds)
    approval_ttl_seconds: int = 600
    quote_ttl_seconds: int = 3600

    # Model
    model_provider: str = "ollama"
    model_name: str = "qwen3.5:2b"
    model_base_url: str = "http://localhost:11434/v1"
    model_api_key: str = "ollama"

    # Learner host
    learner_host_port: int = 8020

    # Counsellor host
    counsellor_host_port: int = 8030

    # Demo seed contact encryption key (NOT for production; secrets belong in env)
    demo_contact_secret: str = "demo-only-contact-secret"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


__all__ = ["Settings", "get_settings", "settings"]