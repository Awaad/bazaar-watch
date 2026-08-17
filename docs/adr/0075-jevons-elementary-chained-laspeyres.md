# ADR-0075: Two-level index: Jevons elementary, chained Laspeyres above

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

A price index computed by an unstated ad hoc method is indefensible the moment it is
challenged, and it will be challenged.

Expenditure weights only exist above a certain level of aggregation. Below that level, at a single
product in a single branch, there is nothing to weight by.

At the elementary level the choice of averaging formula matters more than it appears. Carli, the
arithmetic mean of price relatives, carries a well documented upward bias.

Baskets must be refreshable without breaking the continuity of the series.

## Decision

Two levels, following standard statistical practice.

**Elementary aggregates** use the **Jevons index**, the geometric mean of price relatives. Chosen
because it is transitive and is the international standard at this level. Carli is not used.

**Higher-level aggregation** combines elementary indices with expenditure weights in a
Laspeyres-type structure, **chained** so that a basket refresh does not create a discontinuity.

The taxonomy maps to COICOP division 01, which is most of what makes the figures comparable to
official statistics (ADR-0009).

## Consequences

The method is standard, citable and defensible against a competent critic.

COICOP mapping constrains the taxonomy design slightly and pays for itself in comparability.

Chaining means the basket can evolve with the market, which matters under high inflation and rapid
product churn.

Implementation is more involved than a simple average, and the two levels must be kept distinct in
code or the weighting is applied at the wrong level.

## Alternatives considered

**Simple arithmetic mean of prices.** Rejected. Not an index, and it is dominated by
expensive items.

**Carli at the elementary level.** Rejected. Documented upward bias, which in a high-inflation
setting would compound into a visibly wrong number.

**Fixed-base Laspeyres without chaining.** Rejected. The basket cannot be refreshed without breaking
the series, and product churn here is rapid.

**Fisher or Törnqvist.** Not rejected on merit; both require current-period weights at every level,
which the corpus can eventually support. Deferred as a refinement.

## Revisit trigger

Corpus expenditure data becomes rich enough to support a superlative index formula
throughout.
