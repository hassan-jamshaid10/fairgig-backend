import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.append(str(ROOT))


def _set_env(env: str) -> None:
    os.environ["ENV"] = env


async def test_connection(env: str) -> None:
    _set_env(env)

    # Clear ALL caches before importing so modules pick up the new ENV value.
    from shared.config import get_settings
    get_settings.cache_clear()

    # Reset the engine so it is rebuilt with the fresh settings.
    # Import database lazily so the module re-reads os.environ["ENV"].
    from shared import database as db_module
    db_module.reset_engine()

    from sqlalchemy import text
    from sqlalchemy.engine import make_url

    settings = get_settings()

    url = make_url(settings.active_db_url)
    host = url.host or "unknown"
    port = url.port or 5432

    print("\nTesting database connection")
    print(f"  ENV  : {settings.ENV}")
    print(f"  Host : {host}:{port}")

    try:
        engine = db_module._get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar() or ""
            print(f"\nConnected. PostgreSQL: {version[:60]}")
    except Exception as exc:
        print(f"\nConnection failed: {exc}")
        return

    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    """
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_schema IN ('auth_svc', 'earnings_svc', 'grievance_svc')
                    ORDER BY table_schema, table_name
                    """
                )
            )
            rows = result.fetchall()
            if rows:
                print(f"\n{len(rows)} tables found:")
                for schema, table in rows:
                    print(f"  {schema}.{table}")
            else:
                print("\nNo tables found in auth_svc / earnings_svc / grievance_svc.")
                print("Run schema.sql on the target DB if this is unexpected.")
    except Exception as exc:
        print(f"\nSchema check failed: {exc}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test DB connectivity.")
    parser.add_argument(
        "--env",
        default=os.getenv("ENV", "prod"),
        help="Environment to test: local | prod (default: prod)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(test_connection(args.env))