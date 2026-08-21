"""Public surface of the observations module.

Every cross-module call enters here. If this module ever has no service
surface, it should not be a module.

The selectables below are ADR-0090, which is ADR-0088 applied to a second
table. `price_observations` accumulates superseded rows by design, so an
aggregate that forgets a status predicate double counts every reprocessed
receipt. Aggregates ask for a scope by name instead.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.sql import Subquery

from bazaarwatch.modules.observations.models import ObservationStatus, PriceObservation


def countable_observations() -> Subquery:
    """Observations that may enter a published figure.

    Accepted, and resolved to a product. An unresolved observation is a real
    fact and belongs in the review queue, not in an index: it has no product to
    aggregate under.

    Superseded rows are the reason this exists. Reprocessing a corpus writes new
    observations and moves the old ones aside in the same transaction, so a
    query without the status predicate counts both and the figure is wrong by
    however much the model improved (ADR-0082).
    """
    return (
        select(PriceObservation)
        .where(
            PriceObservation.status == ObservationStatus.ACCEPTED.value,
            PriceObservation.product_id.is_not(None),
        )
        .subquery("countable_observations")
    )


def unresolved_observations() -> Subquery:
    """Collected, not yet mapped to a product.

    What creates review tasks. Deliberately not filtered on status: a pending
    unresolved row is exactly the thing a T1 task is for, and waiting for it to
    be accepted first would deadlock the queue that does the accepting.
    """
    return (
        select(PriceObservation)
        .where(PriceObservation.product_id.is_(None))
        .subquery("unresolved_observations")
    )


__all__ = ["countable_observations", "unresolved_observations"]
