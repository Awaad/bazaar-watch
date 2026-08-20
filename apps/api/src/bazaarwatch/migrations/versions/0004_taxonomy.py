"""Taxonomy: versions, category identity, versioned structure

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-20

Three tables and two trigger functions. See ADR-0089 for why identity and shape
are separate tables.

`category_structure.path` is derived. The application never writes it; the
trigger below builds it from the parent chain, and a second trigger cascades to
descendants when a node moves or is renamed. This is the same reasoning as
`updated_at`: a value the application maintains is wrong the moment anything
writes outside the ORM.

The i18n completeness rule is a trigger and not a CI gate.
`docs/15-repo-structure-standards.md` listed `taxonomy-i18n-complete` as a gate,
but a gate reads source and the rule is about rows. It is the same situation as
`basket_item_requires_verified_product`: a CHECK cannot reach another table, so
it is a trigger.

This revision imports `Ltree` from `core.models`, which the no-imports rule for
migrations does not cover. That rule is about vocabularies: an enum grows, and a
revision rendering its DDL from today's class would emit tomorrow's schema for
yesterday's history. A type spelling is fixed, and `LTREE` will read `LTREE` in
every future version of this file.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from bazaarwatch.core.models import Ltree

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UPDATED_AT_TABLES = ("taxonomy_versions", "categories", "category_structure")

# Launch locales, mirrored from bazaarwatch.core.locales.LAUNCH_LOCALES. Written
# out rather than imported: a revision that rendered its rule from today's
# constant would enforce tomorrow's locales on yesterday's history. Parity is
# asserted by test.
_LAUNCH_LOCALES = "ARRAY['tr', 'en', 'ru', 'de']"

# Labels are the slug with hyphens mapped to underscores, because ltree labels
# allow only [A-Za-z0-9_]. `slugify` collapses every non [a-z0-9] run to a
# single hyphen, so an underscore cannot occur in a slug and the mapping cannot
# map two distinct slugs onto one label.
SET_CATEGORY_PATH = """
CREATE OR REPLACE FUNCTION set_category_path() RETURNS TRIGGER AS $$
DECLARE
    v_label       TEXT;
    v_parent_path LTREE;
BEGIN
    SELECT replace(c.slug, '-', '_') INTO v_label
    FROM categories c WHERE c.id = NEW.category_id;

    IF v_label IS NULL THEN
        RAISE EXCEPTION 'category % has no identity row', NEW.category_id;
    END IF;

    IF NEW.parent_id IS NULL THEN
        NEW.path := v_label::LTREE;
        RETURN NEW;
    END IF;

    SELECT s.path INTO v_parent_path
    FROM category_structure s
    WHERE s.category_id = NEW.parent_id
      AND s.taxonomy_version = NEW.taxonomy_version;

    IF v_parent_path IS NULL THEN
        RAISE EXCEPTION 'parent % has no structure in taxonomy version %',
            NEW.parent_id, NEW.taxonomy_version;
    END IF;

    -- Slugs are globally unique, so a label already present in the ancestry
    -- means a cycle. Without this the descendant cascade never terminates.
    IF v_label = ANY (string_to_array(v_parent_path::TEXT, '.')) THEN
        RAISE EXCEPTION 'category % would be its own ancestor in taxonomy version %',
            NEW.category_id, NEW.taxonomy_version;
    END IF;

    NEW.path := v_parent_path || v_label::LTREE;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

# Moving a node moves everything under it. The cascade re-touches direct
# children only; each child's own BEFORE trigger recomputes its path from the
# already-updated parent and its AFTER trigger carries on down. Recursion depth
# is the depth of the subtree, and the cycle check above is what guarantees it
# terminates.
CASCADE_CATEGORY_PATH = """
CREATE OR REPLACE FUNCTION cascade_category_path() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.path IS DISTINCT FROM OLD.path THEN
        UPDATE category_structure
        SET parent_id = parent_id
        WHERE parent_id = NEW.category_id
          AND taxonomy_version = NEW.taxonomy_version;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
"""

# A slug is part of every descendant's path, in every version the node appears
# in, so renaming one node rewrites more than one tree.
CASCADE_CATEGORY_SLUG = """
CREATE OR REPLACE FUNCTION cascade_category_slug() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.slug IS DISTINCT FROM OLD.slug THEN
        UPDATE category_structure
        SET parent_id = parent_id
        WHERE category_id = NEW.id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
"""

# docs/11 section 5: `tr` is required at write, the remaining launch locales
# before a version is activated. The second half spans rows, so it cannot be a
# CHECK.
ASSERT_I18N_ON_ACTIVATION = f"""
CREATE OR REPLACE FUNCTION taxonomy_version_activation_is_complete() RETURNS TRIGGER AS $$
DECLARE
    v_nodes      INTEGER;
    v_incomplete INTEGER;
BEGIN
    IF NEW.status <> 'active' THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'UPDATE' AND OLD.status = 'active' THEN
        RETURN NEW;
    END IF;

    SELECT count(*) INTO v_nodes
    FROM category_structure s WHERE s.taxonomy_version = NEW.version;

    IF v_nodes = 0 THEN
        RAISE EXCEPTION 'taxonomy version % has no categories and cannot be activated',
            NEW.version;
    END IF;

    SELECT count(*) INTO v_incomplete
    FROM category_structure s
    JOIN categories c ON c.id = s.category_id
    WHERE s.taxonomy_version = NEW.version
      AND NOT (c.name_i18n ?& {_LAUNCH_LOCALES});

    IF v_incomplete > 0 THEN
        RAISE EXCEPTION
            'taxonomy version % cannot be activated: % categories have incomplete name_i18n',
            NEW.version, v_incomplete;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

_FUNCTIONS = (
    "set_category_path()",
    "cascade_category_path()",
    "cascade_category_slug()",
    "taxonomy_version_activation_is_complete()",
)


def upgrade() -> None:
    op.create_table(
        "taxonomy_versions",
        sa.Column("version", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column(
            "status", sa.String(length=16), server_default=sa.text("'draft'"), nullable=False
        ),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.CheckConstraint("status IN ('draft', 'active', 'superseded')", name="status_known"),
        sa.CheckConstraint("version > 0", name="version_is_positive"),
        sa.CheckConstraint(
            "(status = 'draft') = (activated_at IS NULL)", name="activated_iff_not_draft"
        ),
        sa.PrimaryKeyConstraint("version", name="pk_taxonomy_versions"),
    )
    # At most one active version. ADR-0079 rule 3 runs two series in parallel,
    # but the second is computed under a superseded or draft version, not a
    # second active one.
    op.create_index(
        "uq_taxonomy_versions_active",
        "taxonomy_versions",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name_i18n", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("superseded_by_id", sa.Uuid(), nullable=True),
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
        sa.CheckConstraint("name_i18n ? 'tr'", name="has_turkish_name"),
        sa.CheckConstraint(
            "superseded_by_id IS NULL OR superseded_by_id <> id", name="not_its_own_successor"
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_id"],
            ["categories.id"],
            name="fk_categories_superseded_by_id_categories",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_categories"),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
    )

    op.create_table(
        "category_structure",
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("taxonomy_version", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("path", Ltree(), nullable=False),
        sa.Column("sort_order", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
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
            "parent_id IS NULL OR parent_id <> category_id", name="not_its_own_parent"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_category_structure_category_id_categories",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["taxonomy_version"],
            ["taxonomy_versions.version"],
            name="fk_category_structure_taxonomy_version_taxonomy_versions",
            ondelete="RESTRICT",
        ),
        # Composite, so a parent is necessarily a node in the same version. A
        # plain reference to `categories` would let a path be built across two
        # trees with nothing to catch it.
        sa.ForeignKeyConstraint(
            ["parent_id", "taxonomy_version"],
            ["category_structure.category_id", "category_structure.taxonomy_version"],
            name="fk_category_structure_parent_category_structure",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("category_id", "taxonomy_version", name="pk_category_structure"),
    )
    op.create_index(
        "ix_category_structure_path",
        "category_structure",
        ["path"],
        postgresql_using="gist",
    )
    op.create_index(
        "ix_category_structure_parent",
        "category_structure",
        ["taxonomy_version", "parent_id"],
    )

    op.execute(SET_CATEGORY_PATH)
    op.execute(CASCADE_CATEGORY_PATH)
    op.execute(CASCADE_CATEGORY_SLUG)
    op.execute(ASSERT_I18N_ON_ACTIVATION)

    op.execute(
        "CREATE TRIGGER trg_category_structure_path "
        "BEFORE INSERT OR UPDATE ON category_structure "
        "FOR EACH ROW EXECUTE FUNCTION set_category_path()"
    )
    op.execute(
        "CREATE TRIGGER trg_category_structure_cascade "
        "AFTER UPDATE ON category_structure "
        "FOR EACH ROW EXECUTE FUNCTION cascade_category_path()"
    )
    op.execute(
        "CREATE TRIGGER trg_categories_slug_cascade "
        "AFTER UPDATE ON categories "
        "FOR EACH ROW EXECUTE FUNCTION cascade_category_slug()"
    )
    op.execute(
        "CREATE TRIGGER trg_taxonomy_versions_activation "
        "BEFORE INSERT OR UPDATE ON taxonomy_versions "
        "FOR EACH ROW EXECUTE FUNCTION taxonomy_version_activation_is_complete()"
    )

    for table in _UPDATED_AT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def downgrade() -> None:
    for table in reversed(_UPDATED_AT_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")

    op.execute("DROP TRIGGER IF EXISTS trg_taxonomy_versions_activation ON taxonomy_versions")
    op.execute("DROP TRIGGER IF EXISTS trg_categories_slug_cascade ON categories")
    op.execute("DROP TRIGGER IF EXISTS trg_category_structure_cascade ON category_structure")
    op.execute("DROP TRIGGER IF EXISTS trg_category_structure_path ON category_structure")

    for function in _FUNCTIONS:
        op.execute(f"DROP FUNCTION IF EXISTS {function}")

    op.drop_table("category_structure")
    op.drop_table("categories")
    op.drop_table("taxonomy_versions")
