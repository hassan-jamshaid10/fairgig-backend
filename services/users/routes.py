"""
Users routes — profile CRUD.
Authentication is done via JWT forwarded from the gateway.
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.security import decode_access_token
from services.users.models import UserProfileORM
from services.users.schemas import ProfileRead, ProfileUpdate

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


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[ProfileRead],
    summary="List all user profiles (paginated)",
)
async def list_users(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Return a paginated list of public user profiles."""
    result = await db.execute(select(UserProfileORM).offset(skip).limit(limit))
    return result.scalars().all()


@router.get(
    "/me",
    response_model=ProfileRead,
    summary="Get my profile",
)
async def get_my_profile(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated user's profile."""
    result = await db.execute(select(UserProfileORM).where(UserProfileORM.id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return profile


@router.patch(
    "/me",
    response_model=ProfileRead,
    summary="Update my profile",
)
async def update_my_profile(
    payload: ProfileUpdate,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db),
):
    """Update bio, skills, avatar or hourly rate."""
    result = await db.execute(select(UserProfileORM).where(UserProfileORM.id == user_id))
    profile = result.scalar_one_or_none()

    if not profile:
        # Auto-create profile on first update
        profile = UserProfileORM(
            id=user_id,
            skills=[],
            jobs_completed=0,
            rating=0.0,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(profile)

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)
    profile.updated_at = datetime.now(timezone.utc)

    await db.flush()
    return profile


@router.get(
    "/{user_id}",
    response_model=ProfileRead,
    summary="Get a user's public profile",
)
async def get_user_profile(user_id: str, db: AsyncSession = Depends(get_db)):
    """Return any user's public profile by ID."""
    result = await db.execute(select(UserProfileORM).where(UserProfileORM.id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="User not found.")
    return profile
