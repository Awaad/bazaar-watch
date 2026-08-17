# ADR-0030: Fulfilment is out of scope with no schema commitment

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

The original conception of this project was a delivery service, with the price dataset as
the enabling layer. The dataset then became a project of its own with independent value.

A delivery arm that routes to the cheapest shop and charges the market average is opaque pricing,
run by a platform whose entire brand is price transparency. The moment a user compares the delivery
price to the platform's own price map, the trust that produced the data evaporates.

Speculative schema is cheap to add later and expensive to have present, because it shapes decisions
nobody remembers making.

## Decision

Fulfilment is out of scope. No tables, no columns, no contributor-facing promises that
presuppose it.

The raw observation layer stays complete and queryable so an unforeseen consumer can be served later
without a schema commitment now. Over-aggregation is the failure mode to guard against: detail is
not discarded merely because no current feature needs it.

Revisiting requires a superseding ADR that first resolves the transparency conflict with the
platform's core claim.

## Consequences

Contributor terms describe only what the platform does, which keeps consent honest
and specific.

The dataset remains neutral toward retailers, which preserves the option of them as partners rather
than adversaries.

If fulfilment is later built, it starts from a complete corpus rather than an aggregated one, which
is the expensive thing to recover.

Analytics must be strong enough that a future consumer is served by queries rather than by schema
that was speculatively added.

## Alternatives considered

**Leave a seam with placeholder columns.** Rejected. A speculative column shapes
decisions and is never removed.

**Build fulfilment as originally conceived.** Rejected. The transparency conflict is unresolved and
the delivery economics in a market this size are separately unfavourable.

**Rule it out permanently.** Rejected as overreach. It is deferred, not forbidden.

## Revisit trigger

A superseding ADR that resolves the pricing transparency conflict explicitly.
