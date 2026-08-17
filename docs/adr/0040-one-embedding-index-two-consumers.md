# ADR-0040: One embedding index serves both search and lexicon suggestion

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Two apparently separate problems turn out to be one. Making a German find `peynir` is
matching a query in one language to a catalog entry in another. Ranking candidates for
`EMMENTAL PEYNIR 200G` from a receipt line is matching an abbreviated source string to the same
catalog.

Both are retrieval against the canonical product catalog, differing only in what sits on the query
side.

Building them separately would mean two indexes, two models to serve and two things to keep
synchronised with catalog changes.

## Decision

One vector index over `product_search_docs.semantic_text`, serving both user search and
lexicon suggestion.

Lexicon suggestion queries it with `interpreted_text` from extraction, not `raw_text`, because
uppercase truncated abbreviations are not natural language (ADR-0013).

Both paths use the same hybrid fusion with trigram for brands and near-literal matches.

This moves the embedding investment earlier than a search-only justification would, since suggestion
is needed in P2 while public search lands in P3.

## Consequences

One model to serve, one index to maintain, one rebuild path on catalog change.

The embedding decision blocks both search and suggestion quality, which raises its priority.

Improvements to the index benefit both consumers at once.

If the two query distributions diverge enough that one model cannot serve both well, this
consolidation would have to be unwound, which is the risk being taken.

## Alternatives considered

**Separate indexes tuned per consumer.** Rejected as premature. One index is
strictly simpler and there is no evidence yet that tuning diverges.

**Lexical-only suggestion, dense search only.** Rejected. Suggestion is exactly where cross-form
matching helps most.

**Defer embeddings until P3.** Rejected. It would leave T1 review without ranked candidates during
the phase when throughput matters most.

## Revisit trigger

Measured performance shows the two query distributions need materially different
treatment.
