"""Fixture: correct. Asks for a scope by name and never names the table."""

from sqlalchemy import func, select

from bazaarwatch.modules.observations import service


def mean_price():
    countable = service.countable_observations()
    return select(func.avg(countable.c.price_minor))
