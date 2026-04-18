"""Shared Pydantic schemas used across all services."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


# ── Token ─────────────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: UUID
    role: Optional[str] = None


class TokenData(BaseModel):
    sub: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str


# ── User ──────────────────────────────────────────────────────────────────────

Role = Literal["Worker", "Verifier", "Advocate"]


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    city_zone: Optional[str] = None


class UserCreate(UserBase):
    password: str
    role: Role


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserRead(UserBase):
    id: UUID
    created_at: datetime
    role: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Job ───────────────────────────────────────────────────────────────────────

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


# ── Generic ───────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    city_zone: Optional[str] = None


class UserBasicRead(BaseModel):
    id: UUID
    full_name: str
    city_zone: Optional[str] = None
    role: str

    class Config:
        from_attributes = True  # Allows Pydantic to read directly from your ORM models