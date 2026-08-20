"""Fixture: a local variable named `branches` holding a scope.

Correct, and the first version of this gate rejected it. Naming the thing you
got back from the service `branches` carries no access to the table; the point
is where it came from.
"""

from sqlalchemy import select

from bazaarwatch.modules.geo import service


def basket_cost():
    branches = service.index_eligible_branches()
    return select(branches.c.id, branches.c.chain_id)
