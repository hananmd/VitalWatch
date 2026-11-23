"""Application settings, loaded from VITALWATCH_* environment variables.

Secrets are never given defaults here; they must come from the environment.
"""

from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VITALWATCH_")

    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # e.g. postgresql+psycopg://user:password@host:5432/vitalwatch
    # SecretStr keeps the password out of logs and reprs.
    database_url: SecretStr | None = None
