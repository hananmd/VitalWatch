import pytest
from pydantic import ValidationError

from vitalwatch.config import Settings
from vitalwatch.main import create_app


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VITALWATCH_ENVIRONMENT", raising=False)
    monkeypatch.delenv("VITALWATCH_LOG_LEVEL", raising=False)

    settings = Settings()

    assert settings.environment == "local"
    assert settings.log_level == "INFO"


def test_reads_prefixed_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VITALWATCH_ENVIRONMENT", "staging")
    monkeypatch.setenv("VITALWATCH_LOG_LEVEL", "DEBUG")

    settings = Settings()

    assert settings.environment == "staging"
    assert settings.log_level == "DEBUG"


def test_rejects_unknown_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VITALWATCH_ENVIRONMENT", "prod")

    with pytest.raises(ValidationError):
        Settings()


def test_app_uses_given_settings() -> None:
    app = create_app(Settings(environment="test"))

    assert app.state.settings.environment == "test"
