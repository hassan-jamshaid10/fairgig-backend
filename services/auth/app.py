"""
Auth Service — app entry point
Runs on port 8001 (default)

Start with:
    uv run uvicorn services.auth.app:app --reload --port 8001
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import get_settings
from services.auth.routes import router

settings = get_settings()

app = FastAPI(
    title="FairGig — Auth Service",
    description="""
## Authentication & Authorisation

Handles user registration, login, and JWT token issuance.

### Features
- ✅ Register with email + password
- ✅ Login → returns JWT access token
- ✅ Token introspection (verify)
- ✅ Password hashing with bcrypt
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

app.include_router(router, prefix="/auth", tags=["Auth"])


@app.get("/health", tags=["Health"])
async def health():
    return {"service": "auth", "status": "ok", "env": settings.ENV}
