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
from decimal import Decimal
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from bazaarwatch.core.enums import SqlStrEnum
from bazaarwatch.core.locales import REQUIRED_AT_WRITE, Locale
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


class UnitBasis(SqlStrEnum):
    """What a unit price is per. Comparison is per unit, never per pack."""

    PER_L = "per_l"
    PER_KG = "per_kg"
    PER_PIECE = "per_piece"


class UnitOfMeasure(SqlStrEnum):
    GRAM = "g"
    KILOGRAM = "kg"
    MILLILITRE = "ml"
    LITRE = "l"
    PIECE = "piece"


class ProductSource(SqlStrEnum):
    OPERATOR = "operator"
    SCRAPE = "scrape"
    CONTRIBUTOR = "contributor"


class VerificationState(SqlStrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"


class ProductStatus(SqlStrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    MERGED = "merged"
    RETIRED = "retired"


class GtinKind(SqlStrEnum):
    EAN13 = "ean13"
    EAN8 = "ean8"
    UPC = "upc"
    PLU = "plu"
    # Collides across chains by design, which is why it is namespaced.
    CHAIN_INTERNAL = "chain_internal"


class AliasSource(SqlStrEnum):
    OPERATOR = "operator"
    CONTRIBUTOR = "contributor"
    MINED = "mined"
    LEXICON = "lexicon"


class AliasStatus(SqlStrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"


class Brand(Base):
    """Private label ownership lives here and nowhere else.

    `products` carried an `owner_chain_id` too, which was a second place to
    record one fact. Private label is a property of the brand, and a
    private-label product always has one.
    """

    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(SLUG_MAX_LENGTH), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_private_label: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    owner_chain_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("chains.id", ondelete="RESTRICT")
    )
    created_at: Mapped[dt.datetime] = created_at_column()

    __table_args__ = (
        CheckConstraint(
            "NOT is_private_label OR owner_chain_id IS NOT NULL",
            name="private_label_has_owner",
        ),
        # The other direction. An owner on a brand that is not private label is
        # a claim about a chain that the private-label rules will not apply.
        CheckConstraint(
            "is_private_label OR owner_chain_id IS NULL",
            name="owner_implies_private_label",
        ),
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(SLUG_MAX_LENGTH), nullable=False, unique=True)
    # Turkish, as it appears locally.
    canonical_name: Mapped[str] = mapped_column(String(300), nullable=False)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("brands.id", ondelete="RESTRICT")
    )
    # Points at identity, not at a node in one taxonomy version, so a
    # restructure does not move every product. See ADR-0089.
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    net_content_value: Mapped[Decimal | None] = mapped_column(Numeric(precision=12, scale=4))
    net_content_uom: Mapped[str | None] = mapped_column(String(8))
    unit_basis: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=UnitBasis.PER_PIECE.value
    )
    source: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=ProductSource.OPERATOR.value
    )
    verification_state: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=VerificationState.UNVERIFIED.value
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=ProductStatus.ACTIVE.value
    )
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT")
    )
    created_at: Mapped[dt.datetime] = created_at_column()
    updated_at: Mapped[dt.datetime] = updated_at_column()

    __table_args__ = (
        CheckConstraint(UnitBasis.sql_check("unit_basis"), name="unit_basis_known"),
        CheckConstraint(
            f"net_content_uom IS NULL OR {UnitOfMeasure.sql_check('net_content_uom')}",
            name="uom_known_if_present",
        ),
        CheckConstraint(ProductSource.sql_check("source"), name="source_known"),
        CheckConstraint(
            VerificationState.sql_check("verification_state"), name="verification_state_known"
        ),
        CheckConstraint(ProductStatus.sql_check("status"), name="status_known"),
        # A per-kilogram or per-litre basis with no net content is a unit price
        # that cannot be computed, and unit price is what comparison ranks on.
        CheckConstraint(
            "unit_basis = 'per_piece' "
            "OR (net_content_value IS NOT NULL AND net_content_uom IS NOT NULL)",
            name="unit_basis_needs_net_content",
        ),
        CheckConstraint(
            "net_content_value IS NULL OR net_content_value > 0",
            name="net_content_is_positive",
        ),
        # Both directions, so a live product cannot carry a merge target.
        CheckConstraint(
            "(status = 'merged') = (merged_into_id IS NOT NULL)",
            name="merged_iff_target",
        ),
        CheckConstraint(
            "merged_into_id IS NULL OR merged_into_id <> id", name="not_merged_into_itself"
        ),
        Index("ix_products_category_id", "category_id"),
        Index("ix_products_brand_id", "brand_id"),
    )


class ProductGtin(Base):
    __tablename__ = "product_gtins"

    id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    gtin: Mapped[str] = mapped_column(String(64), nullable=False)
    gtin_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    chain_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("chains.id", ondelete="RESTRICT")
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[dt.datetime] = created_at_column()

    __table_args__ = (
        CheckConstraint(GtinKind.sql_check("gtin_kind"), name="gtin_kind_known"),
        CheckConstraint(
            "gtin_kind <> 'chain_internal' OR chain_id IS NOT NULL",
            name="internal_gtin_is_chain_scoped",
        ),
        # Global namespace: one product per code.
        Index(
            "uq_product_gtins_global",
            "gtin",
            "gtin_kind",
            unique=True,
            postgresql_where=text("gtin_kind <> 'chain_internal'"),
        ),
        # Chain-internal namespace: codes legitimately collide across chains.
        Index(
            "uq_product_gtins_chain",
            "chain_id",
            "gtin",
            unique=True,
            postgresql_where=text("gtin_kind = 'chain_internal'"),
        ),
        # One primary code per product. Without this, "the barcode to print" is
        # a question with several answers and no way to choose.
        Index(
            "uq_product_gtins_primary",
            "product_id",
            unique=True,
            postgresql_where=text("is_primary"),
        ),
    )


class ProductAlias(Base):
    __tablename__ = "product_aliases"

    id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    locale: Mapped[str] = mapped_column(String(8), nullable=False)
    # Bounded, because it sits inside a unique index. A btree entry caps at
    # roughly 2704 bytes, so unbounded text fails at insert with an index size
    # error rather than a validation message.
    alias_text: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=AliasStatus.ACTIVE.value
    )
    created_at: Mapped[dt.datetime] = created_at_column()

    __table_args__ = (
        CheckConstraint(Locale.sql_check("locale"), name="locale_known"),
        CheckConstraint(AliasSource.sql_check("source"), name="source_known"),
        CheckConstraint(AliasStatus.sql_check("status"), name="status_known"),
        UniqueConstraint("product_id", "locale", "alias_text", name="uq_product_aliases_text"),
        Index("ix_product_aliases_product_id", "product_id"),
    )


class ProductFacet(Base):
    """Open set: halal, organic, imported, refrigerated, private_label.

    No CHECK, deliberately. `docs/06-catalog-lexicon.md` section 2 calls facets
    an open set that costs nothing and carries no structural weight, and a
    constraint would make adding one a migration.
    """

    __tablename__ = "product_facets"

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT"), primary_key=True
    )
    facet: Mapped[str] = mapped_column(String(32), primary_key=True)
    created_at: Mapped[dt.datetime] = created_at_column()

    __table_args__ = (Index("ix_product_facets_facet", "facet"),)


class ProductGroup(Base):
    """Substitution grouping. 1L and 1.5L Coke are separate products, one group.

    Also the mechanism by which a shopper comparison can include private label
    from several chains while a fixed-identity basket item cannot.
    """

    __tablename__ = "product_groups"

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(SLUG_MAX_LENGTH), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[dt.datetime] = created_at_column()


class ProductGroupMember(Base):
    __tablename__ = "product_group_members"

    group_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("product_groups.id", ondelete="RESTRICT"), primary_key=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT"), primary_key=True
    )
    created_at: Mapped[dt.datetime] = created_at_column()


class Collection(Base):
    """Dietary and national sets. Schema only until query logs justify curation."""

    __tablename__ = "collections"

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(SLUG_MAX_LENGTH), nullable=False, unique=True)
    name_i18n: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[dt.datetime] = created_at_column()

    __table_args__ = (
        CheckConstraint(f"name_i18n ? '{REQUIRED_AT_WRITE.value}'", name="has_turkish_name"),
    )


class CollectionMember(Base):
    __tablename__ = "collection_members"

    collection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("collections.id", ondelete="RESTRICT"), primary_key=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT"), primary_key=True
    )
    created_at: Mapped[dt.datetime] = created_at_column()


class ProductSearchDoc(Base):
    """Materialised retrieval document. Rebuilt on product or alias change.

    `lexical_text` and `semantic_text` are deliberately different. The fold is
    lossy and correct for trigram; it degrades a model trained on natural
    diacritics (ADR-0025).

    The embedding column is unpinned because the model is not chosen (ADR-0024),
    and an unpinned `vector` accepts a 768-dimension row beside a 1024-dimension
    one with no error. `embedding_is_unset` is what stops that: it holds the
    column empty until the migration that pins the dimension drops it and
    creates the HNSW index in the same change.
    """

    __tablename__ = "product_search_docs"

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT"), primary_key=True
    )
    # Turkish-folded: canonical name, brand and aliases.
    lexical_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Unfolded natural language, the embedding input.
    semantic_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Any | None] = mapped_column(Vector)
    # Nullable, unlike the data model's original NOT NULL. Every row written
    # before a model is chosen would need a placeholder, and a placeholder in a
    # NOT NULL column is a lie the schema tells.
    model_version: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[dt.datetime] = updated_at_column()

    __table_args__ = (
        CheckConstraint("embedding IS NULL", name="embedding_is_unset"),
        CheckConstraint(
            "(embedding IS NULL) = (model_version IS NULL)", name="model_version_iff_embedding"
        ),
    )


__all__ = [
    "AliasSource",
    "AliasStatus",
    "Brand",
    "Category",
    "CategoryStructure",
    "Collection",
    "CollectionMember",
    "GtinKind",
    "Product",
    "ProductAlias",
    "ProductFacet",
    "ProductGroup",
    "ProductGroupMember",
    "ProductGtin",
    "ProductSearchDoc",
    "ProductSource",
    "ProductStatus",
    "TaxonomyStatus",
    "TaxonomyVersion",
    "UnitBasis",
    "UnitOfMeasure",
    "VerificationState",
]
