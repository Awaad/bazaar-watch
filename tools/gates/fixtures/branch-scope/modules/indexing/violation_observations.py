"""Fixture: an index aggregate over price_observations, without the predicate.

The worst version of this defect, because the table keeps superseded rows by
design. The figure is not wrong by a rounding error; it is inflated by however
much reprocessing has happened since the corpus was first extracted.
"""

from sqlalchemy import func, select

from bazaarwatch.modules.observations.models import PriceObservation


def mean_price():
    return select(func.avg(PriceObservation.price_minor))
