"""Shared Pydantic schemas + JWT helpers used across all services."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


# ── Token ────────────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    sub: Optional[str] = None   # user id


# ── User ─────────────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Job ──────────────────────────────────────────────────────────────────────

class JobBase(BaseModel):
    title: str
    description: str
    budget: float
    skills: list[str] = []


class JobCreate(JobBase):
    pass


class JobRead(JobBase):
    id: str
    owner_id: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Generic ──────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str
