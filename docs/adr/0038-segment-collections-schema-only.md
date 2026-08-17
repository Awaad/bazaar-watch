# ADR-0038: Segment collections exist as schema only until demand is measured

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Different demographics want disjoint product sets. A German shopper wants Quark and
Vollkornbrot; a Russian wants tvorog and grechka; an Arab shopper wants specific rice, tahini and
halal cuts.

This is a genuine differentiating surface for the expatriate audience and a plausible aid to search,
suggestion and basket construction.

It is also entirely speculative. There is no demand signal, no user base, and no basis for choosing
which collections to curate first.

## Decision

`collections` and `collection_members` exist as a join table and nothing else.

No collections are curated. Query logs decide which are worth building.

The schema cost is three columns; the curation cost is the expensive part and it is deferred until
there is a signal.

## Consequences

The schema is ready when demand appears, so building the feature later is content
work rather than a migration.

Nothing is shipped that nobody asked for.

An empty table in the schema is a standing invitation to fill it speculatively, which needs
resisting.

If collections never prove useful, the cost of having been wrong is one unused table.

## Alternatives considered

**Curate collections now.** Rejected. Guessing at demand with no signal, and the
curation is the expensive half.

**Omit the schema entirely.** Rejected. Adding it later is a migration on a live system for
something whose shape is already clear.

**Model collections as tags.** Rejected. Tags are per-product facets; a collection is a curated
ordered set with its own identity and translations.

## Revisit trigger

Query logs show clustered demand for a demographic product set, or an expatriate cohort
requests one directly.
