# ADR-0084: One shared tombstone, never a per-user pseudonym

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

On erasure, the contributor reference on retained facts must point somewhere. The obvious
choice is a random identifier per erased user, which preserves the ability to know that a set of
submissions came from one departed person.

That is pseudonymisation, not anonymisation. All of that person's submissions remain linkable to each
other: same identifier, twenty receipts, specific branches, specific times, a reconstructable
shopping profile.

Pseudonymised data remains personal data. The work of erasure would be done and the obligation
retained.

## Decision

All erased contributor references point at a **single shared tombstone**, one well-known
`deleted-contributor` row with `is_tombstone = TRUE`, enforced unique by partial index and seeded by
migration with a fixed identifier.

This dissolves the linkage between an erased person's submissions and therefore actually anonymises.

The lost ability to count one departed person's submissions is recovered, where wanted, by
`erasure_counters`, which holds counts by month and carries no identifier.

Erased contributors are excluded from leaderboards. Aggregate totals remain correct because the
entries are retained.

## Consequences

Erasure is genuinely erasure rather than a rename.

Retroactive fraud analysis loses the ability to group a departed contributor's submissions, which is
a minor analytical loss accepted deliberately.

Foreign key integrity is preserved without nullable references throughout the schema.

The tombstone row must never be deleted or duplicated, which the partial unique index and a seeded
fixed identifier both protect.

## Alternatives considered

**Per-user random pseudonym.** Rejected. Keeps the profile linkable, so the obligation
remains.

**Null the contributor reference.** Rejected. Loses foreign key integrity and the ability to
distinguish "erased contributor" from "no contributor", which matters for scraped rows.

**Delete the rows entirely.** Rejected. Destroys facts about shops that are not personal data.

## Revisit trigger

Never.
