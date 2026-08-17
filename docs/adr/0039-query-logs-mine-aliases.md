# ADR-0039: Query logs are the alias mining pipeline

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Large retailers do not build synonym dictionaries by hand. They mine them from behaviour:
a user searches, gets poor results, reformulates, and clicks. That reformulation-then-click chain is
a labelled synonym pair, produced at no curation cost.

Zero-result queries followed by a successful reformulation are the highest-signal event available in
search.

The alternative is guessing which terms users will type, in four languages, against a catalog whose
names are all in a fifth situation entirely.

## Decision

Every search is logged with locale, folded query, result count and downstream click.

A zero-result query followed within a session by a reformulation and a click is treated as a
candidate synonym pair.

Candidates feed the alias override layer (ADR-0037) and the reranker, and produce a demand-ranked
backlog for operator curation.

`search_queries` carries a partial index on zero-result rows by locale, because that is the query
that drives the backlog.

## Consequences

The alias backlog is ordered by actual demand rather than by guess.

The mechanism requires traffic, so it contributes nothing until the public search surface ships in
P3. Until then aliases come from lexicon entries and operator curation.

Search queries are user data and are subject to the same redaction and erasure rules as anything
else.

Mined pairs are candidates, not aliases. They pass through moderation, consistent with ADR-0011.

## Alternatives considered

**Hand-curate a synonym dictionary.** Rejected. Four languages against disjoint
demographic product sets is unbounded.

**Auto-accept mined pairs above a threshold.** Rejected under ADR-0011, and a wrong alias is
retroactively visible across all search.

**No query logging.** Rejected. Discards the cheapest source of exactly the data that is hardest to
obtain.

## Revisit trigger

Mined pair precision proves high enough over a large adjudicated sample to justify
supervised bulk approval.
