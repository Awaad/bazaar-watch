# ADR-0035: Comparison is access-scoped; geography is load-bearing

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

A cheap shop the user cannot reach is worth nothing. A chain being cheapest overall is
irrelevant from a town forty minutes away.

Ranking globally and then filtering produces a recommendation the user cannot act on and then hides
it, which is worse than not producing it.

This makes geography a filter on every basket read path rather than a map feature.

## Decision

Comparison is filtered to a reachable set **before** ranking, never ranked globally and
filtered afterwards.

Reachability is initially a radius via PostGIS `ST_DWithin` on the geography column with a GIST
index.

PostGIS is therefore core infrastructure rather than decorative, which raises the importance of
branch verification (ADR-0023): a mis-pinned branch places itself inside or outside a reachable set
incorrectly and corrupts the comparison.

Online branches have no geometry and are excluded from access-scoped comparison entirely
(ADR-0045).

## Consequences

Recommendations are actionable by construction.

Branch verification moves onto the critical path earlier than a map feature would require.

Radius is a crude proxy for travel time. It is correct enough at city scale and requires no routing
dependency, which is the trade.

Every basket query carries a geographic predicate, so index design on `branches.geom` matters.

## Alternatives considered

**Global ranking with a distance column.** Rejected. Surfaces unreachable options and
makes the user filter mentally.

**Isochrone from a routing service.** Deferred. More accurate, adds an external dependency and a
cost per query for a refinement that is small at city scale.

**Administrative region filtering.** Rejected. Region boundaries do not match how people shop, and
they break at region edges.

## Revisit trigger

Users report that radius misrepresents reachability, typically where terrain or road
topology makes straight-line distance misleading.
