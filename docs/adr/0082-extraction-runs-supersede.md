# ADR-0082: Extraction runs supersede, never coexist

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Reprocessing the corpus when a model improves is the largest single lever on data quality
over the project's life (ADR-0013, ADR-0069).

Without an explicit supersession mechanism, a second extraction of the same submission creates a
second receipt and a second full set of observations alongside the first. Every reprocessed receipt
would double-count.

This would not raise an error. It would silently inflate every coverage metric and every index
computation, and it would be attributed to the reprocessing improving coverage.

## Decision

`extraction_runs` records each extraction attempt against a submission, with
`extraction_method`, `extraction_version`, `is_current` and `superseded_by`.

A partial unique index enforces exactly one current run per submission.

`receipts` references its run and is unique on it. `price_observations` carries
`extraction_run_id` for receipt-sourced rows.

Superseding a run moves its observations to `superseded` in the **same transaction** as the new
run's observations are written. Nothing is deleted (ADR-0006).

Every read path filters on observation status, and a missing filter produces double counting rather
than an error.

## Consequences

Reprocessing is safe and the quality lever is actually usable.

Historical extraction output remains inspectable, so an extraction regression can be diagnosed by
comparing runs.

Storage grows with each reprocessing pass, which is acceptable at this scale.

Status filtering becomes load-bearing across every aggregate query, which is a discipline requirement
rather than a schema one.

Crops belong to a specific run, so a re-extraction with different line boundaries orphans old crops
rather than invalidating them.

## Alternatives considered

**Update receipts and lines in place.** Rejected. Violates immutability and destroys
the ability to diagnose extraction regressions.

**Delete the old run's observations.** Rejected. Violates the deletion principle and removes the
audit trail.

**Allow runs to coexist and deduplicate at query time.** Rejected. Every query would need to know the
rule, and one that forgets silently double-counts.

## Revisit trigger

Never, while extraction is versioned.
