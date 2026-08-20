"""Fixture: correct. Asks for a scope by name and never says branches."""

from sqlalchemy import select

from bazaarwatch.modules.geo import service


def basket_cost():
    eligible = service.index_eligible_branches()
    return select(eligible.c.id, eligible.c.chain_id)
