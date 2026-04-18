# Jobs Service

Core marketplace service for **posting, browsing, and applying to gigs**.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/jobs/` | ❌ | Browse jobs (paginated, filter by status) |
| `POST` | `/jobs/` | ✅ JWT | Post a new job |
| `GET` | `/jobs/{id}` | ❌ | Get job details |
| `PATCH` | `/jobs/{id}` | ✅ JWT | Update job (owner only) |
| `DELETE` | `/jobs/{id}` | ✅ JWT | Delete job (owner only) |
| `POST` | `/jobs/{id}/apply` | ✅ JWT | Apply to a job |
| `GET` | `/jobs/{id}/applicants` | ✅ JWT | List applicants (owner only) |
| `GET` | `/health` | ❌ | Health check |

## Running Locally

```bash
# from E:\softec26\backend
uv run uvicorn services.jobs.app:app --reload --port 8003
```

Swagger UI → http://localhost:8003/docs  
ReDoc     → http://localhost:8003/redoc

## Environment

Uses `.env.local` by default. Set `ENV=prod` to switch to Supabase.
