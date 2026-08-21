"""Ingest and observations: submissions through price observations

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-20

Six tables, and the last of Checkpoint A.

`receipt_lines.tax_rate_bp` is an addition to `docs/03-data-model.md`, made after
reading a real receipt. Every line printed its own KDV rate, and the rate is the
only printed per-line value the schema had nowhere to put. It cannot be
recovered later: the mapped product's category is a proxy that fails precisely
across a rate change, and the original image is on a retention clock (ADR-0016).

This file was emitted from the models and then read, rather than retyped.
Six tables of constraints is enough transcription for a typo to survive
review, and a CHECK that is subtly different from the one the ORM
describes is invisible until autogenerate proposes a change nobody
ordered. Constraint text is still literal here, for the reason in 0003.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UPDATED_AT_TABLES = ("submissions",)


def upgrade() -> None:
    op.create_table(
        "submissions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("contributor_id", sa.Uuid(), nullable=False),
        sa.Column("client_idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("claimed_branch_id", sa.Uuid(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("location_matched", sa.Boolean(), nullable=True),
        sa.Column("location_confidence", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column(
            "status", sa.String(length=16), server_default=sa.text("'received'"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("'now()'"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("'now()'"),
            nullable=False,
        ),
        sa.CheckConstraint("channel IN ('app', 'console', 'scrape')", name="channel_known"),
        sa.CheckConstraint(
            "location_confidence IS NULL OR location_confidence BETWEEN 0 AND 1",
            name="confidence_in_range",
        ),
        sa.CheckConstraint(
            "kind IN ('receipt', 'shelf_manual', 'shelf_barcode')", name="kind_known"
        ),
        sa.CheckConstraint(
            "(location_matched IS NULL) = (location_confidence IS NULL)",
            name="location_verdict_is_complete",
        ),
        sa.CheckConstraint(
            "status IN ('received', 'extracting', 'extracted', 'in_review', "
            "'accepted', 'rejected', 'failed')",
            name="status_known",
        ),
        sa.ForeignKeyConstraint(
            ["claimed_branch_id"],
            ["branches.id"],
            name="fk_submissions_claimed_branch_id_branches",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["contributor_id"],
            ["users.id"],
            name="fk_submissions_contributor_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_submissions"),
        sa.UniqueConstraint("client_idempotency_key", name="uq_submissions_client_idempotency_key"),
    )
    op.create_index("ix_submissions_contributor_id", "submissions", ["contributor_id"])
    op.create_index("ix_submissions_status", "submissions", ["status"])

    op.create_table(
        "media_objects",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("bucket", sa.String(length=63), nullable=False),
        sa.Column("object_key", sa.String(length=1024), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("reencoded", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("subject_user_id", sa.Uuid(), nullable=False),
        sa.Column("wrapped_dek", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("'now()'"),
            nullable=False,
        ),
        sa.CheckConstraint("byte_size > 0", name="byte_size_is_positive"),
        sa.CheckConstraint("length(wrapped_dek) > 0", name="dek_is_present"),
        sa.CheckConstraint("(width IS NULL) = (height IS NULL)", name="dimensions_are_paired"),
        sa.CheckConstraint(
            "width IS NULL OR (width > 0 AND height > 0)", name="dimensions_are_positive"
        ),
        sa.CheckConstraint("role IN ('original', 'crop')", name="role_known"),
        sa.ForeignKeyConstraint(
            ["subject_user_id"],
            ["users.id"],
            name="fk_media_objects_subject_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submissions.id"],
            name="fk_media_objects_submission_id_submissions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_media_objects"),
        sa.UniqueConstraint("bucket", "object_key", name="uq_media_objects_location"),
    )
    op.create_index(
        "ix_media_objects_content_hash",
        "media_objects",
        ["content_hash"],
        postgresql_where=sa.text("role = 'original'"),
    )
    op.create_index("ix_media_objects_subject_user_id", "media_objects", ["subject_user_id"])

    op.create_table(
        "extraction_runs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("extraction_method", sa.String(length=64), nullable=False),
        sa.Column("extraction_version", sa.String(length=64), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("superseded_by", sa.Uuid(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status", sa.String(length=16), server_default=sa.text("'running'"), nullable=False
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at", name="completed_after_started"
        ),
        sa.CheckConstraint(
            "superseded_by IS NULL OR superseded_by <> id", name="not_its_own_successor"
        ),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed', 'superseded')", name="status_known"
        ),
        sa.CheckConstraint(
            "superseded_by IS NULL OR status = 'superseded'", name="successor_implies_superseded"
        ),
        sa.CheckConstraint(
            "NOT is_current OR status <> 'superseded'", name="superseded_is_not_current"
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submissions.id"],
            name="fk_extraction_runs_submission_id_submissions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by"],
            ["extraction_runs.id"],
            name="fk_extraction_runs_superseded_by_extraction_runs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_extraction_runs"),
        sa.UniqueConstraint(
            "submission_id",
            "extraction_method",
            "extraction_version",
            name="uq_extraction_runs_attempt",
        ),
    )
    op.create_index(
        "uq_extraction_runs_current",
        "extraction_runs",
        ["submission_id"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )

    op.create_table(
        "receipts",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("extraction_run_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=True),
        sa.Column("receipt_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("printed_total_minor", sa.BigInteger(), nullable=True),
        sa.Column("tax_total_minor", sa.BigInteger(), nullable=True),
        sa.Column("discount_total_minor", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'TRY'"), nullable=False),
        sa.Column("fingerprint", sa.String(length=128), nullable=True),
        sa.Column(
            "reconciliation_status",
            sa.String(length=16),
            server_default=sa.text("'unchecked'"),
            nullable=False,
        ),
        sa.Column("reconciliation_residual_minor", sa.BigInteger(), nullable=True),
        sa.Column(
            "status", sa.String(length=16), server_default=sa.text("'pending'"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("'now()'"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "printed_total_minor IS NULL OR printed_total_minor >= 0",
            name="printed_total_is_not_negative",
        ),
        sa.CheckConstraint(
            "reconciliation_status IN ('unchecked', 'balanced', 'residual', 'unparseable')",
            name="reconciliation_status_known",
        ),
        sa.CheckConstraint(
            "reconciliation_status <> 'residual' OR reconciliation_residual_minor IS NOT NULL",
            name="residual_is_quantified",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'flagged', 'duplicate', 'rejected', 'superseded')",
            name="status_known",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_receipts_branch_id_branches",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["extraction_run_id"],
            ["extraction_runs.id"],
            name="fk_receipts_extraction_run_id_extraction_runs",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submissions.id"],
            name="fk_receipts_submission_id_submissions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_receipts"),
        sa.UniqueConstraint("extraction_run_id", name="uq_receipts_extraction_run_id"),
    )
    op.create_index("ix_receipts_fingerprint", "receipts", ["fingerprint"])
    op.create_index("ix_receipts_submission_id", "receipts", ["submission_id"])

    op.create_table(
        "receipt_lines",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("receipt_id", sa.Uuid(), nullable=False),
        sa.Column("line_index", sa.Integer(), nullable=False),
        sa.Column("line_kind", sa.String(length=16), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("interpreted_text", sa.Text(), nullable=True),
        sa.Column("sku_text", sa.String(length=200), nullable=True),
        sa.Column("raw_quantity", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("raw_uom", sa.String(length=16), nullable=True),
        sa.Column("raw_unit_price_minor", sa.BigInteger(), nullable=True),
        sa.Column("raw_line_total_minor", sa.BigInteger(), nullable=True),
        sa.Column("bbox", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tax_rate_bp", sa.SmallInteger(), nullable=True),
        sa.Column("modifies_line_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("'now()'"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "bbox IS NULL OR jsonb_array_length(bbox) = 4", name="bbox_has_four_values"
        ),
        sa.CheckConstraint(
            "tax_rate_bp IS NULL OR tax_rate_bp BETWEEN 0 AND 10000", name="tax_rate_in_range"
        ),
        sa.CheckConstraint(
            "modifies_line_id IS NULL OR modifies_line_id <> id", name="does_not_modify_itself"
        ),
        sa.CheckConstraint("line_index >= 0", name="line_index_is_not_negative"),
        sa.CheckConstraint(
            "line_kind IN ('item', 'discount', 'subtotal', 'tax', 'tender', 'unknown')",
            name="line_kind_known",
        ),
        sa.CheckConstraint("length(raw_text) > 0", name="raw_text_is_not_empty"),
        sa.ForeignKeyConstraint(
            ["modifies_line_id"],
            ["receipt_lines.id"],
            name="fk_receipt_lines_modifies_line_id_receipt_lines",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["receipts.id"],
            name="fk_receipt_lines_receipt_id_receipts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_receipt_lines"),
        sa.UniqueConstraint("receipt_id", "line_index", name="uq_receipt_lines_index"),
    )

    op.create_table(
        "price_observations",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("source_kind", sa.String(length=16), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'TRY'"), nullable=False),
        sa.Column(
            "quantity",
            sa.Numeric(precision=12, scale=4),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("uom", sa.String(length=16), server_default=sa.text("'piece'"), nullable=False),
        sa.Column("unit_price_minor", sa.BigInteger(), nullable=True),
        sa.Column("unit_basis", sa.String(length=16), nullable=True),
        sa.Column(
            "price_kind", sa.String(length=16), server_default=sa.text("'regular'"), nullable=False
        ),
        sa.Column(
            "status", sa.String(length=16), server_default=sa.text("'pending'"), nullable=False
        ),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("extraction_run_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("'now()'"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1", name="confidence_in_range"
        ),
        sa.CheckConstraint("price_minor >= 0", name="price_is_not_negative"),
        sa.CheckConstraint(
            "price_kind IN ('regular', 'promotional', 'member', 'clearance')",
            name="price_kind_known",
        ),
        sa.CheckConstraint("quantity > 0", name="quantity_is_positive"),
        sa.CheckConstraint(
            "(source_kind = 'receipt_line') = (extraction_run_id IS NOT NULL)",
            name="run_iff_receipt_sourced",
        ),
        sa.CheckConstraint(
            "source_kind IN ('receipt_line', 'shelf_manual', 'shelf_barcode', 'scrape')",
            name="source_kind_known",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'provisional', 'accepted', 'flagged', 'superseded')",
            name="status_known",
        ),
        sa.CheckConstraint(
            "unit_basis IS NULL OR unit_basis IN ('per_l', 'per_kg', 'per_piece')",
            name="unit_basis_known_if_present",
        ),
        sa.CheckConstraint(
            "(unit_price_minor IS NULL) = (unit_basis IS NULL)", name="unit_price_has_a_basis"
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_price_observations_branch_id_branches",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["extraction_run_id"],
            ["extraction_runs.id"],
            name="fk_price_observations_extraction_run_id_extraction_runs",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_price_observations_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_price_observations"),
        sa.UniqueConstraint("source_kind", "source_id", name="uq_price_observations_source"),
    )
    op.create_index(
        "ix_price_observations_branch_product_time",
        "price_observations",
        ["branch_id", "product_id", sa.text("observed_at DESC")],
    )
    op.create_index(
        "ix_price_observations_run",
        "price_observations",
        ["extraction_run_id"],
        postgresql_where=sa.text("extraction_run_id IS NOT NULL"),
    )
    op.create_index(
        "ix_price_observations_unresolved",
        "price_observations",
        ["branch_id", sa.text("observed_at DESC")],
        postgresql_where=sa.text("product_id IS NULL"),
    )

    for table in _UPDATED_AT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def downgrade() -> None:
    for table in reversed(_UPDATED_AT_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")

    op.drop_table("price_observations")
    op.drop_table("receipt_lines")
    op.drop_table("receipts")
    op.drop_table("extraction_runs")
    op.drop_table("media_objects")
    op.drop_table("submissions")
