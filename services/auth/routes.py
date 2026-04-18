"""
Auth routes — register, login, verify token.
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.schemas import Token, UserCreate, UserRead, MessageResponse
from shared.security import create_access_token, decode_access_token
from services.auth.models import UserORM

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Helpers ───────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


async def get_user_by_email(db: AsyncSession, email: str) -> UserORM | None:
    result = await db.execute(select(UserORM).where(UserORM.email == email))
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
    user = UserORM(
        id=str(uuid.uuid4()),
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Login and receive JWT",
)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
):
    """Login with email + password (OAuth2 form). Returns a JWT bearer token."""
    user = await get_user_by_email(db, form.username)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user.id})
    return Token(access_token=token)


@router.get(
    "/verify",
    response_model=UserRead,
    summary="Verify token and return current user",
)
async def verify_token(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
):
    """Validate a JWT and return the associated user."""
    from jose import JWTError

    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )
    result = await db.execute(select(UserORM).where(UserORM.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user
