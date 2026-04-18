"""ORM models for the Jobs service."""

from datetime import datetime
from sqlalchemy import ARRAY, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base


class JobORM(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    budget: Mapped[float] = mapped_column(Float, nullable=False)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    status: Mapped[str] = mapped_column(String(50), default="open")  # open|closed|in_progress
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ApplicationORM(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    applicant_id: Mapped[str] = mapped_column(String, nullable=False)
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending|accepted|rejected
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
