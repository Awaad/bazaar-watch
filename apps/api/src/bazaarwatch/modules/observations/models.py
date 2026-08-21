"""Price observations.

A nullable `product_id` is deliberate. An unresolved observation is a real fact
already collected; it simply cannot enter an index yet, and discarding it would
throw away the evidence that creates the review task.

`unit_price_minor` is derived, never submitted. It is what makes a 500 g pack
comparable to a 750 g one, and comparison is the product.

Every read path filters on status, and a missing filter produces double counting
rather than an error. That is why aggregates do not query this table directly.
See ADR-0090 and `service.py`.
"""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from bazaarwatch.core.enums import SqlStrEnum
from bazaarwatch.core.models import Base, created_at_column, uuid_pk


class SourceKind(SqlStrEnum):
    RECEIPT_LINE = "receipt_line"
    SHELF_MANUAL = "shelf_manual"
    SHELF_BARCODE = "shelf_barcode"
    SCRAPE = "scrape"


class PriceKind(SqlStrEnum):
    REGULAR = "regular"
    PROMOTIONAL = "promotional"
    MEMBER = "member"
    CLEARANCE = "clearance"


class ObservationStatus(SqlStrEnum):
    PENDING = "pending"
    PROVISIONAL = "provisional"
    ACCEPTED = "accepted"
    FLAGGED = "flagged"
    # Set when the extraction run that produced it is superseded, in the same
    # transaction as the replacement is written. Never deleted (ADR-0082).
    SUPERSEDED = "superseded"


class UnitBasis(SqlStrEnum):
    PER_L = "per_l"
    PER_KG = "per_kg"
    PER_PIECE = "per_piece"


class PriceObservation(Base):
    __tablename__ = "price_observations"

    id: Mapped[uuid.UUID] = uuid_pk()
    source_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    # Polymorphic on purpose: a receipt line, a shelf capture or a scrape row.
    # No foreign key, because the target table varies. The unique pair below is
    # what stops one source producing two observations.
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    branch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT")
    )
    observed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="TRY")
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=4), nullable=False, server_default=text("1")
    )
    uom: Mapped[str] = mapped_column(String(16), nullable=False, server_default="piece")
    unit_price_minor: Mapped[int | None] = mapped_column(BigInteger)
    unit_basis: Mapped[str | None] = mapped_column(String(16))
    price_kind: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=PriceKind.REGULAR.value
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=ObservationStatus.PENDING.value
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(precision=4, scale=3))
    extraction_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("extraction_runs.id", ondelete="RESTRICT")
    )
    created_at: Mapped[dt.datetime] = created_at_column()

    __table_args__ = (
        CheckConstraint(SourceKind.sql_check("source_kind"), name="source_kind_known"),
        CheckConstraint(PriceKind.sql_check("price_kind"), name="price_kind_known"),
        CheckConstraint(ObservationStatus.sql_check("status"), name="status_known"),
        CheckConstraint(
            f"unit_basis IS NULL OR {UnitBasis.sql_check('unit_basis')}",
            name="unit_basis_known_if_present",
        ),
        CheckConstraint("price_minor >= 0", name="price_is_not_negative"),
        CheckConstraint("quantity > 0", name="quantity_is_positive"),
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1", name="confidence_in_range"
        ),
        # A unit price without a basis is a number with no meaning, and a basis
        # without a price is half a derivation.
        CheckConstraint(
            "(unit_price_minor IS NULL) = (unit_basis IS NULL)", name="unit_price_has_a_basis"
        ),
        # A receipt-sourced observation names the run that produced it, and only
        # a receipt-sourced one has a run to name. This is what lets superseding
        # a run find its observations.
        CheckConstraint(
            "(source_kind = 'receipt_line') = (extraction_run_id IS NOT NULL)",
            name="run_iff_receipt_sourced",
        ),
        UniqueConstraint("source_kind", "source_id", name="uq_price_observations_source"),
        Index(
            "ix_price_observations_run",
            "extraction_run_id",
            postgresql_where=text("extraction_run_id IS NOT NULL"),
        ),
        Index(
            "ix_price_observations_branch_product_time",
            "branch_id",
            "product_id",
            text("observed_at DESC"),
        ),
        # Unresolved rows, ordered for the review queue.
        Index(
            "ix_price_observations_unresolved",
            "branch_id",
            text("observed_at DESC"),
            postgresql_where=text("product_id IS NULL"),
        ),
    )


__all__ = ["ObservationStatus", "PriceKind", "PriceObservation", "SourceKind", "UnitBasis"]
