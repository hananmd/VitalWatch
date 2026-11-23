"""Imports every module's tables so ``Base.metadata`` is complete (used by Alembic and tests)."""

from vitalwatch.core.models import Patient, Role, Tenant, User
from vitalwatch.db import Base
from vitalwatch.devices.models import Device, DeviceStatus

__all__ = ["Base", "Device", "DeviceStatus", "Patient", "Role", "Tenant", "User"]
