# Auth Service

Handles **registration, login, and JWT issuance** for FairGig.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/login` | Login → JWT token |
| `GET` | `/auth/verify` | Verify token → current user |
| `GET` | `/health` | Health check |

## Running Locally

```bash
# from E:\softec26\backend
uv run uvicorn services.auth.app:app --reload --port 8001
```

Swagger UI → http://localhost:8001/docs  
ReDoc     → http://localhost:8001/redoc

## Environment

Uses `.env.local` by default. Set `ENV=prod` to switch to Supabase.
