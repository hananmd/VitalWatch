"""Application settings, loaded from VITALWATCH_* environment variables.

Secrets are never given defaults here; they must come from the environment.
"""

from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# HS256 needs a key at least this long. No default: it must come from the environment.
_MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VITALWATCH_")

    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # e.g. postgresql+psycopg://user:password@host:5432/vitalwatch
    # SecretStr keeps the password out of logs and reprs.
    database_url: SecretStr | None = None

    # Signs access tokens. Required for login; the process still starts without it
    # so /health works in CI image scans before the key is injected.
    jwt_secret: SecretStr | None = None
    # Short on purpose: 15 minutes unless overridden, and never longer than an hour.
    jwt_expires_seconds: int = Field(default=900, ge=60, le=3600)

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_is_long_enough(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value()) < _MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                f"VITALWATCH_JWT_SECRET must be at least {_MIN_JWT_SECRET_LENGTH} characters"
            )
        return value
