"""Catalog: brands, products, codes, aliases, groups, collections, search docs

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-20

Ten tables. Constraint expressions are literals rather than rendered from the
enums, for the reason in 0003: a revision importing today's class would emit
tomorrow's schema for yesterday's history. `enum-parity` keeps them honest.

Two departures from `docs/03-data-model.md` as originally written, both agreed
and both now in the document:

`products.owner_chain_id` is gone. Private label is a property of the brand, and
a private-label product always has one, so recording the owner twice was two
places for one fact that could disagree.

`product_search_docs.model_version` is nullable and paired with a biconditional.
Every row written before a model is chosen would have needed a placeholder, and
a placeholder in a NOT NULL column is a lie the schema tells.

The embedding column is unpinned per ADR-0024 and held empty by
`embedding_is_unset`. An unpinned `vector` accepts a 768-dimension row beside a
1024-dimension one silently, and the failure would surface much later as an
`ALTER TYPE` that cannot succeed. The migration that pins the dimension drops
that constraint and creates the HNSW index in the same change.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UPDATED_AT_TABLES = ("products", "product_search_docs")


def _created_at() -> sa.Column[dt.datetime]:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )


def _updated_at() -> sa.Column[dt.datetime]:
    return sa.Column(
        "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "brands",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "is_private_label", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("owner_chain_id", sa.Uuid(), nullable=True),
        _created_at(),
        sa.CheckConstraint(
            "NOT is_private_label OR owner_chain_id IS NOT NULL", name="private_label_has_owner"
        ),
        sa.CheckConstraint(
            "is_private_label OR owner_chain_id IS NULL", name="owner_implies_private_label"
        ),
        sa.ForeignKeyConstraint(
            ["owner_chain_id"],
            ["chains.id"],
            name="fk_brands_owner_chain_id_chains",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_brands"),
        sa.UniqueConstraint("slug", name="uq_brands_slug"),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("canonical_name", sa.String(length=300), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("net_content_value", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("net_content_uom", sa.String(length=8), nullable=True),
        sa.Column(
            "unit_basis",
            sa.String(length=16),
            server_default=sa.text("'per_piece'"),
            nullable=False,
        ),
        sa.Column(
            "source", sa.String(length=16), server_default=sa.text("'operator'"), nullable=False
        ),
        sa.Column(
            "verification_state",
            sa.String(length=16),
            server_default=sa.text("'unverified'"),
            nullable=False,
        ),
        sa.Column(
            "status", sa.String(length=16), server_default=sa.text("'active'"), nullable=False
        ),
        sa.Column("merged_into_id", sa.Uuid(), nullable=True),
        _created_at(),
        _updated_at(),
        sa.CheckConstraint(
            "unit_basis IN ('per_l', 'per_kg', 'per_piece')", name="unit_basis_known"
        ),
        sa.CheckConstraint(
            "net_content_uom IS NULL OR net_content_uom IN ('g', 'kg', 'ml', 'l', 'piece')",
            name="uom_known_if_present",
        ),
        sa.CheckConstraint("source IN ('operator', 'scrape', 'contributor')", name="source_known"),
        sa.CheckConstraint(
            "verification_state IN ('unverified', 'verified')", name="verification_state_known"
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'merged', 'retired')", name="status_known"
        ),
        sa.CheckConstraint(
            "unit_basis = 'per_piece' "
            "OR (net_content_value IS NOT NULL AND net_content_uom IS NOT NULL)",
            name="unit_basis_needs_net_content",
        ),
        sa.CheckConstraint(
            "net_content_value IS NULL OR net_content_value > 0", name="net_content_is_positive"
        ),
        sa.CheckConstraint(
            "(status = 'merged') = (merged_into_id IS NOT NULL)", name="merged_iff_target"
        ),
        sa.CheckConstraint(
            "merged_into_id IS NULL OR merged_into_id <> id", name="not_merged_into_itself"
        ),
        sa.ForeignKeyConstraint(
            ["brand_id"], ["brands.id"], name="fk_products_brand_id_brands", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_products_category_id_categories",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["merged_into_id"],
            ["products.id"],
            name="fk_products_merged_into_id_products",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
        sa.UniqueConstraint("slug", name="uq_products_slug"),
    )
    op.create_index("ix_products_category_id", "products", ["category_id"])
    op.create_index("ix_products_brand_id", "products", ["brand_id"])

    op.create_table(
        "product_gtins",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("gtin", sa.String(length=64), nullable=False),
        sa.Column("gtin_kind", sa.String(length=16), nullable=False),
        sa.Column("chain_id", sa.Uuid(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        _created_at(),
        sa.CheckConstraint(
            "gtin_kind IN ('ean13', 'ean8', 'upc', 'plu', 'chain_internal')",
            name="gtin_kind_known",
        ),
        sa.CheckConstraint(
            "gtin_kind <> 'chain_internal' OR chain_id IS NOT NULL",
            name="internal_gtin_is_chain_scoped",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_product_gtins_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["chain_id"],
            ["chains.id"],
            name="fk_product_gtins_chain_id_chains",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_product_gtins"),
    )
    op.create_index(
        "uq_product_gtins_global",
        "product_gtins",
        ["gtin", "gtin_kind"],
        unique=True,
        postgresql_where=sa.text("gtin_kind <> 'chain_internal'"),
    )
    op.create_index(
        "uq_product_gtins_chain",
        "product_gtins",
        ["chain_id", "gtin"],
        unique=True,
        postgresql_where=sa.text("gtin_kind = 'chain_internal'"),
    )
    # One primary code per product. Without this, "the barcode to print" has
    # several answers and no way to choose between them.
    op.create_index(
        "uq_product_gtins_primary",
        "product_gtins",
        ["product_id"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )

    op.create_table(
        "product_aliases",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("alias_text", sa.String(length=200), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column(
            "status", sa.String(length=16), server_default=sa.text("'active'"), nullable=False
        ),
        _created_at(),
        sa.CheckConstraint("locale IN ('tr', 'en', 'ru', 'de', 'ar')", name="locale_known"),
        sa.CheckConstraint(
            "source IN ('operator', 'contributor', 'mined', 'lexicon')", name="source_known"
        ),
        sa.CheckConstraint("status IN ('pending', 'active', 'rejected')", name="status_known"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_product_aliases_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_product_aliases"),
        sa.UniqueConstraint("product_id", "locale", "alias_text", name="uq_product_aliases_text"),
    )
    op.create_index("ix_product_aliases_product_id", "product_aliases", ["product_id"])

    op.create_table(
        "product_facets",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("facet", sa.String(length=32), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_product_facets_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("product_id", "facet", name="pk_product_facets"),
    )
    op.create_index("ix_product_facets_facet", "product_facets", ["facet"])

    op.create_table(
        "product_groups",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_product_groups"),
        sa.UniqueConstraint("slug", name="uq_product_groups_slug"),
    )
    op.create_table(
        "product_group_members",
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["product_groups.id"],
            name="fk_product_group_members_group_id_product_groups",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_product_group_members_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("group_id", "product_id", name="pk_product_group_members"),
    )

    op.create_table(
        "collections",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name_i18n", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        _created_at(),
        sa.CheckConstraint("name_i18n ? 'tr'", name="has_turkish_name"),
        sa.PrimaryKeyConstraint("id", name="pk_collections"),
        sa.UniqueConstraint("slug", name="uq_collections_slug"),
    )
    op.create_table(
        "collection_members",
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collections.id"],
            name="fk_collection_members_collection_id_collections",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_collection_members_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("collection_id", "product_id", name="pk_collection_members"),
    )

    op.create_table(
        "product_search_docs",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("lexical_text", sa.Text(), nullable=False),
        sa.Column("semantic_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        _updated_at(),
        sa.CheckConstraint("embedding IS NULL", name="embedding_is_unset"),
        sa.CheckConstraint(
            "(embedding IS NULL) = (model_version IS NULL)", name="model_version_iff_embedding"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_product_search_docs_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("product_id", name="pk_product_search_docs"),
    )
    op.execute(
        "CREATE INDEX ix_product_search_docs_lexical ON product_search_docs "
        "USING GIN (lexical_text gin_trgm_ops)"
    )

    for table in _UPDATED_AT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def downgrade() -> None:
    for table in reversed(_UPDATED_AT_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")

    op.drop_table("product_search_docs")
    op.drop_table("collection_members")
    op.drop_table("collections")
    op.drop_table("product_group_members")
    op.drop_table("product_groups")
    op.drop_table("product_facets")
    op.drop_table("product_aliases")
    op.drop_table("product_gtins")
    op.drop_table("products")
    op.drop_table("brands")
