from __future__ import annotations
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase

from shared.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker | None = None


def _get_engine() -> AsyncEngine:
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()

        # SSL required for Supabase, not needed locally
        connect_args = (
            {"ssl": "require"} if settings.ENV == "prod" else {}
        )

        _engine = create_async_engine(
            settings.active_db_url,
            echo=settings.DEBUG,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            connect_args=connect_args,
        )
        _session_factory = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _engine


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    _get_engine()
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()