"""Catalog tables. Taxonomy half.

Owned by this module. Cross-module access goes through `service.py`.

The split between `categories` and `category_structure` is ADR-0089 and is not
cosmetic. ADR-0079 rule 3 requires a taxonomy restructure to run both series in
parallel for three cycles, which means computing new index values under the old
tree while the new tree is live. One mutable tree cannot do that. Identity is
stable and carries the slug; shape is per version.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from bazaarwatch.core.enums import SqlStrEnum
from bazaarwatch.core.locales import REQUIRED_AT_WRITE
from bazaarwatch.core.models import (
    Base,
    Ltree,
    created_at_column,
    updated_at_column,
    uuid_pk,
)
from bazaarwatch.core.text import SLUG_MAX_LENGTH


class TaxonomyStatus(SqlStrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    # Kept, never deleted. ADR-0079 rule 5: the old series stays available
    # permanently, and a superseded version is what makes it readable.
    SUPERSEDED = "superseded"


class TaxonomyVersion(Base):
    """A shape of the category tree, named by every figure computed under it.

    `index_runs` and `index_values` both carry `taxonomy_version`. Before this
    table existed they named an integer no row defined, so a published figure
    referenced a version that could not be looked up.
    """

    __tablename__ = "taxonomy_versions"

    # The natural key. Deliberately not a surrogate UUID: this integer is what
    # index runs already record and what a published figure already names, and
    # a surrogate would put a second identifier on the same fact.
    version: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=TaxonomyStatus.DRAFT.value
    )
    activated_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = created_at_column()
    updated_at: Mapped[dt.datetime] = updated_at_column()

    __table_args__ = (
        CheckConstraint(TaxonomyStatus.sql_check("status"), name="status_known"),
        CheckConstraint("version > 0", name="version_is_positive"),
        # Draft has not been activated; the other two have. Without this an
        # active version can carry no activation time, and the announcement
        # date ADR-0079 rule 2 requires has nowhere to come from.
        CheckConstraint(
            "(status = 'draft') = (activated_at IS NULL)",
            name="activated_iff_not_draft",
        ),
        Index(
            "uq_taxonomy_versions_active",
            "status",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )


class Category(Base):
    """Identity. Stable across restructures, and what a product points at.

    No `status` column. Membership in a taxonomy version's structure is what
    makes a node live, and a status alongside that is a second way to say the
    same thing that can disagree with the first.
    """

    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = uuid_pk()
    # Globally unique and stable, because it is a URL. Restructuring the tree
    # must not change where a category lives on the web.
    slug: Mapped[str] = mapped_column(String(SLUG_MAX_LENGTH), nullable=False, unique=True)
    name_i18n: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # A restructure that merges two nodes genuinely changes identity. The
    # survivor is recorded so the retired node's history has somewhere to go.
    # Same shape as branch_candidates.duplicate_of_id.
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="RESTRICT")
    )
    created_at: Mapped[dt.datetime] = created_at_column()
    updated_at: Mapped[dt.datetime] = updated_at_column()

    __table_args__ = (
        # Turkish is required at write. The remaining launch locales are
        # required before a version can be activated, which a CHECK cannot
        # express because it spans rows; see the trigger in migration 0004.
        CheckConstraint(f"name_i18n ? '{REQUIRED_AT_WRITE.value}'", name="has_turkish_name"),
        CheckConstraint(
            "superseded_by_id IS NULL OR superseded_by_id <> id",
            name="not_its_own_successor",
        ),
    )


class CategoryStructure(Base):
    """Shape, per taxonomy version.

    `path` is derived and maintained by a trigger, never written by the
    application. `parent_id` is the source of truth and carries the foreign key,
    so a malformed hierarchy is a constraint violation rather than an orphan
    nobody notices.
    """

    __tablename__ = "category_structure"

    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="RESTRICT"), primary_key=True
    )
    taxonomy_version: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("taxonomy_versions.version", ondelete="RESTRICT"),
        primary_key=True,
    )
    # No plain foreign key to `categories`: the parent must be a node in the
    # same taxonomy version, which only a composite key to this table can say.
    # A parent borrowed from another version would build a path across two
    # trees and nothing would catch it.
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    # Materialised ancestry, labels built from the slug with hyphens mapped to
    # underscores. `slugify` collapses every non `[a-z0-9]` run to a hyphen, so
    # an underscore can never occur in a slug and the mapping cannot collide.
    # NOT NULL, and never written by the application. The BEFORE trigger fills
    # it, so a null here means the trigger was bypassed rather than that the
    # node is rootless.
    path: Mapped[str] = mapped_column(Ltree, nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    created_at: Mapped[dt.datetime] = created_at_column()
    updated_at: Mapped[dt.datetime] = updated_at_column()

    __table_args__ = (
        ForeignKeyConstraint(
            ["parent_id", "taxonomy_version"],
            ["category_structure.category_id", "category_structure.taxonomy_version"],
            name="fk_category_structure_parent_category_structure",
            ondelete="RESTRICT",
        ),
        CheckConstraint("parent_id IS NULL OR parent_id <> category_id", name="not_its_own_parent"),
        Index("ix_category_structure_parent", "taxonomy_version", "parent_id"),
        # Subtree queries are the point of ltree, and they are index scans
        # only with this.
        Index("ix_category_structure_path", "path", postgresql_using="gist"),
    )


__all__ = [
    "Category",
    "CategoryStructure",
    "TaxonomyStatus",
    "TaxonomyVersion",
]
