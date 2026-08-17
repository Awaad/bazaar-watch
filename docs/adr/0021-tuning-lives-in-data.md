# ADR-0021: Tuning constants live in validated data, not in code

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Economy constants, integrity thresholds, review quorum sizes, agreement thresholds, bounty
weights, staleness windows and reviewer weight seeds all need frequent adjustment as the corpus and
the contributor base evolve.

Every one of them will be wrong on the first attempt, and several will need changing weekly during
early operation.

A constant embedded in code, or in a database column default, requires a deploy or a migration to
change.

## Decision

All tuning constants live in `config/tuning.json`, validated on load and deployed
independently of code.

They are **not** environment variables. Environment configuration is for provider selection,
credentials and endpoints. Tuning is data with a schema.

Database columns that hold tuned values are `NOT NULL` without defaults, seeded from tuning at
insert, so a constant cannot hide in a DDL default.

`core.tuning` is the only sanctioned reader.

## Consequences

Retuning never requires a deploy or a migration, which matters most during the phase
when tuning is wrong.

Tuning changes are reviewable as a data diff, and their effect is attributable.

Validation must be thorough, because a malformed tuning file is now a production incident.

A value seeded at insert time does not retroactively change for existing rows, which is correct for
snapshot semantics such as `review_responses.weight` and needs care where it is not.

## Alternatives considered

**Constants in code.** Rejected. Deploy per adjustment.

**Constants as column defaults.** Rejected, and actively removed during the v1 audit. A migration
per adjustment, and the value becomes invisible.

**Database-stored settings table.** Rejected for now. Comparable benefit, but loses reviewability of
the change as a diff and adds a read on a hot path.

## Revisit trigger

Tuning needs to differ per region or per contributor cohort, at which point a settings
table with scoping supersedes the flat file.
