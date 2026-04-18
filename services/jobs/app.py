"""
Jobs Service — app entry point
Runs on port 8003

Start with:
    uv run uvicorn services.jobs.app:app --reload --port 8003
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import get_settings
from services.jobs.routes import router

settings = get_settings()

app = FastAPI(
    title="FairGig — Jobs Service",
    description="""
## Job Listings & Applications

Core marketplace service for posting, browsing, and applying to jobs.

### Features
- ✅ Post a new job (authenticated)
- ✅ Browse & search jobs (paginated)
- ✅ Get job details
- ✅ Update / delete your own job
- ✅ Apply to a job
- ✅ List applicants (job owner only)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={"name": "FairGig Team", "email": "dev@fairgig.io"},
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/jobs", tags=["Jobs"])


@app.get("/health", tags=["Health"])
async def health():
    return {"service": "jobs", "status": "ok", "env": settings.ENV}
