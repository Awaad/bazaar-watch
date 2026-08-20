"""Public surface of the geo module.

Every cross-module call enters here. If this module ever has no service
surface, it should not be a module.

The two selectables below are the whole point of ADR-0088. Index and comparison
code does not query `branches` and does not carry the ADR-0045 and ADR-0023
predicates itself; it asks for a scope by name and the exclusions come with it.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.sql import Subquery

from bazaarwatch.modules.geo.models import Branch, BranchKind


def index_eligible_branches() -> Subquery:
    """Branches whose prices may enter a published figure.

    Physical, because an online seller's pricing is not evidence about the
    physical market (ADR-0045). Human-verified, because open map data has
    closed stores and wrong pins and a mis-pinned branch corrupts access-scoped
    comparison rather than merely showing a wrong dot (ADR-0023).

    Use this for per-category chain indices (ADR-0034), basket index
    computation, and access-scoped comparison (ADR-0035).

    `operating_status` is deliberately not filtered. A permanently closed
    branch has real history, and an index recomputed over a past period must
    still see the prices observed then. Filtering current state is a
    presentation concern and belongs at the call site that wants it.
    """
    return (
        select(Branch)
        .where(
            Branch.branch_kind == BranchKind.PHYSICAL.value,
            Branch.verified_by_human.is_(True),
        )
        .subquery("index_eligible_branches")
    )


def public_branches() -> Subquery:
    """Branches a price may be shown against.

    Human-verified, any kind. Online sellers are real price sources and belong
    in item lookup and price history; they are excluded from indices and
    comparison, which is what the narrower scope above is for (ADR-0045).
    """
    return select(Branch).where(Branch.verified_by_human.is_(True)).subquery("public_branches")


__all__ = ["index_eligible_branches", "public_branches"]
