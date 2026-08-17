# ADR-0045: Branches may be locationless

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Online sellers publish prices and have no geometry. Several exist locally, including
ventures that have since failed but whose catalogs remain useful.

They are real price sources and belong in item lookup and price history.

They are not evidence about the physical market. Their pricing reflects a different cost structure
and a different competitive position, and including them in a chain or category index would
contaminate a measurement of shop prices with something else.

Access-scoped comparison presumes reachability, which is meaningless without geometry.

## Decision

`branch_kind` is `physical` or `online`. Geometry is nullable, enforced in both
directions by check constraints: a physical branch must have geometry, an online branch must not.

Online branches appear in item lookup and price history.

They are excluded from access-scoped basket comparison (ADR-0035) and from per-category chain
indices (ADR-0034).

They still require a chain row, which for a single online seller is a chain of one (ADR-0087).

## Consequences

Scraped price data is usable without polluting the index.

Every index and comparison query carries a `branch_kind` predicate, and forgetting it is a silent
correctness bug rather than an error.

The user-facing distinction needs explaining, since an online price appearing in history but not in
a basket comparison is otherwise confusing.

Online sellers' catalogs also seed canonical products, which is a separate use (ADR-0046).

## Alternatives considered

**Exclude online sellers entirely.** Rejected. Discards real price data and a
valuable catalog seed.

**Include them in indices.** Rejected. Contaminates a measurement of physical shop prices.

**Give them a nominal location.** Rejected. A fabricated coordinate would silently enter reachability
calculations.

## Revisit trigger

Online grocery becomes a large enough share of local spending that excluding it makes the
index unrepresentative.
