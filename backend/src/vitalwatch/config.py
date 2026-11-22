"""Application settings, loaded from environment variables.

Every variable uses the ``VITALWATCH_`` prefix, e.g. ``VITALWATCH_ENVIRONMENT=staging``.
Secrets are never given defaults here; they must come from the environment.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VITALWATCH_", extra="ignore")

    app_name: str = "VitalWatch"
    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @property
    def docs_enabled(self) -> bool:
        """Interactive API docs are off in production."""
        return self.environment != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
