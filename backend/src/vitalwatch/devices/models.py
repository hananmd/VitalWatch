"""Tables owned by the devices module. Credentials are added in #9."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, String, text
from sqlalchemy.orm import Mapped, mapped_column

from vitalwatch.db import Base, CreatedAt, UUIDPrimaryKey


class DeviceStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


class Device(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "devices"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'revoked')", name="status_valid"),
        CheckConstraint("device_id ~ '^[A-Za-z0-9_-]{1,64}$'", name="device_id_format"),
        # The linked patient must be in the same tenant as the device. Deleting the
        # patient unlinks the device (sets only patient_id to NULL, PostgreSQL 15+).
        ForeignKeyConstraint(
            ["tenant_id", "patient_id"],
            ["patients.tenant_id", "patients.id"],
            ondelete="SET NULL (patient_id)",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"), index=True
    )
    # Hardware identifier from the contract (e.g. DEV-0042), unique across the platform
    # because devices authenticate with it before any tenant is known.
    device_id: Mapped[str] = mapped_column(String(64), unique=True)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(String(16), server_default=text("'active'"))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
