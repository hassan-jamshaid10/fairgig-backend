"""
Jobs routes — post, browse, apply.
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.security import decode_access_token
from services.jobs.models import ApplicationORM, JobORM
from services.jobs.schemas import (
    ApplicationCreate,
    ApplicationRead,
    JobCreate,
    JobRead,
    JobUpdate,
)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8001/auth/login")


# ── Auth dependency ───────────────────────────────────────────────────────────

async def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    from jose import JWTError
    try:
        payload = decode_access_token(token)
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")


# ── Job CRUD ──────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[JobRead],
    summary="Browse open jobs (paginated)",
)
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: str = Query("open", alias="status"),
    db: AsyncSession = Depends(get_db),
):
    """Return a paginated list of jobs. Filter by status (open / closed / in_progress)."""
    result = await db.execute(
        select(JobORM)
        .where(JobORM.status == status_filter)
        .order_by(JobORM.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.post(
    "/",
    response_model=JobRead,
    status_code=status.HTTP_201_CREATED,
    summary="Post a new job",
)
async def create_job(
    payload: JobCreate,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db),
):
    """Create a job listing. Requires authentication."""
    now = datetime.now(timezone.utc)
    job = JobORM(
        id=str(uuid.uuid4()),
        owner_id=user_id,
        title=payload.title,
        description=payload.description,
        budget=payload.budget,
        skills=payload.skills,
        status="open",
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    await db.flush()
    return job


@router.get(
    "/{job_id}",
    response_model=JobRead,
    summary="Get job details",
)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch a single job by ID."""
    result = await db.execute(select(JobORM).where(JobORM.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.patch(
    "/{job_id}",
    response_model=JobRead,
    summary="Update your job",
)
async def update_job(
    job_id: str,
    payload: JobUpdate,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db),
):
    """Update title, description, budget, skills or status. Only the owner can do this."""
    result = await db.execute(select(JobORM).where(JobORM.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not your job.")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(job, key, value)
    job.updated_at = datetime.now(timezone.utc)

    await db.flush()
    return job


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete your job",
)
async def delete_job(
    job_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a job. Only the owner can do this."""
    result = await db.execute(select(JobORM).where(JobORM.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not your job.")
    await db.delete(job)


# ── Applications ──────────────────────────────────────────────────────────────

@router.post(
    "/{job_id}/apply",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Apply to a job",
)
async def apply_to_job(
    job_id: str,
    payload: ApplicationCreate,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db),
):
    """Submit an application. Cannot apply to your own job."""
    result = await db.execute(select(JobORM).where(JobORM.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.owner_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot apply to your own job.")

    application = ApplicationORM(
        id=str(uuid.uuid4()),
        job_id=job_id,
        applicant_id=user_id,
        cover_letter=payload.cover_letter,
        proposed_rate=payload.proposed_rate,
        status="pending",
        applied_at=datetime.now(timezone.utc),
    )
    db.add(application)
    await db.flush()
    return application


@router.get(
    "/{job_id}/applicants",
    response_model=list[ApplicationRead],
    summary="List applicants (owner only)",
)
async def list_applicants(
    job_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db),
):
    """Return all applications for a job. Only the job owner can see this."""
    result = await db.execute(select(JobORM).where(JobORM.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not your job.")

    apps = await db.execute(select(ApplicationORM).where(ApplicationORM.job_id == job_id))
    return apps.scalars().all()
