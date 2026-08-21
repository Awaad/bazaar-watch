"""Public surface of the lexicon module.

Every cross-module call enters here. If this module ever has no service
surface, it should not be a module.

Resolution is a query builder rather than a function that runs one. Nothing in
this repository has an async session yet, and a synchronous version would be
rewritten the moment one arrives. A `Select` is neutral: the caller executes it
on whatever connection it has, and it is testable today. Same shape as the geo
selectables in ADR-0088.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Select, case, literal, select

from bazaarwatch.core.text import turkish_fold
from bazaarwatch.modules.lexicon.models import ChainLexiconEntry, KeyKind, LexiconStatus


def resolution_query(
    chain_id: uuid.UUID, *, sku: str | None = None, raw_text: str | None = None
) -> Select[tuple[uuid.UUID]]:
    """The product a receipt line maps to, for one chain.

    Exact match, never fuzzy. A fuzzy match that is wrong attaches a price to
    the wrong product and nothing raises (ADR-0008).

    Tries the SKU first and falls back to the folded description, in one
    statement rather than two round trips. The ordering is what makes it a
    fallback rather than a race: where a line carries both a code and a
    description and both are mapped, the code wins.

    `raw_text` is folded here rather than by the caller. A caller who forgets
    passes an unfolded string that matches nothing, and sees an unresolved line
    rather than an error.

    Returns a statement selecting zero or one `product_id`. Zero is the normal
    unresolved case and is what creates a review task, not an exception.
    """
    if sku is None and raw_text is None:
        raise ValueError("resolution needs a sku, a raw description, or both")

    keys = []
    if sku is not None:
        keys.append(
            (ChainLexiconEntry.key_kind == KeyKind.SKU.value) & (ChainLexiconEntry.key_value == sku)
        )
    if raw_text is not None:
        keys.append(
            (ChainLexiconEntry.key_kind == KeyKind.RAW_TEXT.value)
            & (ChainLexiconEntry.key_value == turkish_fold(raw_text))
        )

    match = keys[0]
    for key in keys[1:]:
        match = match | key

    return (
        select(ChainLexiconEntry.product_id)
        .where(
            ChainLexiconEntry.chain_id == chain_id,
            ChainLexiconEntry.status == LexiconStatus.ACTIVE.value,
            match,
        )
        .order_by(
            case((ChainLexiconEntry.key_kind == KeyKind.SKU.value, literal(0)), else_=literal(1))
        )
        .limit(1)
    )


__all__ = ["resolution_query"]
