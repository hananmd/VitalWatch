"""The database itself enforces the core rules, whatever the application code does."""

import uuid

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from vitalwatch.models import Device, DeviceStatus, Patient, Role, Tenant, User

pytestmark = pytest.mark.db


def add_tenant(session: Session, name: str = "Sunrise Care") -> Tenant:
    tenant = Tenant(name=name)
    session.add(tenant)
    session.flush()
    return tenant


def make_user(tenant: Tenant | None, role: Role = Role.CAREGIVER, email: str = "a@example.test"):
    return User(
        tenant_id=tenant.id if tenant else None,
        email=email,
        full_name="Test Person",
        role=role,
        password_hash="not-a-real-hash",  # noqa: S106 - constraint tests do not log in
    )


def assert_rejected(session: Session, obj: object, constraint: str | None) -> None:
    """Flushing ``obj`` must fail on ``constraint`` (None means a NOT NULL violation)."""
    session.add(obj)
    with pytest.raises(IntegrityError) as excinfo:
        session.flush()
    assert excinfo.value.orig.diag.constraint_name == constraint


def test_rows_round_trip_with_server_defaults(session: Session) -> None:
    tenant = add_tenant(session)
    patient = Patient(tenant_id=tenant.id, display_name="Patient A", room="12", birth_year=1940)
    user = make_user(tenant)
    session.add_all([patient, user])
    session.flush()
    device = Device(tenant_id=tenant.id, device_id="DEV-0042", patient_id=patient.id)
    session.add(device)
    session.flush()

    session.expire_all()
    loaded = session.scalars(select(Device).where(Device.device_id == "DEV-0042")).one()
    assert loaded.status == DeviceStatus.ACTIVE
    assert loaded.patient_id == patient.id
    assert loaded.created_at.tzinfo is not None
    assert session.get(User, user.id).is_active is True


def test_patient_requires_a_tenant(session: Session) -> None:
    assert_rejected(session, Patient(display_name="No Home"), None)


def test_patient_tenant_must_exist(session: Session) -> None:
    patient = Patient(tenant_id=uuid.uuid4(), display_name="Ghost")
    assert_rejected(session, patient, "fk_patients_tenant_id_tenants")


def test_platform_admin_has_no_tenant(session: Session) -> None:
    session.add(make_user(None, Role.PLATFORM_ADMIN))
    session.flush()


def test_platform_admin_with_a_tenant_is_rejected(session: Session) -> None:
    user = make_user(add_tenant(session), Role.PLATFORM_ADMIN)
    assert_rejected(session, user, "ck_users_tenant_matches_role")


@pytest.mark.parametrize("role", [Role.CARE_HOME_ADMIN, Role.CAREGIVER])
def test_care_home_staff_without_a_tenant_is_rejected(session: Session, role: Role) -> None:
    assert_rejected(session, make_user(None, role), "ck_users_tenant_matches_role")


def test_unknown_role_is_rejected(session: Session) -> None:
    user = make_user(add_tenant(session))
    user.role = "superuser"
    assert_rejected(session, user, "ck_users_role_valid")


def test_email_is_unique_across_tenants(session: Session) -> None:
    session.add(make_user(add_tenant(session, "Home A"), email="same@example.test"))
    session.flush()
    other = make_user(add_tenant(session, "Home B"), email="same@example.test")
    assert_rejected(session, other, "uq_users_email")


def test_email_must_be_lower_case(session: Session) -> None:
    user = make_user(add_tenant(session), email="Mixed@Example.test")
    assert_rejected(session, user, "ck_users_email_lowercase")


@pytest.mark.parametrize("birth_year", [1899, 2101])
def test_birth_year_out_of_range_is_rejected(session: Session, birth_year: int) -> None:
    patient = Patient(tenant_id=add_tenant(session).id, display_name="P", birth_year=birth_year)
    assert_rejected(session, patient, "ck_patients_birth_year_range")


def test_unknown_device_status_is_rejected(session: Session) -> None:
    device = Device(tenant_id=add_tenant(session).id, device_id="DEV-1", status="lost")
    assert_rejected(session, device, "ck_devices_status_valid")


@pytest.mark.parametrize("device_id", ["", "has space", "semi;colon"])
def test_device_id_format_is_enforced(session: Session, device_id: str) -> None:
    device = Device(tenant_id=add_tenant(session).id, device_id=device_id)
    assert_rejected(session, device, "ck_devices_device_id_format")


def test_device_id_longer_than_64_is_rejected(session: Session) -> None:
    session.add(Device(tenant_id=add_tenant(session).id, device_id="x" * 65))
    with pytest.raises(DataError, match="value too long"):
        session.flush()


def test_device_id_is_unique_across_tenants(session: Session) -> None:
    session.add(Device(tenant_id=add_tenant(session, "Home A").id, device_id="DEV-1"))
    session.flush()
    other = Device(tenant_id=add_tenant(session, "Home B").id, device_id="DEV-1")
    assert_rejected(session, other, "uq_devices_device_id")


def test_device_cannot_link_to_another_tenants_patient(session: Session) -> None:
    home_a = add_tenant(session, "Home A")
    home_b = add_tenant(session, "Home B")
    patient_b = Patient(tenant_id=home_b.id, display_name="Patient B")
    session.add(patient_b)
    session.flush()

    device = Device(tenant_id=home_a.id, device_id="DEV-A1", patient_id=patient_b.id)
    assert_rejected(session, device, "fk_devices_tenant_id_patient_id_patients")


def test_deleting_a_patient_unlinks_its_device(session: Session) -> None:
    tenant = add_tenant(session)
    patient = Patient(tenant_id=tenant.id, display_name="Patient A")
    session.add(patient)
    session.flush()
    device = Device(tenant_id=tenant.id, device_id="DEV-1", patient_id=patient.id)
    session.add(device)
    session.flush()

    session.execute(delete(Patient).where(Patient.id == patient.id))
    session.refresh(device)

    assert device.patient_id is None
    assert device.tenant_id == tenant.id  # only patient_id is cleared


def test_tenant_with_data_cannot_be_deleted(session: Session) -> None:
    tenant = add_tenant(session)
    session.add(Patient(tenant_id=tenant.id, display_name="Patient A"))
    session.flush()

    with pytest.raises(IntegrityError) as excinfo:
        session.execute(delete(Tenant).where(Tenant.id == tenant.id))
    assert excinfo.value.orig.diag.constraint_name == "fk_patients_tenant_id_tenants"
