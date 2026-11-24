"""Login against a real database: the stored value is a hash, and the password is not logged."""

import logging
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

from vitalwatch.config import Settings
from vitalwatch.core.auth import decode_access_token, get_session
from vitalwatch.core.models import Role, Tenant, User
from vitalwatch.core.passwords import hash_password, make_hasher
from vitalwatch.main import create_app

pytestmark = pytest.mark.db

_SIGNING_KEY = "k" * 32
_PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
def login_client(session: Session) -> Iterator[TestClient]:
    app = create_app(Settings(environment="test", jwt_secret=SecretStr(_SIGNING_KEY)))

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as client:
        yield client


def _add_user(
    session: Session,
    *,
    email: str,
    role: Role,
    tenant: Tenant | None,
    active: bool = True,
) -> User:
    user = User(
        tenant_id=None if tenant is None else tenant.id,
        email=email,
        full_name="Test Person",
        role=role,
        password_hash=hash_password(make_hasher("test"), _PASSWORD),
        is_active=active,
    )
    session.add(user)
    session.flush()
    return user


def test_login_returns_a_token_and_stores_only_the_hash(
    login_client: TestClient, session: Session
) -> None:
    tenant = Tenant(name=f"Sunrise {uuid.uuid4().hex[:8]}")
    session.add(tenant)
    session.flush()
    user = _add_user(session, email="caregiver@example.test", role=Role.CAREGIVER, tenant=tenant)

    response = login_client.post(
        "/api/v1/auth/login",
        json={"email": "Caregiver@Example.Test", "password": _PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert _PASSWORD not in response.text
    context = decode_access_token(body["access_token"], _SIGNING_KEY)
    assert context.user_id == user.id
    assert context.tenant_id == tenant.id
    assert context.role is Role.CAREGIVER
    stored = session.get(User, user.id)
    assert stored is not None
    assert stored.password_hash.startswith("$argon2id$")
    assert stored.password_hash != _PASSWORD
    assert _PASSWORD not in stored.password_hash


def test_platform_admin_token_has_no_tenant(login_client: TestClient, session: Session) -> None:
    user = _add_user(session, email="admin@example.test", role=Role.PLATFORM_ADMIN, tenant=None)

    response = login_client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": _PASSWORD}
    )

    assert response.status_code == 200
    context = decode_access_token(response.json()["access_token"], _SIGNING_KEY)
    assert context.tenant_id is None
    assert context.role is Role.PLATFORM_ADMIN


def test_wrong_password_unknown_user_and_inactive_user_look_the_same(
    login_client: TestClient, session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    tenant = Tenant(name=f"Harbour {uuid.uuid4().hex[:8]}")
    session.add(tenant)
    session.flush()
    _add_user(session, email="active@example.test", role=Role.CAREGIVER, tenant=tenant)
    _add_user(
        session,
        email="inactive@example.test",
        role=Role.CAREGIVER,
        tenant=tenant,
        active=False,
    )

    with caplog.at_level(logging.DEBUG):
        wrong = login_client.post(
            "/api/v1/auth/login",
            json={"email": "active@example.test", "password": "not-the-password"},
        )
        missing = login_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.test", "password": _PASSWORD},
        )
        inactive = login_client.post(
            "/api/v1/auth/login",
            json={"email": "inactive@example.test", "password": _PASSWORD},
        )

    assert wrong.status_code == missing.status_code == inactive.status_code == 401
    assert wrong.json() == missing.json() == inactive.json()
    assert _PASSWORD not in caplog.text
    assert "not-the-password" not in caplog.text
    for record in caplog.records:
        assert _PASSWORD not in str(record.args)
        assert "not-the-password" not in str(record.args)
        assert _PASSWORD not in record.getMessage()
