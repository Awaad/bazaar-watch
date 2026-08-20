"""Geo tables.

Owned by this module. No other module imports these; cross-module access goes
through `service.py`. See docs/15-repo-structure-standards.md section 2.

Two exclusions live on `branches` and both are load-bearing. ADR-0045 keeps
online branches out of indices and comparison; ADR-0023 keeps unverified
branches out of the same. Neither is expressed by querying this file. Index and
comparison code uses the selectables in `service.py`, which is ADR-0088 and is
enforced by the `branch-scope` gate.
"""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import Any

from geoalchemy2 import Geography, WKBElement
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from bazaarwatch.core.enums import SqlStrEnum
from bazaarwatch.core.models import Base, created_at_column, updated_at_column, uuid_pk
from bazaarwatch.core.text import SLUG_MAX_LENGTH

# WGS84 lon/lat on the spheroid. `geography` rather than `geometry` because
# every distance this system asks for is a real distance in metres, and
# ST_DWithin on geography answers that directly instead of via a projection
# nobody would remember to choose. See ADR-0035.
POINT_4326 = Geography(
    geometry_type="POINT",
    srid=4326,
    # Not the default. GeoAlchemy2 otherwise attaches an index named
    # `idx_branches_geom` to the table at construction, which bypasses
    # NAMING_CONVENTION, and Alembic creates indexes attached to a table it
    # creates. The result is two GIST indexes, one of them under a name the
    # downgrade does not know. The index is declared explicitly below.
    spatial_index=False,
)


class BranchKind(SqlStrEnum):
    PHYSICAL = "physical"
    # Real price source, no geometry, excluded from indices and from
    # access-scoped comparison. See ADR-0045.
    ONLINE = "online"


class OperatingStatus(SqlStrEnum):
    OPEN = "open"
    TEMPORARILY_CLOSED = "temporarily_closed"
    PERMANENTLY_CLOSED = "permanently_closed"


class CandidateStatus(SqlStrEnum):
    PENDING = "pending"
    PROMOTED = "promoted"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"


class AttributeDimension(SqlStrEnum):
    """Fixed ordinal dimensions, no free text. See ADR-0052."""

    PRODUCE_FRESHNESS = "produce_freshness"
    STOCK_BREADTH = "stock_breadth"
    QUEUE_LENGTH = "queue_length"


class SourceProvider(SqlStrEnum):
    """Where a branch or candidate came from.

    No CHECK constraint backs this one yet, deliberately: adding it is a schema
    change beyond the six agreed for this slice. It is the vocabulary the
    pipeline and the operator paths write, and promoting it to a constraint is
    a one-line migration whenever that is agreed.
    """

    OVERTURE = "overture"
    MANUAL = "manual"
    SCRAPE = "scrape"


# 0 to 1. Provider confidence measures record quality, not whether the shop is
# open today, which is why it can never drive promotion (ADR-0011, ADR-0023).
_CONFIDENCE_RANGE = "source_confidence IS NULL OR source_confidence BETWEEN 0 AND 1"


class Chain(Base):
    __tablename__ = "chains"

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(SLUG_MAX_LENGTH), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Receipt layout follows the POS vendor, not the fascia. Two chains on the
    # same POS print the same shape, and one chain mid-migration prints two.
    pos_vendor: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[dt.datetime] = created_at_column()
    updated_at: Mapped[dt.datetime] = updated_at_column()


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[uuid.UUID] = uuid_pk()
    chain_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("chains.id", ondelete="RESTRICT"), nullable=False
    )
    # Globally unique, so it carries its chain: `lemar-girne-merkez`.
    slug: Mapped[str] = mapped_column(String(SLUG_MAX_LENGTH), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    branch_kind: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=BranchKind.PHYSICAL.value
    )
    geom: Mapped[WKBElement | None] = mapped_column(POINT_4326)
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    source_provider: Mapped[str | None] = mapped_column(String(32))
    source_id: Mapped[str | None] = mapped_column(String(128))
    source_confidence: Mapped[Decimal | None] = mapped_column(Numeric(precision=4, scale=3))
    operating_status: Mapped[str] = mapped_column(
        String(24), nullable=False, server_default=OperatingStatus.OPEN.value
    )
    # The gate on every published figure. See ADR-0023.
    verified_by_human: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    verified_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = created_at_column()
    updated_at: Mapped[dt.datetime] = updated_at_column()

    __table_args__ = (
        CheckConstraint(BranchKind.sql_check("branch_kind"), name="branch_kind_known"),
        CheckConstraint(OperatingStatus.sql_check("operating_status"), name="status_known"),
        # Both directions. A physical branch without geometry is invisible to
        # reachability; an online branch with geometry would silently enter it.
        CheckConstraint(
            "branch_kind <> 'physical' OR geom IS NOT NULL",
            name="physical_has_geom",
        ),
        CheckConstraint(
            "branch_kind <> 'online' OR geom IS NULL",
            name="online_has_no_geom",
        ),
        # Verification is an operator action with an actor and a time. A true
        # flag with neither recorded is a claim nobody made.
        CheckConstraint(
            "NOT verified_by_human OR (verified_by IS NOT NULL AND verified_at IS NOT NULL)",
            name="verification_has_an_actor",
        ),
        CheckConstraint(_CONFIDENCE_RANGE, name="confidence_in_range"),
        # Partial: manually entered branches have no source and would otherwise
        # collide with each other on (NULL, NULL) under some engines.
        Index(
            "uq_branches_source",
            "source_provider",
            "source_id",
            unique=True,
            postgresql_where=text("source_id IS NOT NULL"),
        ),
        Index("ix_branches_geom", "geom", postgresql_using="gist"),
        Index("ix_branches_chain_id", "chain_id"),
    )


class BranchCandidate(Base):
    """Pipeline output. Never joined to prices. Promotion is explicit.

    A separate table rather than a flag on `branches`, because one forgotten
    predicate on a mixed table puts an unverified row into a price join. See
    ADR-0023.
    """

    __tablename__ = "branch_candidates"

    id: Mapped[uuid.UUID] = uuid_pk()
    source_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    # The provider payload as received. Kept so a promotion decision can be
    # re-examined against what the pipeline actually saw.
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    name: Mapped[str | None] = mapped_column(String(200))
    geom: Mapped[WKBElement | None] = mapped_column(POINT_4326)
    suggested_chain_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("chains.id", ondelete="RESTRICT")
    )
    operating_status: Mapped[str | None] = mapped_column(String(24))
    source_confidence: Mapped[Decimal | None] = mapped_column(Numeric(precision=4, scale=3))
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=CandidateStatus.PENDING.value
    )
    promoted_branch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("branches.id", ondelete="RESTRICT")
    )
    # The survivor. ADR-0023 says a duplicate is marked with a reference to it,
    # so that a re-run does not resurrect the row and an operator can see what
    # it was folded into.
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("branch_candidates.id", ondelete="RESTRICT")
    )
    created_at: Mapped[dt.datetime] = created_at_column()
    # Re-runs upsert on the source key and operators move status, so the row
    # mutates. Without this there is no way to tell when a candidate last
    # changed, and deprioritising stale candidates has nothing to sort on.
    updated_at: Mapped[dt.datetime] = updated_at_column()

    __table_args__ = (
        CheckConstraint(CandidateStatus.sql_check("status"), name="status_known"),
        # Nullable, because a provider may say nothing about it. When it does
        # say something, the ingest stage normalises to our vocabulary rather
        # than storing the provider's spelling.
        CheckConstraint(
            f"operating_status IS NULL OR {OperatingStatus.sql_check('operating_status')}",
            name="status_known_if_present",
        ),
        CheckConstraint(_CONFIDENCE_RANGE, name="confidence_in_range"),
        # Both directions, so a rejected candidate cannot carry a branch
        # reference and a promoted one cannot lack it.
        CheckConstraint(
            "(status = 'promoted') = (promoted_branch_id IS NOT NULL)",
            name="promoted_iff_branch",
        ),
        CheckConstraint(
            "(status = 'duplicate') = (duplicate_of_id IS NOT NULL)",
            name="duplicate_iff_survivor",
        ),
        # Following the survivor chain must terminate.
        CheckConstraint(
            "duplicate_of_id IS NULL OR duplicate_of_id <> id",
            name="not_its_own_duplicate",
        ),
        Index(
            "uq_branch_candidates_source",
            "source_provider",
            "source_id",
            unique=True,
        ),
        Index("ix_branch_candidates_status", "status"),
    )


class BranchAttributeRating(Base):
    """Ordinal store attributes. See ADR-0052.

    Rigorously excluded from any index computation: a subjective quality rating
    contaminating a published inflation figure would destroy its defensibility.

    The unique key is an idempotency guard against a resubmitted rating, not a
    rate limit. It cannot be one: the same contributor can rate the same branch
    fifty times a day at different timestamps and every row is legal. The
    aggregate handles it instead, by counting one rating per contributor per
    dimension, the most recent within the window. Fifty submissions become one
    vote and manipulation needs multiple accounts, which is the general problem
    the trust model already carries.
    """

    __tablename__ = "branch_attribute_ratings"

    id: Mapped[uuid.UUID] = uuid_pk()
    branch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False
    )
    contributor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    dimension: Mapped[str] = mapped_column(String(24), nullable=False)
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # Client-supplied: when the contributor was in the shop, not when the row
    # arrived. `created_at` is the latter.
    observed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[dt.datetime] = created_at_column()

    __table_args__ = (
        CheckConstraint(AttributeDimension.sql_check("dimension"), name="dimension_known"),
        CheckConstraint("score BETWEEN 1 AND 5", name="score_in_range"),
        Index(
            "uq_branch_attribute_ratings_submission",
            "branch_id",
            "contributor_id",
            "dimension",
            "observed_at",
            unique=True,
        ),
        # Recency-weighted reads walk backwards from now.
        Index(
            "ix_branch_attribute_ratings_recent",
            "branch_id",
            "dimension",
            text("observed_at DESC"),
        ),
    )


__all__ = [
    "AttributeDimension",
    "Branch",
    "BranchAttributeRating",
    "BranchCandidate",
    "BranchKind",
    "CandidateStatus",
    "Chain",
    "OperatingStatus",
    "SourceProvider",
]
