"""Tuning constants.

Economy amounts, integrity thresholds, review quorum and bounty weights live in
validated data, not in code and not in a DDL default. Every one of them will be
wrong on the first attempt and several will change weekly during early
operation, and retuning must never require a deploy or a migration. See
ADR-0021.

This is not configuration. Environment configuration is provider selection,
credentials and endpoints, and lives in `settings`. Tuning is data with a
schema, deployed independently of code and reviewable as a diff.

Validation is strict: a malformed tuning file is a startup failure, because the
alternative is a process running on silently wrong constants.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from bazaarwatch.core.settings import get_settings


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ReviewTuning(_Frozen):
    """Quorum and reviewer weighting. See ADR-0049, ADR-0061."""

    required_responses: int = Field(ge=1, le=10)
    agreement_threshold: float = Field(gt=0.0, le=1.0)
    reviewer_weight_seed: float = Field(gt=0.0, le=1.0)
    reviewer_weight_max: float = Field(gt=0.0, le=1.0)
    honeypot_rate: float = Field(ge=0.0, le=1.0)
    lease_ttl_seconds: int = Field(ge=30, le=3600)


class EconomyTuning(_Frozen):
    """Points amounts. Award on acceptance, never on submission. See ADR-0019,
    ADR-0020, ADR-0050."""

    submission_provisional_points: int = Field(ge=0)
    submission_confirmed_points: int = Field(ge=0)
    review_resolved_points: int = Field(ge=0)
    lexicon_first_resolution_points: int = Field(ge=0)


class BountyTuning(_Frozen):
    """Reward tracks marginal information value, not volume. See ADR-0020."""

    empty_cell_multiplier: float = Field(ge=1.0)
    stale_cell_multiplier: float = Field(ge=1.0)
    max_multiplier: float = Field(ge=1.0)
    staleness_days: int = Field(ge=1)


class IntegrityTuning(_Frozen):
    """Signal thresholds. Nothing here rejects on its own. See ADR-0018."""

    location_match_metres: int = Field(ge=10, le=2000)
    reward_recency_window_days: int = Field(ge=1)
    dual_extraction_value_minor: int = Field(ge=0)


class Tuning(_Frozen):
    version: int = Field(ge=1)
    review: ReviewTuning
    economy: EconomyTuning
    bounty: BountyTuning
    integrity: IntegrityTuning


def load_tuning(path: Path) -> Tuning:
    """Read and validate. Raises rather than falling back to defaults: a process
    running on silently wrong constants is worse than one that does not start."""
    source = path
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"tuning file not found: {source}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"tuning file is not valid JSON: {source}: {exc}") from exc
    return Tuning.model_validate(raw)


@lru_cache(maxsize=1)
def get_tuning() -> Tuning:
    """Read once per process. Retuning is a redeploy of the data file, which is
    still neither a code deploy nor a migration."""
    return load_tuning(get_settings().tuning_path)
