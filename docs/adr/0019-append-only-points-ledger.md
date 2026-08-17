# ADR-0019: Points are an append-only ledger; balances are derived

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Contributors earn value for accepted contributions. Some of that value may eventually be
converted to money, and a contributor who believes they were cheated will say so publicly in a small
community.

A mutable score column has no history. When a contributor asks why their balance dropped, there is
no answer, and when a bug corrupts a balance there is no way to recompute it.

Reversals are certain: duplicates are detected late, adjudication overturns provisional acceptance,
and fabrications surface after the fact.

## Decision

`points_ledger` is append-only. No mutable score column exists anywhere in the schema.
Balances and leaderboards are derived by aggregation.

Every row carries actor, signed amount, reason code and subject reference.

Reversals are compensating negative rows carrying `reverses_entry_id`. Never a deletion, never an
update.

Reversals are visible to the contributor with their reason. A silent clawback is worse than no
clawback.

All amounts come from `tuning.json` (ADR-0021).

## Consequences

Any balance is reconstructible and any dispute is answerable from the record.

A bug in award logic is correctable by compensating entries without rewriting history.

Balance reads are aggregations rather than column reads, which is trivial at this scale and would
need a materialised balance at a much larger one.

The ledger supports per-contributor, per-period statements for out-of-band payout (ADR-0009 in
`09-contribution-economy.md`).

## Alternatives considered

**Mutable balance column.** Rejected. No history, no dispute resolution, no
recomputation.

**Ledger plus cached balance column.** Rejected for now as premature; the cache is the thing that
goes stale and lies.

**Delete incorrect entries.** Rejected. Destroys the audit trail precisely where it matters most.

## Revisit trigger

Balance aggregation appears in slow query logs, at which point a materialised balance with
a rebuild path is added, never a mutable column.
