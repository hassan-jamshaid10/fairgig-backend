from __future__ import annotations
import socket
from collections.abc import AsyncGenerator

from sqlalchemy.engine import make_url
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


def _is_pooler_url(hostname: str) -> bool:
    return "pooler.supabase.com" in (hostname or "")


def _resolve_ipv4(hostname: str) -> str:
    """Force IPv4 resolution — asyncpg struggles with IPv6."""
    port = 6543 if _is_pooler_url(hostname) else 5432
    try:
        results = socket.getaddrinfo(hostname, port, socket.AF_INET)
        return results[0][4][0]  # first IPv4 address
    except OSError:
        return hostname


def _ensure_asyncpg_scheme(raw_url: str) -> str:
    """
    Ensure the URL uses the asyncpg driver scheme.
    Supabase / SQLAlchemy async requires 'postgresql+asyncpg://'.
    Accepts: postgresql://, postgres://, postgresql+asyncpg://
    """
    for prefix in ("postgresql+asyncpg://", "postgres+asyncpg://"):
        if raw_url.startswith(prefix):
            return raw_url  # already correct
    for prefix in ("postgresql://", "postgres://"):
        if raw_url.startswith(prefix):
            return raw_url.replace(prefix, "postgresql+asyncpg://", 1)
    raise ValueError(f"Unrecognised DB URL scheme: {raw_url!r}")


def _get_engine() -> AsyncEngine:
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()

        raw = _ensure_asyncpg_scheme(settings.active_db_url)
        url = make_url(raw)
        connect_args: dict[str, object] = {}

        if settings.ENV == "prod":
            # Supabase requires SSL — do NOT disable it.
            connect_args = {"ssl": "require", "statement_cache_size": 0}

            # Pooler hostname already resolves to IPv4.
            # Only force IPv4 for direct (non-pooler) connections.
            if url.host and not _is_pooler_url(url.host):
                ipv4 = _resolve_ipv4(url.host)
                url = url.set(host=ipv4)

        db_url = url.render_as_string(hide_password=False)

        _engine = create_async_engine(
            db_url,
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


def reset_engine() -> None:
    """
    Tear down the cached engine and session factory.
    Call this when you need to reinitialise with a different ENV
    (e.g. inside test_connection.py after switching os.environ["ENV"]).
    """
    global _engine, _session_factory
    if _engine is not None:
        # Fire-and-forget dispose; safe to call synchronously here
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_engine.dispose())
            else:
                loop.run_until_complete(_engine.dispose())
        except RuntimeError:
            pass
    _engine = None
    _session_factory = None


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    _get_engine()
    if _session_factory is None:
        raise RuntimeError("Database session factory not initialized")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()