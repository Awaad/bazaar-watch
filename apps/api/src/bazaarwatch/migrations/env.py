"""Alembic environment.

Async, because the application engine is async and running migrations through a
second synchronous driver would mean two connection paths to keep in step.

The URL comes from settings rather than alembic.ini, so the application and the
migrations read one source of truth and no credential sits in a committed file.
"""

from __future__ import annotations

import asyncio

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from bazaarwatch.core.logging import configure_logging
from bazaarwatch.core.models import Base
from bazaarwatch.core.settings import get_settings

# Importing the models registers them on Base.metadata. Without this, an
# autogenerate run would cheerfully propose dropping every table.
from bazaarwatch.modules.geo import models as geo_models  # noqa: F401
from bazaarwatch.modules.identity import models as identity_models  # noqa: F401

config = context.config

configure_logging(json_output=False)

target_metadata = Base.metadata

config.set_main_option("sqlalchemy.url", str(get_settings().database_url))


def _configure(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Type changes are otherwise invisible to autogenerate, which is how a
        # column silently keeps the wrong type across a migration.
        compare_type=True,
        compare_server_default=True,
        transaction_per_migration=True,
    )


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection: Connection) -> None:
    _configure(connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
