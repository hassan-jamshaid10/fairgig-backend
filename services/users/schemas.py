"""Users service Pydantic schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ProfileUpdate(BaseModel):
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    skills: Optional[list[str]] = None
    hourly_rate: Optional[float] = None


class ProfileRead(BaseModel):
    id: str
    bio: Optional[str]
    avatar_url: Optional[str]
    skills: list[str]
    hourly_rate: Optional[float]
    jobs_completed: int
    rating: float
    updated_at: datetime

    model_config = {"from_attributes": True}
