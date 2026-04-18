"""
Users Service — app entry point
Runs on port 8002

Start with:
    uv run uvicorn services.users.app:app --reload --port 8002
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import get_settings
from services.users.routes import router

settings = get_settings()

app = FastAPI(
    title="FairGig — Users Service",
    description="""
## User Profile Management

Manages public user profiles, skills, and ratings.

### Features
- ✅ Get / update your own profile
- ✅ List all users (paginated)
- ✅ Get any user's public profile
- ✅ Update skills & bio
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

app.include_router(router, prefix="/users", tags=["Users"])


@app.get("/health", tags=["Health"])
async def health():
    return {"service": "users", "status": "ok", "env": settings.ENV}
