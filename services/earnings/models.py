import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Date, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from shared.database import Base

class ShiftORM(Base):
    __tablename__ = "shifts"
    __table_args__ = {"schema": "earnings_svc"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_id = Column(UUID(as_uuid=True), nullable=False) # Will come from JWT
    platform = Column(String, nullable=False)
    shift_date = Column(Date, nullable=False)
    hours_worked = Column(Float, nullable=False)
    gross_earned = Column(Float, nullable=False)
    platform_deductions = Column(Float, nullable=False)  # Strictly with 's'
    net_received = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))