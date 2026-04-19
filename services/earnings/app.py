import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.config import get_settings

# THIS IS THE CRITICAL LINE
from services.earnings.routes import router

settings = get_settings()

app = FastAPI(
    title="FairGig — Earnings Service",
    description="Handles shifts, verification screenshots (Cloudinary), and CSV imports.",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# THIS LINE ATTACHES THE ROUTES TO THE SERVER
app.include_router(router, tags=["Earnings"])

@app.get("/health", tags=["Health"])
async def health():
    return {"service": "earnings", "status": "ok", "env": settings.ENV}