# FairGig — Backend

> Microservice-based FastAPI backend for the FairGig freelance platform.

## Architecture

```
backend/
├── .env                    # Shared defaults (safe to commit)
├── .env.local              # Local dev — PostgreSQL  (git-ignored)
├── .env.production         # Production  — Supabase  (git-ignored)
├── pyproject.toml          # uv project + dependencies
├── Dockerfile
├── docker-compose.yml
│
├── shared/                 # Cross-service utilities
│   ├── config.py           # Pydantic Settings (env-aware)
│   ├── database.py         # Async SQLAlchemy engine + session
│   ├── supabase_client.py  # Supabase client (prod only)
│   ├── schemas.py          # Shared Pydantic schemas
│   └── security.py         # JWT sign / verify
│
└── services/
    ├── auth/               # 🔐 Auth Service  — port 8001
    │   ├── app.py
    │   ├── models.py
    │   ├── routes.py
    │   └── README.md
    ├── users/              # 👤 Users Service — port 8002
    │   ├── app.py
    │   ├── models.py
    │   ├── schemas.py
    │   ├── routes.py
    │   └── README.md
    └── jobs/               # 💼 Jobs Service  — port 8003
        ├── app.py
        ├── models.py
        ├── schemas.py
        ├── routes.py
        └── README.md
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) ≥ 0.9
- Python 3.11+
- PostgreSQL 15+ (local) **or** a Supabase project (prod)

## Quick Start (Local)

```powershell
# 1. Install dependencies (cache stored on E:\uv_cache)
cd E:\softec26\backend
uv sync

# 2. Copy local env and fill in your Postgres credentials
copy .env.local.example .env.local   # already provided as .env.local

# 3. Start services (3 separate terminals)
uv run uvicorn services.auth.app:app  --reload --port 8001
uv run uvicorn services.users.app:app --reload --port 8002
uv run uvicorn services.jobs.app:app  --reload --port 8003
```

## Swagger Docs

| Service | Swagger UI | ReDoc |
|---------|-----------|-------|
| Auth    | http://localhost:8001/docs | http://localhost:8001/redoc |
| Users   | http://localhost:8002/docs | http://localhost:8002/redoc |
| Jobs    | http://localhost:8003/docs | http://localhost:8003/redoc |

## Docker (local stack with Postgres)

```powershell
docker-compose up --build
```

## Environment Files

| File | Purpose | Committed? |
|------|---------|-----------|
| `.env` | Shared defaults (no secrets) | ✅ Yes |
| `.env.local` | Local Postgres credentials | ❌ No |
| `.env.production` | Supabase credentials | ❌ No |

## Switching Local ↔ Production

The `shared/config.py` `active_db_url` property handles this automatically:

- `ENV=local` → uses `DATABASE_URL` (local Postgres)
- `ENV=prod`  → uses `SUPABASE_DB_URL` (Supabase Postgres)

## uv Cache

Cache is stored on **E:\uv_cache** (configured in `pyproject.toml` `[tool.uv]`).
