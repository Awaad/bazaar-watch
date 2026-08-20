"""Geo: chains, branches, candidates, attribute ratings

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-20

Four tables and the PostGIS geography column the rest of the system's
reachability logic depends on.

Constraint expressions are written out as literals rather than rendered from
the enums. A revision that imported today's `BranchKind` would emit tomorrow's
schema for yesterday's history. The `enum-parity` gate is what keeps the
literals honest.

`spatial_index=False` on every Geography column is required, not stylistic.
GeoAlchemy2 otherwise attaches an index named `idx_<table>_<column>` to the
table at construction time, Alembic creates indexes attached to a table it
creates, and the result is two GIST indexes with one of them outside
NAMING_CONVENTION. Both indexes here are declared explicitly below.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_POINT_4326 = Geography(geometry_type="POINT", srid=4326, spatial_index=False)

_UPDATED_AT_TABLES = ("chains", "branches", "branch_candidates")


def upgrade() -> None:
    op.create_table(
        "chains",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        # Receipt layout follows the POS vendor, not the fascia.
        sa.Column("pos_vendor", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chains"),
        sa.UniqueConstraint("slug", name="uq_chains_slug"),
    )

    op.create_table(
        "branches",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("chain_id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "branch_kind",
            sa.String(length=16),
            server_default=sa.text("'physical'"),
            nullable=False,
        ),
        sa.Column("geom", _POINT_4326, nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("source_provider", sa.String(length=32), nullable=True),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column("source_confidence", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column(
            "operating_status",
            sa.String(length=24),
            server_default=sa.text("'open'"),
            nullable=False,
        ),
        sa.Column(
            "verified_by_human",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("verified_by", sa.Uuid(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("branch_kind IN ('physical', 'online')", name="branch_kind_known"),
        sa.CheckConstraint(
            "operating_status IN ('open', 'temporarily_closed', 'permanently_closed')",
            name="status_known",
        ),
        sa.CheckConstraint(
            "branch_kind <> 'physical' OR geom IS NOT NULL", name="physical_has_geom"
        ),
        sa.CheckConstraint("branch_kind <> 'online' OR geom IS NULL", name="online_has_no_geom"),
        sa.CheckConstraint(
            "NOT verified_by_human OR (verified_by IS NOT NULL AND verified_at IS NOT NULL)",
            name="verification_has_an_actor",
        ),
        sa.CheckConstraint(
            "source_confidence IS NULL OR source_confidence BETWEEN 0 AND 1",
            name="confidence_in_range",
        ),
        sa.ForeignKeyConstraint(
            ["chain_id"],
            ["chains.id"],
            name="fk_branches_chain_id_chains",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["verified_by"],
            ["users.id"],
            name="fk_branches_verified_by_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_branches"),
        sa.UniqueConstraint("slug", name="uq_branches_slug"),
    )
    # Partial: manually entered branches carry no source key and must not
    # collide with each other.
    op.create_index(
        "uq_branches_source",
        "branches",
        ["source_provider", "source_id"],
        unique=True,
        postgresql_where=sa.text("source_id IS NOT NULL"),
    )
    op.create_index("ix_branches_geom", "branches", ["geom"], postgresql_using="gist")
    op.create_index("ix_branches_chain_id", "branches", ["chain_id"])

    op.create_table(
        "branch_candidates",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("source_provider", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("geom", _POINT_4326, nullable=True),
        sa.Column("suggested_chain_id", sa.Uuid(), nullable=True),
        sa.Column("operating_status", sa.String(length=24), nullable=True),
        sa.Column("source_confidence", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("promoted_branch_id", sa.Uuid(), nullable=True),
        sa.Column("duplicate_of_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'promoted', 'rejected', 'duplicate')",
            name="status_known",
        ),
        sa.CheckConstraint(
            "operating_status IS NULL OR operating_status IN "
            "('open', 'temporarily_closed', 'permanently_closed')",
            name="status_known_if_present",
        ),
        sa.CheckConstraint(
            "source_confidence IS NULL OR source_confidence BETWEEN 0 AND 1",
            name="confidence_in_range",
        ),
        sa.CheckConstraint(
            "(status = 'promoted') = (promoted_branch_id IS NOT NULL)",
            name="promoted_iff_branch",
        ),
        sa.CheckConstraint(
            "(status = 'duplicate') = (duplicate_of_id IS NOT NULL)",
            name="duplicate_iff_survivor",
        ),
        sa.CheckConstraint(
            "duplicate_of_id IS NULL OR duplicate_of_id <> id",
            name="not_its_own_duplicate",
        ),
        sa.ForeignKeyConstraint(
            ["suggested_chain_id"],
            ["chains.id"],
            name="fk_branch_candidates_suggested_chain_id_chains",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["promoted_branch_id"],
            ["branches.id"],
            name="fk_branch_candidates_promoted_branch_id_branches",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["duplicate_of_id"],
            ["branch_candidates.id"],
            name="fk_branch_candidates_duplicate_of_id_branch_candidates",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_branch_candidates"),
    )
    # Total, not partial: the pipeline upserts on this key, so both parts are
    # NOT NULL and every candidate has one.
    op.create_index(
        "uq_branch_candidates_source",
        "branch_candidates",
        ["source_provider", "source_id"],
        unique=True,
    )
    op.create_index("ix_branch_candidates_status", "branch_candidates", ["status"])

    op.create_table(
        "branch_attribute_ratings",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("contributor_id", sa.Uuid(), nullable=False),
        sa.Column("dimension", sa.String(length=24), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "dimension IN ('produce_freshness', 'stock_breadth', 'queue_length')",
            name="dimension_known",
        ),
        sa.CheckConstraint("score BETWEEN 1 AND 5", name="score_in_range"),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_branch_attribute_ratings_branch_id_branches",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["contributor_id"],
            ["users.id"],
            name="fk_branch_attribute_ratings_contributor_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_branch_attribute_ratings"),
    )
    # An idempotency guard against a resubmitted rating, not a rate limit. The
    # aggregate counts one rating per contributor per dimension; see ADR-0052
    # and docs/03-data-model.md section 4.
    op.create_index(
        "uq_branch_attribute_ratings_submission",
        "branch_attribute_ratings",
        ["branch_id", "contributor_id", "dimension", "observed_at"],
        unique=True,
    )
    op.create_index(
        "ix_branch_attribute_ratings_recent",
        "branch_attribute_ratings",
        ["branch_id", "dimension", sa.text("observed_at DESC")],
    )

    # updated_at is maintained by the database, not the application. An
    # application-maintained timestamp is wrong the moment anything writes
    # outside the ORM, which migrations and operational fixes both do.
    for table in _UPDATED_AT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def downgrade() -> None:
    for table in reversed(_UPDATED_AT_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")

    # Dependency order: ratings and candidates both reference branches, and
    # branches references chains.
    op.drop_table("branch_attribute_ratings")
    op.drop_table("branch_candidates")
    op.drop_table("branches")
    op.drop_table("chains")
