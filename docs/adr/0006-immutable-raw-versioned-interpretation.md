# ADR-0006: Raw facts are immutable; interpretation is a separate versioned layer

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

A receipt line is evidence of what a source printed. A canonical product mapping is an
interpretation of that evidence, and interpretations will be wrong.

Catalog mistakes are certain: products will be merged that should be separate, split that should
be merged, and mapped to the wrong canonical identity. Extraction models will improve, and
today's extraction will look poor in a year.

If interpretation is baked into the recorded fact, every one of those mistakes is permanent data
loss, and the loss is invisible because nothing errors.

## Decision

`receipt_lines` records `raw_text` verbatim and is append-only. It is never edited.

Product resolution is a separate, revisable mapping in `chain_lexicon`. Correcting a mapping
reprocesses observations; it does not edit facts.

Extraction is versioned. A re-extraction opens a new `extraction_runs` row and supersedes the
previous one rather than mutating it (ADR-0082).

Nothing is deleted anywhere in the system. Duplicates, fabrications and errors are marked.
Points are reversed by compensating entries. Merges write redirects. The single exception is
erasure, which is honoured by severing identity rather than destroying facts (ADR-0071).

## Consequences

A wrong lexicon entry is repaired by superseding it and reprocessing, with the
underlying evidence untouched.

The corpus can be reprocessed wholesale when extraction improves, which is the largest single
lever on data quality available over the project's life. This is why originals must be backed up
(ADR-0069).

Storage grows monotonically. At this scale that is not a constraint.

Every read path must account for superseded rows, so status filtering is not optional and a
missing filter produces double counting.

Human decisions accumulate as a labelled training set as a byproduct.

## Alternatives considered

**Normalise on ingest, store the resolved product only.** Rejected. Every catalog
mistake becomes irreversible data loss, discovered late or never.

**Soft-delete flags on facts.** Rejected as a weaker form of the same thing: it invites
`WHERE deleted = false` to be forgotten, and it does not solve reprocessing.

**Edit lines in place on correction.** Rejected. Destroys the audit trail that makes a published
figure defensible.

## Revisit trigger

Never. This is the load-bearing principle of the data model.
