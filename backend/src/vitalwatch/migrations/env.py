"""Alembic environment.

The connection comes from, in order:
1. ``config.attributes["connection"]`` (tests pass an open connection), or
2. ``VITALWATCH_DATABASE_URL`` via ``Settings``.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection

from vitalwatch.config import Settings
from vitalwatch.db import make_engine
from vitalwatch.models import Base

config = context.config

if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _database_url() -> str:
    url = Settings().database_url
    if url is None:
        raise RuntimeError("VITALWATCH_DATABASE_URL is not set")
    return url.get_secret_value()


def _run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it (``alembic upgrade head --sql``)."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return

    engine = make_engine(_database_url())
    try:
        with engine.connect() as connection:
            _run(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
