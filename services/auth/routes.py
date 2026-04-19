"""
Auth routes — register, login, refresh, verify token.
"""

import bcrypt
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import Query
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.schemas import (
    LoginRequest,
    RefreshRequest,
    TokenPair,
    UserBasicRead,
    UserCreate,
    UserRead,
    UserUpdate,
)
from shared.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from services.auth.models import UserORM, RoleORM

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Helpers ───────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


async def get_user_by_email(db: AsyncSession, email: str) -> UserORM | None:
    result = await db.execute(select(UserORM).where(UserORM.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> UserORM | None:
    result = await db.execute(select(UserORM).where(UserORM.id == user_id))
    return result.scalar_one_or_none()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new account. Returns the created user (no password)."""
    if await get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )

    role_result = await db.execute(select(RoleORM).where(RoleORM.name == payload.role))
    role_orm = role_result.scalar_one_or_none()
    if not role_orm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{payload.role}' does not exist.",
        )

    user = UserORM(
        email=payload.email,
        full_name=payload.full_name,
        phone=payload.phone,
        city_zone=payload.city_zone,
        password_hash=hash_password(payload.password),
        created_at=datetime.now(timezone.utc),
        roles=[role_orm],
    )
    db.add(user)
    await db.flush()
    return user


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Login and receive access + refresh tokens",
)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_data = {"sub": str(user.id), "role": user.role}
    return TokenPair(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        user_id=user.id,
        role=user.role,
    )


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Exchange refresh token for a new token pair",
)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        token_payload = decode_refresh_token(payload.refresh_token)
        user_id: str = token_payload.get("sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    token_data = {"sub": str(user.id), "role": user.role}
    return TokenPair(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        user_id=user.id,
        role=user.role,
    )

@router.get(
    "/verify",
    response_model=UserRead,
    summary="Verify access token and return current user",
)
async def verify_token(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
):
    """Validate an access JWT and return the associated user."""
    try:
        token_payload = decode_access_token(token)
        user_id: str = token_payload.get("sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current logged in user profile",
)
async def get_me(
    db: AsyncSession = Depends(get_db),
    access_token: Optional[str] = Query(None, description="Paste your JWT token here"),
    header_token: Optional[str] = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)),
):
    """
    Returns the currently logged in user's information.
    Accepts token via query parameter or Authorization header.
    """
    token = access_token or header_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please provide an access token.",
        )

    try:
        token_payload = decode_access_token(token)
        user_id: str = token_payload.get("sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identification.",
        )

    # Use your existing ORM helper instead of raw SQL
    user = await get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(status_code=401, detail="User not found.")

    return user

@router.patch(
    "/me",
    response_model=UserRead,
    summary="Update current logged in user profile",
)
async def update_me(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    access_token: Optional[str] = Query(None, description="Paste your JWT token here"),
    header_token: Optional[str] = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)),
):
    """
    Updates the logged in user's profile. 
    Ignores email or role updates.
    """
    token = access_token or header_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please provide an access token.",
        )

    try:
        token_payload = decode_access_token(token)
        user_id: str = token_payload.get("sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identification.",
        )

    # 1. Fetch the user
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # 2. Extract only the fields the user actually sent in the request body
    # exclude_unset=True ensures we don't overwrite existing data with None
    update_data = payload.model_dump(exclude_unset=True)

    if not update_data:
        return user # If body is empty, just return the existing user

    # 3. Apply the updates safely
    allowed_fields = {"full_name", "phone", "city_zone"}
    
    for key, value in update_data.items():
        if key in allowed_fields:
            setattr(user, key, value)

    # 4. Save and return
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user

@router.get(
    "/users/{user_id}",
    response_model=UserBasicRead,
    summary="Get basic user info (For Verifiers, Advocates, and internal microservices)",
)
async def get_user_basic_info(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    access_token: Optional[str] = Query(None, description="Paste your JWT token here"),
    header_token: Optional[str] = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)),
):
    """
    Returns limited user info (id, full_name, city_zone, role) for cross-service communication.
    Restricted to non-Worker roles.
    """
    token = access_token or header_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please provide an access token.",
        )

    # 1. Decode token and extract the caller's role
    try:
        token_payload = decode_access_token(token)
        caller_role: str = token_payload.get("role", "").lower()
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )

    # 2. Strict Access Control (Workers get a 403)
    if caller_role == "worker":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden. Workers are not authorized to look up other users.",
        )

    # 3. Fetch the requested user
    target_user = await get_user_by_id(db, user_id)
    
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    # 4. Return the user 
    # (Pydantic automatically filters this through UserBasicRead, dropping email and phone)
    return target_user