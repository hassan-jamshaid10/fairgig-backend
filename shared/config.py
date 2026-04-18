import os
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

# Resolve env file relative to this file's location (backend/shared/)
_BASE = Path(__file__).parent.parent          # → backend/
_ENV_NAME = os.getenv("ENV", "local")
_ENV_FILE = _BASE / (".env.production" if _ENV_NAME == "prod" else f".env.{_ENV_NAME}")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENV: str = "local"
    DEBUG: bool = True

    DATABASE_URL: str | None = None
    SUPABASE_DB_URL: str | None = None

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    AUTH_PORT: int = 8001
    USERS_PORT: int = 8002
    JOBS_PORT: int = 8003
    GATEWAY_PORT: int = 8000

    @property
    def active_db_url(self) -> str:
        url = self.SUPABASE_DB_URL if self.ENV == "prod" else self.DATABASE_URL
        if not url:
            raise RuntimeError(
                f"No database URL configured for ENV='{self.ENV}'. "
                f"Set {'SUPABASE_DB_URL' if self.ENV == 'prod' else 'DATABASE_URL'} "
                f"in {_ENV_FILE}"
            )
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()