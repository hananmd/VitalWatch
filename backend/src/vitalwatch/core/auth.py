"""Login, access tokens and role checks.

The tenant and the role come from the verified token, never from the request body.
"""

import logging
import re
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Literal

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from vitalwatch.config import Settings
from vitalwatch.core.models import Role, User
from vitalwatch.core.passwords import dummy_hash, verify_password

logger = logging.getLogger(__name__)

# Shape only. No DNS lookup, so a login attempt cannot leak the address to a resolver.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _email(value: str) -> str:
    email = value.strip().lower()
    if not _EMAIL.fullmatch(email):
        raise ValueError("invalid email")
    return email


Email = Annotated[str, AfterValidator(_email)]

_ALGORITHM = "HS256"
# tenant_id is checked separately: PyJWT treats a present null as "missing", but a
# platform admin's tenant_id claim is null on purpose.
_REQUIRED_CLAIMS = ["exp", "iat", "sub", "role"]
_PASSWORD_FIELDS = {"password", "password_hash"}
_bearer = HTTPBearer(auto_error=False)


class TokenError(Exception):
    """The token is missing, expired, badly signed, or does not carry the required claims."""


@dataclass(frozen=True, slots=True)
class AuthContext:
    user_id: uuid.UUID
    tenant_id: uuid.UUID | None
    role: Role


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Email = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - OAuth token type, not a credential
    expires_in: int


def redact_passwords(value: object) -> object:
    """Drop password values from validation errors before they are sent or logged."""
    if isinstance(value, list):
        return [redact_passwords(item) for item in value]
    if isinstance(value, dict):
        loc = value.get("loc")
        hides_password = isinstance(loc, list) and bool(loc) and loc[-1] in _PASSWORD_FIELDS
        redacted: dict[str, object] = {}
        for key, item in value.items():
            if key in _PASSWORD_FIELDS or (key == "input" and hides_password):
                redacted[key] = "[redacted]"
            else:
                redacted[key] = redact_passwords(item)
        return redacted
    return value


def create_access_token(
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID | None,
    role: Role,
    secret: str,
    ttl_seconds: int,
    now: datetime | None = None,
) -> str:
    issued = now or datetime.now(UTC)
    if issued.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    payload = {
        "sub": str(user_id),
        "tenant_id": None if tenant_id is None else str(tenant_id),
        "role": role.value,
        "iat": int(issued.timestamp()),
        "exp": int(issued.timestamp()) + ttl_seconds,
    }
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def decode_access_token(token: str, secret: str) -> AuthContext:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[_ALGORITHM],
            options={"require": _REQUIRED_CLAIMS},
        )
        if "tenant_id" not in payload:
            raise TokenError
        user_id = uuid.UUID(str(payload["sub"]))
        role = Role(str(payload["role"]))
        raw_tenant = payload["tenant_id"]
        tenant_id = None if raw_tenant is None else uuid.UUID(str(raw_tenant))
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise TokenError from exc
    if (role is Role.PLATFORM_ADMIN) != (tenant_id is None):
        raise TokenError
    return AuthContext(user_id=user_id, tenant_id=tenant_id, role=role)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_session(request: Request) -> Iterator[Session | None]:
    """Yield a session, or None when the app has no database.

    This does not raise. A failure here would be returned in place of a 422
    when the request body is invalid.
    """
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        yield None
        return
    with Session(engine) as session:
        yield session


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Not authenticated")
    settings = get_settings(request)
    if settings.jwt_secret is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )
    try:
        return decode_access_token(credentials.credentials, settings.jwt_secret.get_secret_value())
    except TokenError:
        raise _unauthorized("Invalid or expired token") from None


def require_roles(*allowed: Role):
    """Dependency factory: the caller must have one of ``allowed`` roles."""
    if not allowed:
        raise ValueError("require_roles needs at least one role")

    def check(user: Annotated[AuthContext, Depends(get_current_user)]) -> AuthContext:
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
        return user

    return check


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", summary="Exchange email and password for an access token")
def login(
    body: LoginRequest,
    request: Request,
    session: Annotated[Session | None, Depends(get_session)],
) -> TokenResponse:
    settings = get_settings(request)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is not configured"
        )
    if settings.jwt_secret is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )

    email = body.email
    user = session.scalar(select(User).where(User.email == email))
    hasher = request.app.state.password_hasher
    if user is None:
        # Spend the same kind of work as a real check, then reject. The dummy hash
        # is not a user password and is never logged.
        verify_password(hasher, body.password, dummy_hash(hasher))
        password_ok = False
    else:
        password_ok = verify_password(hasher, body.password, user.password_hash)

    if user is None or not user.is_active or not password_ok:
        # Email only: the password must not appear in the log message or its arguments.
        logger.info("login failed for %s", email)
        raise _unauthorized("Invalid email or password")

    token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=Role(user.role),
        secret=settings.jwt_secret.get_secret_value(),
        ttl_seconds=settings.jwt_expires_seconds,
    )
    return TokenResponse(access_token=token, expires_in=settings.jwt_expires_seconds)
