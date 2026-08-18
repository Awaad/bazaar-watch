from __future__ import annotations

import pytest
from pydantic import ValidationError

from bazaarwatch.core.settings import Environment, Settings


def test_missing_required_settings_fail_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing DSN must fail at startup, not fall back to something that
    happens to work on one machine."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_are_frozen(settings: Settings) -> None:
    with pytest.raises(ValidationError):
        settings.api_port = 1  # type: ignore[misc]


def test_is_production_only_for_production(settings: Settings) -> None:
    assert settings.is_production is False
    assert settings.model_copy(update={"environment": Environment.PRODUCTION}).is_production is True
