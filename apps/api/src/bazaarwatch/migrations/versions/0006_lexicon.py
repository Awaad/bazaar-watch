"""Lexicon: chain-scoped receipt-line to product mapping

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-20

One table. Constraint expressions are literals rather than rendered from the
enums, for the reason in 0003.

`raw_text_key_is_folded` is an addition to `docs/03-data-model.md`. The document
says `key_value` holds Turkish-folded text for that kind and nothing enforced
it. An unfolded entry is not wrong in any visible way: it simply never matches,
so the operator who wrote it sees their mapping silently ignored. `turkish_fold`
is IMMUTABLE, which is what lets a CHECK say it.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chain_lexicon",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("chain_id", sa.Uuid(), nullable=False),
        sa.Column("key_kind", sa.String(length=16), nullable=False),
        sa.Column("key_value", sa.String(length=200), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column(
            "confidence",
            sa.Numeric(precision=4, scale=3),
            server_default=sa.text("1.000"),
            nullable=False,
        ),
        sa.Column("decided_by", sa.Uuid(), nullable=False),
        sa.Column("decided_via", sa.String(length=16), nullable=False),
        sa.Column(
            "status", sa.String(length=16), server_default=sa.text("'active'"), nullable=False
        ),
        sa.Column("superseded_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("key_kind IN ('sku', 'raw_text')", name="key_kind_known"),
        sa.CheckConstraint("decided_via IN ('operator', 'review_t1')", name="decided_via_known"),
        sa.CheckConstraint("status IN ('active', 'superseded')", name="status_known"),
        sa.CheckConstraint("confidence BETWEEN 0 AND 1", name="confidence_in_range"),
        sa.CheckConstraint("length(key_value) > 0", name="key_value_is_not_empty"),
        sa.CheckConstraint(
            "key_kind <> 'raw_text' OR key_value = turkish_fold(key_value)",
            name="raw_text_key_is_folded",
        ),
        sa.CheckConstraint(
            "superseded_by IS NULL OR status = 'superseded'",
            name="successor_implies_superseded",
        ),
        sa.CheckConstraint(
            "superseded_by IS NULL OR superseded_by <> id", name="not_its_own_successor"
        ),
        sa.ForeignKeyConstraint(
            ["chain_id"],
            ["chains.id"],
            name="fk_chain_lexicon_chain_id_chains",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_chain_lexicon_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by"],
            ["users.id"],
            name="fk_chain_lexicon_decided_by_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by"],
            ["chain_lexicon.id"],
            name="fk_chain_lexicon_superseded_by_chain_lexicon",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chain_lexicon"),
    )
    # One active entry per key. Superseded history accumulates without limit,
    # which is the point: a mapping decision is evidence.
    op.create_index(
        "uq_chain_lexicon_active",
        "chain_lexicon",
        ["chain_id", "key_kind", "key_value"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index("ix_chain_lexicon_product_id", "chain_lexicon", ["product_id"])


def downgrade() -> None:
    op.drop_table("chain_lexicon")
