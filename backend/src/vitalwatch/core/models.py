"""Tables owned by the core module: tenants (care homes), users (staff) and patients."""

import uuid
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    SmallInteger,
    String,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from vitalwatch.db import Base, CreatedAt, UUIDPrimaryKey


class Role(StrEnum):
    PLATFORM_ADMIN = "platform_admin"
    CARE_HOME_ADMIN = "care_home_admin"
    CAREGIVER = "caregiver"


_ROLE_VALUES = ", ".join(f"'{r.value}'" for r in Role)


class Tenant(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200), unique=True)


class User(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(f"role IN ({_ROLE_VALUES})", name="role_valid"),
        # Platform admins belong to no care home; everyone else belongs to exactly one.
        CheckConstraint(
            "(role = 'platform_admin') = (tenant_id IS NULL)", name="tenant_matches_role"
        ),
        # Emails are stored lower-case so the unique constraint is case-insensitive.
        CheckConstraint("email = lower(email)", name="email_lowercase"),
    )

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"), index=True
    )
    email: Mapped[str] = mapped_column(String(254), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())


class Patient(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "patients"
    __table_args__ = (
        # Lets other tables reference (tenant_id, id), so a row can only point at a
        # patient in its own tenant. The index also serves tenant_id lookups.
        UniqueConstraint("tenant_id", "id"),
        CheckConstraint("birth_year BETWEEN 1900 AND 2100", name="birth_year_range"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="RESTRICT"))
    display_name: Mapped[str] = mapped_column(String(200))
    room: Mapped[str | None] = mapped_column(String(50))
    birth_year: Mapped[int | None] = mapped_column(SmallInteger)
