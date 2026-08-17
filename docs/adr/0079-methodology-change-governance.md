# ADR-0079: Methodology changes are announced, parallel-run and linked

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Methodology changes are the point at which published statistics lose credibility. A series
that shifts without explanation looks like manipulation even when it is an improvement.

Statistical agencies solved this long ago, and the solution is procedural rather than technical.

A taxonomy restructure changes what a category index means even when no formula changed, so it counts
as a methodology change whether or not it feels like one.

## Decision

Six rules, fixed in advance.

1. **Every run records its methodology.** `methodology_version`, `taxonomy_version`,
   `staleness_window_days`, `missing_policy`. A value without them is not publishable.
2. **Announce before changing.** The change and its rationale are published before the first figure
   computed under it.
3. **Run both series in parallel for three cycles**, published side by side.
4. **Publish a linking factor** so users can splice the two series.
5. **Sunset, do not delete.** The old series stays available permanently, marked superseded.
6. **Never restate a published figure.** A figure published under a given methodology stands as the
   historical record. Corrections are issued as new figures with an erratum.

## Consequences

Users can trust that a published number will not change under them, which is the
foundation of a usable series.

Improvements are possible without destroying continuity.

Three cycles of parallel computation is real work and delays the benefit of any change, which is the
cost of credibility.

`index_runs` uniqueness on methodology version means both series coexist naturally in the schema.

A taxonomy restructure is expensive under this rule, which is a useful disincentive against casual
restructuring (ADR-0009).

## Alternatives considered

**Change methodology and recompute history.** Rejected. Restating published figures is
what destroys trust in a series permanently.

**Never change methodology.** Rejected. Improvements would be impossible and errors permanent.

**Change without announcement.** Rejected. Indistinguishable from manipulation when noticed.

**One cycle of parallel running.** Rejected as too short to demonstrate the relationship between the
series.

## Revisit trigger

Never. This is procedural discipline, not a technical trade.
