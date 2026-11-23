"""Fixtures for tests that need a real PostgreSQL.

Server: ``VITALWATCH_TEST_DATABASE_URL`` if set (CI uses its Postgres service), otherwise a
throwaway testcontainers Postgres. Tests never use ``VITALWATCH_DATABASE_URL``, and every
database they touch is created here with a random name and dropped afterwards.
"""

import os
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import URL, Connection, Engine, create_engine, make_url, text
from sqlalchemy.orm import Session

from vitalwatch.db import make_engine

BACKEND_DIR = Path(__file__).resolve().parents[2]
POSTGRES_IMAGE = "postgres:17-bookworm"


@pytest.fixture(scope="session")
def server_url() -> Iterator[URL]:
    configured = os.environ.get("VITALWATCH_TEST_DATABASE_URL")
    if configured:
        yield make_url(configured)
        return

    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer(POSTGRES_IMAGE, driver="psycopg") as postgres:
        yield make_url(postgres.get_connection_url())


@pytest.fixture(scope="session")
def make_database(server_url: URL) -> Iterator[Callable[[], URL]]:
    """Returns a factory that creates an empty database; all are dropped at session end."""
    admin = create_engine(server_url, isolation_level="AUTOCOMMIT")
    created: list[str] = []

    def factory() -> URL:
        name = f"vw_test_{uuid.uuid4().hex[:12]}"
        with admin.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
        created.append(name)
        return server_url.set(database=name)

    yield factory

    with admin.connect() as conn:
        for name in created:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    admin.dispose()


def alembic_config(connection: Connection) -> Config:
    config = Config(BACKEND_DIR / "alembic.ini")
    config.attributes["connection"] = connection
    config.attributes["configure_logger"] = False  # leave pytest's logging alone
    return config


@contextmanager
def connect(url: URL) -> Iterator[Connection]:
    engine = make_engine(url)
    try:
        with engine.connect() as connection:
            yield connection
    finally:
        engine.dispose()


@pytest.fixture
def empty_db(make_database: Callable[[], URL]) -> Iterator[Connection]:
    """A connection to a brand-new, empty database (for migration tests)."""
    with connect(make_database()) as connection:
        yield connection


@pytest.fixture
def migrations(empty_db: Connection) -> Config:
    """Alembic config bound to ``empty_db``."""
    return alembic_config(empty_db)


@pytest.fixture(scope="session")
def migrated_engine(make_database: Callable[[], URL]) -> Iterator[Engine]:
    """One database migrated to head, shared by all model tests."""
    engine = make_engine(make_database())
    with engine.begin() as connection:
        command.upgrade(alembic_config(connection), "head")
    yield engine
    engine.dispose()


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    """A session whose work is always rolled back, so tests don't see each other's rows."""
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as db_session:
            yield db_session
        transaction.rollback()
