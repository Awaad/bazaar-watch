from __future__ import annotations

import pytest

from bazaarwatch.core.settings import Environment, Settings


@pytest.fixture
def settings() -> Settings:
    """Settings that never touch a real service. Connection failure is the
    expected path for the readiness tests."""
    return Settings(
        environment=Environment.LOCAL,
        database_url="postgresql+psycopg://u:p@127.0.0.1:1/none",  # type: ignore[arg-type]
        redis_url="redis://127.0.0.1:1/0",  # type: ignore[arg-type]
    )
