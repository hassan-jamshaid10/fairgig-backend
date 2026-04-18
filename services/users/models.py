"""SQLAlchemy ORM model for the user_profiles table."""

from datetime import datetime
from sqlalchemy import ARRAY, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base


class UserProfileORM(Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True)       # same as users.id
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    hourly_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    jobs_completed: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
