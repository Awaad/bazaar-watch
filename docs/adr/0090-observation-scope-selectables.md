# ADR-0090: Aggregates reach observations only through named selectables

**Status:** Accepted
**Accepted:** 2026-08-20
**Date:** 2026-08-20
**Supersedes:** none
**Superseded by:** none

## Context

ADR-0082 says it plainly in its own consequences: every read path filters on
observation status, and a missing filter produces double counting rather than an
error.

That is a stronger version of the problem ADR-0088 already solved for branches.
`price_observations` accumulates superseded rows **by design**. Reprocessing a
corpus when the extraction model improves writes new observations and moves the
old ones to `superseded` in the same transaction. Nothing is deleted, because
ADR-0006 makes the record append-only and an observation that vanished is an
observation nobody can audit.

So the table always contains rows that must not be counted, and the number of
them grows every time the model gets better. An aggregate that forgets the
predicate does not fail, it returns a figure inflated by exactly the amount of
reprocessing that has happened. Under ADR-0079 that figure, once published,
stands permanently with an erratum.

`unresolved` is a second trap in the same table. `product_id` is nullable
deliberately: an unresolved observation is a real fact that simply has no product
to aggregate under yet. An aggregate that groups by `product_id` without
excluding nulls produces a bucket of unrelated prices from unrelated goods.

`docs/15-repo-structure-standards.md` anticipated an
`observation-status-predicate` gate that inspects aggregates for the filter. It
is unwritable for the same reason the `branch-kind-predicate` gate was: queries
compose across functions, and a textual gate matching a table name and a status
word in one file both misses real violations and fires on prose.

## Decision

Aggregate and comparison code never references the `price_observations` table.
It obtains observations from one of two named selectables on the `observations`
service surface.

`countable_observations()` is accepted and resolved to a product. It is the
source for index computation, basket values and any published figure.

`unresolved_observations()` is every observation with no product, regardless of
status. It is the source for review task generation. It deliberately does not
filter on status, because a pending unresolved row is exactly what a T1 task is
for and requiring acceptance first would deadlock the queue that does the
accepting.

The rule is enforced by extending the `branch-scope` gate rather than adding a
second one: the identifiers `price_observations` and `PriceObservation` may not
appear in `modules/indexing`, `modules/search` or `modules/economy`, and raw SQL
naming the table may not appear outside `modules/observations` and the
migrations.

Each call returns a fresh object, so one query can use a scope twice without an
alias collision.

## Consequences

The status predicate is written once and reviewed once. Adding a third reason to
exclude an observation is an edit to one function.

`economy` is in the restricted set where it was not for branches, because bounty
payout aggregates over observations and paying twice for a reprocessed receipt is
the same defect wearing different clothes.

The two scopes cannot be composed into one query without care: they are disjoint
by construction, and a caller wanting both wants a union rather than a join.

This does not stop anyone determined to query the table directly. It is aimed at
forgetting.

## Alternatives considered

**A gate that inspects aggregates for the predicate**, as `docs/15` described.
Rejected for the reasons in ADR-0088, which apply unchanged.

**A view excluding superseded rows.** Deferred, exactly as in ADR-0088. Nothing
reads raw analytical SQL yet, and a view with no consumer is a placeholder.

**Deleting superseded observations.** Rejected: ADR-0006 makes the record
append-only, and the superseded rows are the evidence that a reprocessing
happened at all.

**A partial index instead of a scope.** An index makes the correct query fast.
It does nothing to make the incorrect query fail, and the incorrect query is the
one that ships.

## Revisit trigger

The first consumer of raw analytical SQL over `price_observations`, at which
point both scopes also become database views.
