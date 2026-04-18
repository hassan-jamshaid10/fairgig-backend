import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.append(str(ROOT))

os.environ["ENV"] = "prod"

SCHEMA_SQL = """
-- UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Schemas
CREATE SCHEMA IF NOT EXISTS auth_svc;
CREATE SCHEMA IF NOT EXISTS earnings_svc;
CREATE SCHEMA IF NOT EXISTS grievance_svc;

-- auth_svc.users
CREATE TABLE IF NOT EXISTS auth_svc.users (
    id              UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255)  NOT NULL UNIQUE,
    password_hash   TEXT          NOT NULL,
    full_name       VARCHAR(255)  NOT NULL,
    phone           VARCHAR(30),
    city_zone       VARCHAR(100),
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- auth_svc.roles
CREATE TABLE IF NOT EXISTS auth_svc.roles (
    id   UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO auth_svc.roles (name)
VALUES ('Worker'), ('Verifier'), ('Advocate')
ON CONFLICT (name) DO NOTHING;

-- auth_svc.user_roles
CREATE TABLE IF NOT EXISTS auth_svc.user_roles (
    user_id UUID NOT NULL REFERENCES auth_svc.users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES auth_svc.roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- earnings_svc.shifts
CREATE TABLE IF NOT EXISTS earnings_svc.shifts (
    id                   UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id            UUID          NOT NULL REFERENCES auth_svc.users(id) ON DELETE CASCADE,
    platform             VARCHAR(100)  NOT NULL,
    shift_date           DATE          NOT NULL,
    hours_worked         NUMERIC(6,2)  NOT NULL CHECK (hours_worked > 0),
    gross_earned         NUMERIC(10,2) NOT NULL CHECK (gross_earned >= 0),
    platform_deductions  NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (platform_deductions >= 0),
    net_received         NUMERIC(10,2) NOT NULL CHECK (net_received >= 0),
    created_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- earnings_svc.screenshots
CREATE TABLE IF NOT EXISTS earnings_svc.screenshots (
    id           UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    shift_id     UUID        NOT NULL REFERENCES earnings_svc.shifts(id) ON DELETE CASCADE,
    verifier_id  UUID        REFERENCES auth_svc.users(id) ON DELETE SET NULL,
    image_url    TEXT        NOT NULL,
    status       VARCHAR(20) NOT NULL DEFAULT 'Pending'
                     CHECK (status IN ('Pending', 'Confirmed', 'Flagged', 'Unverifiable')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- grievance_svc.grievances
CREATE TABLE IF NOT EXISTS grievance_svc.grievances (
    id           UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id    UUID         NOT NULL REFERENCES auth_svc.users(id) ON DELETE CASCADE,
    platform     VARCHAR(100) NOT NULL,
    category     VARCHAR(100) NOT NULL,
    description  TEXT         NOT NULL,
    status       VARCHAR(50)  NOT NULL DEFAULT 'Open',
    is_anonymous BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- grievance_svc.grievance_comments
CREATE TABLE IF NOT EXISTS grievance_svc.grievance_comments (
    id           UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    grievance_id UUID        NOT NULL REFERENCES grievance_svc.grievances(id) ON DELETE CASCADE,
    worker_id    UUID        NOT NULL REFERENCES auth_svc.users(id) ON DELETE CASCADE,
    comment_text TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- grievance_svc.grievance_tags
CREATE TABLE IF NOT EXISTS grievance_svc.grievance_tags (
    id           UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    grievance_id UUID        NOT NULL REFERENCES grievance_svc.grievances(id) ON DELETE CASCADE,
    tag_name     VARCHAR(50) NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- View: earnings_svc.anonymized_shifts
CREATE OR REPLACE VIEW earnings_svc.anonymized_shifts AS
SELECT
    s.city_zone,
    sh.platform,
    sh.shift_date,
    sh.hours_worked,
    sh.gross_earned,
    sh.platform_deductions,
    sh.net_received
FROM earnings_svc.shifts sh
JOIN auth_svc.users       s ON s.id = sh.worker_id;
"""


async def run() -> None:
    from shared.config import get_settings
    from shared.database import _get_engine, reset_engine

    get_settings.cache_clear()
    reset_engine()

    # Ensure statement_cache_size=0 is in connect_args before engine is built.
    # (reset_engine() above cleared any previously cached engine.)
    print("Running schema on Supabase (prod)...")
    engine = _get_engine()

    from sqlalchemy import text

    # Split on semicolons, run each statement individually
    # (transaction pooler doesn't support multi-statement queries)
    statements = [s.strip() for s in SCHEMA_SQL.split(";") if s.strip()]

    async with engine.begin() as conn:
        for stmt in statements:
            await conn.execute(text(stmt))

    print(f"\n✓ Schema applied — {len(statements)} statements executed.")

    # Verify tables
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema IN ('auth_svc', 'earnings_svc', 'grievance_svc')
            ORDER BY table_schema, table_name
        """))
        rows = result.fetchall()
        print(f"\n{len(rows)} tables/views found:")
        for schema, table in rows:
            print(f"  {schema}.{table}")


if __name__ == "__main__":
    asyncio.run(run())