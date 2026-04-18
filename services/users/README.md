# Users Service

Manages **public user profiles, skills, and ratings** for FairGig.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/users/` | ❌ | List all profiles (paginated) |
| `GET` | `/users/me` | ✅ JWT | Get my profile |
| `PATCH` | `/users/me` | ✅ JWT | Update my profile |
| `GET` | `/users/{user_id}` | ❌ | Get any user's public profile |
| `GET` | `/health` | ❌ | Health check |

## Running Locally

```bash
# from E:\softec26\backend
uv run uvicorn services.users.app:app --reload --port 8002
```

Swagger UI → http://localhost:8002/docs  
ReDoc     → http://localhost:8002/redoc

## Environment

Uses `.env.local` by default. Set `ENV=prod` to switch to Supabase.
