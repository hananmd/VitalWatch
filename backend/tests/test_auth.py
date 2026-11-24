import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from pydantic import SecretStr

from vitalwatch.config import Settings
from vitalwatch.core.auth import (
    AuthContext,
    TokenError,
    create_access_token,
    decode_access_token,
    require_roles,
)
from vitalwatch.core.models import Role
from vitalwatch.main import create_app

_SIGNING_KEY = "k" * 32
_OTHER_KEY = "m" * 32
_PASSWORD = "a-unique-password-value"


def _settings() -> Settings:
    return Settings(environment="test", jwt_secret=SecretStr(_SIGNING_KEY))


def _token(
    *,
    role: Role = Role.PLATFORM_ADMIN,
    tenant_id: uuid.UUID | None = None,
    secret: str = _SIGNING_KEY,
    now: datetime | None = None,
    ttl_seconds: int = 900,
) -> str:
    if role is not Role.PLATFORM_ADMIN and tenant_id is None:
        tenant_id = uuid.uuid4()
    return create_access_token(
        user_id=uuid.uuid4(),
        tenant_id=tenant_id,
        role=role,
        secret=secret,
        ttl_seconds=ttl_seconds,
        now=now,
    )


@pytest.fixture
def protected_client() -> TestClient:
    app = create_app(_settings())

    @app.get("/platform-only")
    def platform_only(
        user: Annotated[AuthContext, Depends(require_roles(Role.PLATFORM_ADMIN))],
    ) -> dict:
        return {"role": user.role.value}

    @app.get("/care")
    def care(
        user: Annotated[AuthContext, Depends(require_roles(Role.CAREGIVER, Role.CARE_HOME_ADMIN))],
    ) -> dict:
        return {"role": user.role.value}

    return TestClient(app)


def test_valid_token_exposes_the_caller(protected_client: TestClient) -> None:
    user_id = uuid.uuid4()
    token = create_access_token(
        user_id=user_id,
        tenant_id=None,
        role=Role.PLATFORM_ADMIN,
        secret=_SIGNING_KEY,
        ttl_seconds=900,
    )

    context = decode_access_token(token, _SIGNING_KEY)
    response = protected_client.get("/platform-only", headers={"Authorization": f"Bearer {token}"})

    assert context.user_id == user_id
    assert context.tenant_id is None
    assert context.role is Role.PLATFORM_ADMIN
    assert response.status_code == 200
    assert response.json() == {"role": "platform_admin"}


def test_caregiver_token_keeps_its_tenant() -> None:
    tenant_id = uuid.uuid4()
    token = _token(role=Role.CAREGIVER, tenant_id=tenant_id)

    context = decode_access_token(token, _SIGNING_KEY)

    assert context.role is Role.CAREGIVER
    assert context.tenant_id == tenant_id


def test_wrong_role_is_forbidden_and_the_right_role_is_allowed(
    protected_client: TestClient,
) -> None:
    caregiver = {"Authorization": f"Bearer {_token(role=Role.CAREGIVER)}"}

    denied = protected_client.get("/platform-only", headers=caregiver)
    allowed = protected_client.get("/care", headers=caregiver)

    assert denied.status_code == 403
    assert denied.json()["detail"] == "Not allowed"
    assert allowed.status_code == 200
    assert allowed.json() == {"role": "caregiver"}


def test_missing_token_is_unauthorized(protected_client: TestClient) -> None:
    response = protected_client.get("/platform-only")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.parametrize(
    "token",
    [
        "not-a-token",
        _token(secret=_OTHER_KEY),
        _token(now=datetime.now(UTC) - timedelta(minutes=30), ttl_seconds=60),
    ],
)
def test_bad_signature_and_expired_tokens_are_rejected(
    protected_client: TestClient, token: str
) -> None:
    response = protected_client.get("/platform-only", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_missing_claims_are_rejected() -> None:
    now = int(datetime.now(UTC).timestamp())
    incomplete = jwt.encode(
        {"sub": str(uuid.uuid4()), "iat": now, "exp": now + 60},
        _SIGNING_KEY,
        algorithm="HS256",
    )

    with pytest.raises(TokenError):
        decode_access_token(incomplete, _SIGNING_KEY)


def test_a_platform_admin_claim_with_a_tenant_is_rejected() -> None:
    now = int(datetime.now(UTC).timestamp())
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "tenant_id": str(uuid.uuid4()),
            "role": Role.PLATFORM_ADMIN.value,
            "iat": now,
            "exp": now + 60,
        },
        _SIGNING_KEY,
        algorithm="HS256",
    )

    with pytest.raises(TokenError):
        decode_access_token(token, _SIGNING_KEY)


def test_login_validation_does_not_echo_the_password(client: TestClient) -> None:
    too_long = _PASSWORD * 10
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.test", "password": too_long, "tenant_id": "ignored"},
    )

    assert response.status_code == 422
    assert too_long not in response.text
    assert _PASSWORD not in response.text
    assert "tenant_id" in response.text


def test_login_without_a_database_does_not_echo_the_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.test", "password": _PASSWORD},
    )

    assert response.status_code == 503
    assert _PASSWORD not in response.text
