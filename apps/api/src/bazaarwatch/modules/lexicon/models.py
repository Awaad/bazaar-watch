"""Chain-scoped lexicon.

One table. A mapping from what a chain's receipt prints to a product, scoped to
that chain because the same string means different things in different shops.

Resolution is exact match, never fuzzy. A fuzzy match that is wrong attaches a
price to the wrong product and nothing raises. See ADR-0008.

`decided_by` is NOT NULL and no automated process writes here. That is ADR-0011
made structural: a column that cannot be null cannot be filled by a suggestion.
"""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from bazaarwatch.core.enums import SqlStrEnum
from bazaarwatch.core.models import Base, created_at_column, uuid_pk


class KeyKind(SqlStrEnum):
    # The code the receipt printed, verbatim.
    SKU = "sku"
    # The printed description, Turkish-folded.
    RAW_TEXT = "raw_text"


class DecidedVia(SqlStrEnum):
    OPERATOR = "operator"
    # Community review, subject to quorum and independence. Still a human
    # decision, which is the only kind this table accepts (ADR-0047).
    REVIEW_T1 = "review_t1"


class LexiconStatus(SqlStrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"


class ChainLexiconEntry(Base):
    __tablename__ = "chain_lexicon"

    id: Mapped[uuid.UUID] = uuid_pk()
    chain_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("chains.id", ondelete="RESTRICT"), nullable=False
    )
    key_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    # Bounded because it sits inside a unique index: a btree entry caps at
    # roughly 2704 bytes, so unbounded text fails at insert with an index size
    # error rather than a validation message.
    key_value: Mapped[str] = mapped_column(String(200), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(precision=4, scale=3), nullable=False, server_default=text("1.000")
    )
    # Never null, deliberately. See the module docstring.
    decided_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    decided_via: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=LexiconStatus.ACTIVE.value
    )
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("chain_lexicon.id", ondelete="RESTRICT")
    )
    created_at: Mapped[dt.datetime] = created_at_column()

    __table_args__ = (
        CheckConstraint(KeyKind.sql_check("key_kind"), name="key_kind_known"),
        CheckConstraint(DecidedVia.sql_check("decided_via"), name="decided_via_known"),
        CheckConstraint(LexiconStatus.sql_check("status"), name="status_known"),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="confidence_in_range"),
        # An empty key would match every line that printed nothing, which is
        # the failure mode a lexicon is supposed to prevent.
        CheckConstraint("length(key_value) > 0", name="key_value_is_not_empty"),
        # The data model says raw_text holds folded text. Nothing enforced it,
        # and an unfolded entry is not wrong in any visible way: it simply never
        # matches, and the operator who wrote it sees their mapping ignored
        # forever. `turkish_fold` is IMMUTABLE, so a CHECK can say it.
        CheckConstraint(
            "key_kind <> 'raw_text' OR key_value = turkish_fold(key_value)",
            name="raw_text_key_is_folded",
        ),
        # One direction only. An active entry must not name a successor. The
        # converse is deliberately allowed: an operator withdrawing a wrong
        # mapping with nothing to put in its place leaves a superseded row with
        # no successor, and that is a real thing to want.
        CheckConstraint(
            "superseded_by IS NULL OR status = 'superseded'",
            name="successor_implies_superseded",
        ),
        CheckConstraint(
            "superseded_by IS NULL OR superseded_by <> id", name="not_its_own_successor"
        ),
        # Exactly one active entry per key. Superseded history accumulates
        # without limit, which is the point: a mapping decision is evidence.
        Index(
            "uq_chain_lexicon_active",
            "chain_id",
            "key_kind",
            "key_value",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index("ix_chain_lexicon_product_id", "product_id"),
    )


__all__ = ["ChainLexiconEntry", "DecidedVia", "KeyKind", "LexiconStatus"]
