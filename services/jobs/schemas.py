"""Jobs service Pydantic schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=20)
    budget: float = Field(..., gt=0)
    skills: list[str] = []


class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = None
    budget: Optional[float] = Field(None, gt=0)
    skills: Optional[list[str]] = None
    status: Optional[str] = None


class JobRead(BaseModel):
    id: str
    owner_id: str
    title: str
    description: str
    budget: float
    skills: list[str]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApplicationCreate(BaseModel):
    cover_letter: Optional[str] = None
    proposed_rate: Optional[float] = Field(None, gt=0)


class ApplicationRead(BaseModel):
    id: str
    job_id: str
    applicant_id: str
    cover_letter: Optional[str]
    proposed_rate: Optional[float]
    status: str
    applied_at: datetime

    model_config = {"from_attributes": True}
