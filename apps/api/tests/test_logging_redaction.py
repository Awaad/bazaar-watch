from __future__ import annotations

import pytest

from bazaarwatch.core.logging import REDACTED_KEYS, _redact


@pytest.mark.parametrize("key", sorted(REDACTED_KEYS))
def test_sensitive_keys_are_redacted(key: str) -> None:
    """Redaction happens at the processor, so a field cannot leak because
    someone raised the log level during an incident."""
    out = _redact(None, "info", {"event": "x", key: "sensitive"})
    assert out[key] == "[redacted]"


def test_redaction_is_case_insensitive() -> None:
    out = _redact(None, "info", {"Authorization": "Bearer x"})
    assert out["Authorization"] == "[redacted]"


def test_ordinary_fields_survive() -> None:
    out = _redact(None, "info", {"event": "x", "branch_id": "abc"})
    assert out["branch_id"] == "abc"
