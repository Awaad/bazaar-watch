"""Integration harness.

Three choices worth knowing about.

**A separate database, dropped and recreated per session.** Reusing the
development database would let a failed run leave state that makes the next run
lie. Dropping is the only way to be sure the schema under test is the schema the
migrations produce, which matters most when the server version differs between a
laptop, CI and wherever else this runs.

**Migrated by running the same command a developer runs**, as a subprocess with
`DATABASE_URL` in the environment, rather than by driving Alembic in-process.
`get_settings` is `lru_cache`d, so an in-process run would need the cache cleared
at exactly the right moment, and a subprocess cannot get that wrong. It also
means the harness exercises the real migration path rather than a parallel one.

**Synchronous connections.** These tests exercise SQL, not application code, and
a sync engine avoids event-loop fixtures entirely. Async fixtures belong with the
first service function that needs testing, not here.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import NoReturn
from urllib.parse import urlsplit, urlunsplit

import pytest
from sqlalchemy import Connection, Engine, create_engine, text

from bazaarwatch.core.settings import Environment, Settings

TEST_DATABASE = "bazaarwatch_test"
REPO_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_INI = REPO_ROOT / "apps" / "api" / "alembic.ini"

REQUIRED_EXTENSIONS = ("postgis", "vector", "pg_trgm", "ltree", "pgcrypto")


@pytest.fixture
def settings() -> Settings:
    """Settings that never touch a real service. Connection failure is the
    expected path for the readiness tests."""
    return Settings(
        environment=Environment.LOCAL,
        database_url="postgresql+psycopg://u:p@127.0.0.1:1/none",  # type: ignore[arg-type]
        redis_url="redis://127.0.0.1:1/0",  # type: ignore[arg-type]
    )


def _unavailable(reason: str) -> NoReturn:
    """Skip locally, fail in CI.

    On a laptop, `make test` must work with nothing running, so these skip. In
    CI a skipped integration suite is indistinguishable from a passing one, and
    that is how the fold parity check stayed unrun for four slices.
    """
    if os.environ.get("CI"):
        pytest.fail(f"integration tests cannot run in CI: {reason}")
    pytest.skip(reason)


def _with_database(url: str, database: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(parts._replace(path=f"/{database}"))


def _base_url() -> str:
    """The server to test against, taken from the environment.

    `DATABASE_URL` names the development database; only its host, port and
    credentials are borrowed. `TEST_DATABASE_URL` overrides it entirely.
    """
    override = os.environ.get("TEST_DATABASE_URL")
    if override:
        return override
    url = os.environ.get("DATABASE_URL")
    if not url:
        _unavailable("no DATABASE_URL: start the stack with `make up`")
    return _with_database(url, TEST_DATABASE)


def _server_description(url: str) -> str:
    """Server version and extensions, which are the likeliest reason this
    passes on one machine and fails on another."""
    try:
        engine = create_engine(url)
        with engine.connect() as connection:
            version = connection.execute(text("SELECT version()")).scalar_one()
            present = set(connection.execute(text("SELECT extname FROM pg_extension")).scalars())
        engine.dispose()
    except Exception as exc:
        return f"could not describe the server: {exc}"

    missing = [e for e in REQUIRED_EXTENSIONS if e not in present]
    return f"{version}\nmissing extensions: {missing or 'none'}"


@pytest.fixture(scope="session")
def migrated_engine() -> Iterator[Engine]:
    url = _base_url()
    admin = create_engine(_with_database(url, "postgres"), isolation_level="AUTOCOMMIT")

    try:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DATABASE}" WITH (FORCE)'))
            connection.execute(text(f'CREATE DATABASE "{TEST_DATABASE}"'))
    except Exception as exc:
        pytest.skip(f"no reachable Postgres at {urlsplit(url).netloc}: {exc}")
    finally:
        admin.dispose()

    # Migration 0001 asserts the extensions exist and deliberately does not
    # create them: provisioning is the image's job, not a migration's. A
    # database created a moment ago has none of them, so the harness stands in
    # for the image's init here. Anything that cannot be installed is a real gap
    # in the environment, and the migration's assertion will say which.
    provisioning = create_engine(url, isolation_level="AUTOCOMMIT")
    with provisioning.connect() as connection:
        for extension in REQUIRED_EXTENSIONS:
            connection.execute(text(f"CREATE EXTENSION IF NOT EXISTS {extension}"))
    provisioning.dispose()

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI), "upgrade", "head"],
        cwd=REPO_ROOT,
        env={**os.environ, "DATABASE_URL": url},
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(
            f"migrations failed against {urlsplit(url).netloc}\n"
            f"{_server_description(url)}\n{result.stdout}\n{result.stderr}"
        )

    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def db(migrated_engine: Engine) -> Iterator[Connection]:
    """One transaction per test, rolled back at the end.

    Triggers and constraints fire inside the transaction, so everything these
    tests care about is visible. A test needing to observe another transaction's
    commit would need a different fixture, and none does yet.
    """
    connection = migrated_engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()
