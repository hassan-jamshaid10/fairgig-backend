from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, DateTime, String, Table, Column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base


# Junction table
user_roles_table = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", PG_UUID(as_uuid=True), ForeignKey("auth_svc.users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", PG_UUID(as_uuid=True), ForeignKey("auth_svc.roles.id",  ondelete="CASCADE"), primary_key=True),
    schema="auth_svc",
)


class RoleORM(Base):
    __tablename__ = "roles"
    __table_args__ = {"schema": "auth_svc"}

    id:   Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str]  = mapped_column(String, unique=True, nullable=False)


class UserORM(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth_svc"}

    id:            Mapped[UUID]       = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email:         Mapped[str]        = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str]        = mapped_column(String, nullable=False)
    full_name:     Mapped[str]        = mapped_column(String, nullable=False)
    phone:         Mapped[str | None] = mapped_column(String, nullable=True)
    city_zone:     Mapped[str | None] = mapped_column(String, nullable=True)
    created_at:    Mapped[datetime]   = mapped_column(DateTime(timezone=True))

    roles: Mapped[list[RoleORM]] = relationship(
        "RoleORM",
        secondary=user_roles_table,
        lazy="selectin",
    )

    @property
    def role(self) -> str | None:
        """Convenience shim — returns first role name for JWT payload."""
        return self.roles[0].name if self.roles else None