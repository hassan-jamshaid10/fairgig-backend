"""
Centralised settings — switches between local Postgres and Supabase (prod).

Local  : set ENV=local  → uses DATABASE_URL (postgres://...)
Prod   : set ENV=prod   → uses SUPABASE_URL + SUPABASE_KEY
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

    # ── Supabase (prod) ───────────────────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""      # service_role key (backend only)
    SUPABASE_DB_URL: str = ""   # direct postgres connection string from Supabase

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
        """Return the correct DB URL based on ENV."""
        if self.ENV == "prod" and self.SUPABASE_DB_URL:
            return self.SUPABASE_DB_URL
        return self.DATABASE_URL


@lru_cache
def get_settings() -> Settings:
    return Settings()
