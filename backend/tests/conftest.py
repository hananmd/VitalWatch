from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vitalwatch.config import Settings
from vitalwatch.main import create_app

# backend/tests/conftest.py -> repo root is two levels above backend/
CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "docs" / "contracts"


@pytest.fixture
def settings() -> Settings:
    return Settings(environment="test")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def contracts_dir() -> Path:
    assert CONTRACTS_DIR.is_dir(), f"contracts folder not found at {CONTRACTS_DIR}"
    return CONTRACTS_DIR
