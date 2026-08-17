# ADR-0029: Every published figure carries its methodology, coverage and staleness

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Any figure published will eventually be quoted by someone who did not read the
methodology and challenged by someone who did.

A price index computed on thin, stale or heavily imputed data is not measurement, and presenting it
as such is the fastest way to lose credibility permanently.

Two consumers want different instruments: the public and press want one defensible series over
time, a shopper wants an actionable split. Conflating them produces a number that serves neither.

## Decision

Every `index_runs` row records `methodology_version`, `taxonomy_version`,
`staleness_window_days` and `missing_policy`. A value without them is not publishable.

Every `index_values` row publishes `coverage_pct`, `imputed_pct`, `staleness_days_p50` and
`observations_count` alongside the value.

Values below a stated coverage floor are suppressed rather than published thin.

The index answers "have prices risen". It never answers "where should I shop", which is the split
basket (ADR-0036) and a different instrument entirely.

Limitations are published with the figures, not on request (ADR-0080).

## Consequences

A challenge can be answered with the record rather than with reconstruction.

Suppression is a normal outcome, so coverage becomes an operational target rather than a reporting
detail, and bounties are the lever that moves it (ADR-0020).

Publishing is gated on a methodology document existing, which is why `08-index-methodology.md` is
written before any figure ships.

Some periods will have no publishable figure for some scopes, and that must be presented as absence
rather than filled in.

## Alternatives considered

**Publish a single headline number.** Rejected. Indefensible without its context,
and the first serious question destroys it.

**Publish everything including thin values with a caveat.** Rejected. Caveats are not read;
suppression is.

**Do not publish at all.** Rejected. Publication is most of the project's public value and its route
to credibility.

## Revisit trigger

Never. This is what separates a dataset from a claim.
