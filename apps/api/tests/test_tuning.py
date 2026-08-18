from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from bazaarwatch.core.tuning import Tuning, load_tuning

REPO_TUNING = Path("config/tuning.json")


def test_the_committed_tuning_file_is_valid() -> None:
    """The file that ships must load. A malformed one is a startup failure, and
    finding that out in production is the wrong time."""
    tuning = load_tuning(REPO_TUNING)
    assert tuning.version >= 1


def test_missing_file_raises_rather_than_defaulting() -> None:
    """Falling back to defaults would mean a process running on silently wrong
    constants."""
    with pytest.raises(FileNotFoundError):
        load_tuning(Path("config/does-not-exist.json"))


def test_malformed_json_is_reported_as_such(tmp_path: Path) -> None:
    bad = tmp_path / "tuning.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        load_tuning(bad)


def test_unknown_key_is_rejected(tmp_path: Path) -> None:
    """extra='forbid'. A typo in a tuning key must not be silently ignored,
    leaving the intended constant at its old value."""
    raw = json.loads(REPO_TUNING.read_text(encoding="utf-8"))
    raw["review"]["agreemnt_threshold"] = 0.9
    path = tmp_path / "tuning.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_tuning(path)


def test_out_of_range_values_are_rejected(tmp_path: Path) -> None:
    raw = json.loads(REPO_TUNING.read_text(encoding="utf-8"))
    raw["review"]["agreement_threshold"] = 1.5
    path = tmp_path / "tuning.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_tuning(path)


def test_tuning_is_frozen() -> None:
    tuning = load_tuning(REPO_TUNING)
    with pytest.raises(ValidationError):
        tuning.review.required_responses = 5  # type: ignore[misc]


def test_every_section_is_present() -> None:
    """A tuning file missing a section would leave that subsystem without
    constants at the moment it needs them."""
    tuning = load_tuning(REPO_TUNING)
    assert set(Tuning.model_fields) == {
        "version",
        "review",
        "economy",
        "bounty",
        "integrity",
    }
    assert tuning.review.required_responses >= 1
    assert tuning.economy.review_resolved_points >= 0
    assert tuning.bounty.max_multiplier >= tuning.bounty.empty_cell_multiplier
    assert tuning.integrity.location_match_metres > 0
