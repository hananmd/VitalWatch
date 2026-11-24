import pytest
from pydantic import ValidationError

from vitalwatch.config import Settings
from vitalwatch.main import create_app


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VITALWATCH_ENVIRONMENT", raising=False)
    monkeypatch.delenv("VITALWATCH_LOG_LEVEL", raising=False)
    monkeypatch.delenv("VITALWATCH_JWT_SECRET", raising=False)
    monkeypatch.delenv("VITALWATCH_JWT_EXPIRES_SECONDS", raising=False)

    settings = Settings()

    assert settings.environment == "local"
    assert settings.log_level == "INFO"
    assert settings.jwt_secret is None
    assert settings.jwt_expires_seconds == 900


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


def test_jwt_secret_is_read_from_the_environment_and_hidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VITALWATCH_JWT_SECRET", "x" * 32)

    settings = Settings()

    assert settings.jwt_secret is not None
    assert settings.jwt_secret.get_secret_value() == "x" * 32
    assert "x" * 32 not in repr(settings)


def test_jwt_secret_must_be_at_least_32_characters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VITALWATCH_JWT_SECRET", "too-short")

    with pytest.raises(ValidationError):
        Settings()


def test_jwt_expiry_stays_short(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VITALWATCH_JWT_EXPIRES_SECONDS", "86400")

    with pytest.raises(ValidationError):
        Settings()


def test_app_uses_given_settings() -> None:
    app = create_app(Settings(environment="test"))

    assert app.state.settings.environment == "test"
