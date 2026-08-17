# ADR-0023: Open map data seeds candidates, never branches

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Open map data contains closed stores, wrong pins, cross-provider duplicates and outright
absences. None of these are defects in the source; they are the normal state of crowd-maintained
geographic data.

Access-scoped comparison means a mis-pinned branch does not merely show a wrong dot. It places a
branch inside or outside a user's reachable set incorrectly, which corrupts the comparison itself.

A mixed table of verified and unverified rows invites accidental use of the unverified ones.

## Decision

Pipeline output goes to `branch_candidates`, a separate table, not to `branches` with a
flag.

Promotion is an explicit operator action that confirms chain, name, geometry and address, and writes
`verified_by`, `verified_at` and an `audit_log` row.

**No price attaches to a branch with `verified_by_human = FALSE`.** Observations against an
unverified branch are created but excluded from indices and from access-scoped comparison.

Re-runs upsert on `(source_provider, source_id)`, so the pipeline is idempotent.

Rejected candidates are marked `duplicate` or `rejected` with a reference, never deleted, so a re-run
does not resurrect them.

Manual entry is a first-class path, not a fallback. For thirty branches in one city, typing them is
faster than building and tuning a pipeline.

## Consequences

Verification is on the critical path for publishing anything, since unverified
branches are excluded from every index.

The pipeline is a discovery and audit tool feeding a human queue, not an authority.

Branch verification backlog becomes an operational metric
(`14-observability-analytics.md`).

Deduplication is an operator judgement, and the shopping-centre case where two branches share an
address cannot be resolved by geometry at all.

## Alternatives considered

**Trust map data directly.** Rejected. Closed stores and wrong pins would silently
corrupt comparison.

**Boolean flag on `branches`.** Rejected. One forgotten predicate and unverified rows enter a price
join.

**Auto-verify above a confidence threshold.** Rejected under ADR-0011. Provider confidence measures
record quality, not whether the shop is open today.

## Revisit trigger

Verification backlog becomes the binding constraint on expansion and a measured
auto-promotion accuracy justifies supervised bulk approval.
