"""Shared Pydantic schemas used across all services."""

from datetime import date, datetime
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

# User Models
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

# Job Models
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

# Generic Models
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
        from_attributes = True

# Earnings / Shift Models
class ShiftCreate(BaseModel):
    platform: str
    shift_date: date
    hours_worked: float
    gross_earned: float
    platform_deductions: float
    net_received: float
    notes: Optional[str] = None

class ShiftRead(BaseModel):
    id: UUID
    worker_id: UUID
    platform: str
    shift_date: date
    hours_worked: float
    gross_earned: float
    platform_deductions: float
    net_received: float
    notes: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class ShiftReadWithStatus(ShiftRead):
    screenshot_status: str
    screenshot_url: Optional[str] = None

class ShiftHistoryResponse(BaseModel):
    shifts: list[ShiftReadWithStatus]
    total: int

# Screenshot and Verification Models
class ScreenshotRead(BaseModel):
    shift_id: UUID
    image_url: str
    status: str
    verifier_id: Optional[UUID] = None
    verification_note: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    class Config:
        from_attributes = True

class ScreenshotVerifyRequest(BaseModel):
    status: Literal["Confirmed", "Flagged", "Unverifiable"]
    note: Optional[str] = None

class PendingScreenshotRead(BaseModel):
    shift_id: UUID
    image_url: str
    status: str
    created_at: datetime
    shift: ShiftRead
    class Config:
        from_attributes = True

class PendingQueueResponse(BaseModel):
    screenshots: list[PendingScreenshotRead]
    total: int

# NEW: Worker's Private Screenshot View
class WorkerScreenshotShiftContext(BaseModel):
    platform: str
    shift_date: date
    net_received: float

class WorkerScreenshotRead(BaseModel):
    shift_id: UUID
    image_url: str
    status: str
    verified_at: Optional[datetime] = None
    created_at: datetime
    shift: WorkerScreenshotShiftContext

    class Config:
        from_attributes = True

class WorkerScreenshotsResponse(BaseModel):
    screenshots: list[WorkerScreenshotRead]
    total: int