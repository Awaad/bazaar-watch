"""Fixture: the mistake ADR-0088 exists to prevent.

An index query joining observations to branches with neither the ADR-0045
branch_kind predicate nor the ADR-0023 verification predicate. It runs, it
returns rows, and the figure it produces is wrong by however much online and
unverified pricing differs from the physical verified market.
"""

from sqlalchemy import select

from bazaarwatch.modules.geo.models import Branch


def basket_cost():
    return select(Branch.id, Branch.chain_id)
