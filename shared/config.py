"""
Centralised settings — switches between local Postgres and Supabase (prod).

Local : set ENV=local → uses DATABASE_URL (postgresql+asyncpg://...)
Prod  : set ENV=prod  → uses SUPABASE_DB_URL (direct Postgres connection string from Supabase)
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Environment ──────────────────────────────────────────────────────────
    ENV: str = "local"          # "local" | "prod"
    DEBUG: bool = True

    # ── Local Postgres ────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fairgig"

    # ── Supabase prod — direct Postgres connection string only ────────────────
    SUPABASE_DB_URL: str = ""   # e.g. postgresql+asyncpg://postgres:[pw]@db.[ref].supabase.co:5432/postgres

    # ── Auth / JWT ────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-please"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24   # 24 h

    # ── Service ports ─────────────────────────────────────────────────────────
    AUTH_PORT: int = 8001
    USERS_PORT: int = 8002
    JOBS_PORT: int = 8003
    GATEWAY_PORT: int = 8000

    @property
    def active_db_url(self) -> str:
        if self.ENV == "prod" and self.SUPABASE_DB_URL:
            return self.SUPABASE_DB_URL
        return self.DATABASE_URL


@lru_cache
def get_settings() -> Settings:
    return Settings()
