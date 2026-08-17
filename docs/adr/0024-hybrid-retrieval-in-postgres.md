# ADR-0024: Hybrid retrieval in Postgres; no Elasticsearch

**Status:** Accepted
**Accepted:** 2026-08-17
**Open parameter:** Embedding model and vector dimension, pending evaluation. The retrieval architecture is settled.
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Cross-lingual grocery search fails on lexical matching because the hard cases have zero
character overlap: `Käse` to `peynir`, `гречка` to `karabuğday`, `tvorog` to `lor peyniri`. Trigram
reaches `Emmentaler` to `Emmental` and nothing harder.

The catalog is Turkish and there is no supply side to localise it, unlike a retailer whose sellers
submit localised titles. Translation as a strategy is unbounded, because different demographics want
disjoint product sets.

Brands, barcodes and SKUs are exactly what dense embeddings blur and lexical matching handles well.

Scale is a few thousand products.

## Decision

Hybrid retrieval inside Postgres: `pg_trgm` GIN over folded `lexical_text`, and
`pgvector` HNSW over unfolded `semantic_text`, fused by reciprocal rank fusion.

`product_search_docs` carries the two inputs as separate columns, because the Turkish fold is lossy
and correct for trigram while degrading a model trained on natural diacritics (ADR-0025).

No Elasticsearch.

The embedding model is undecided and sits behind an `EmbeddingProvider` interface. The vector column
is deliberately unpinned in the schema until selection, since candidates differ in dimension and
HNSW requires a fixed one.

## Consequences

One datastore to run, back up and keep synchronised. No index-sync bug class.

Cross-lingual matching works without a translation project, which was the alternative that does not
scale.

Search is not runnable until the migration that pins the dimension and creates the HNSW index, so
model selection blocks the search surface.

An embedding model must be served, which is why it lives in the worker rather than the API
(ADR-0043).

Fusion weighting cannot be tuned without traffic, so a defensible default ships and query logs drive
tuning later (ADR-0039).

## Alternatives considered

**Elasticsearch.** Rejected. A second stateful service to run, back up, monitor and
synchronise, for a catalog of a few thousand products. Its Turkish analyser and stemming matter less
than aliases and dense retrieval do for short noun phrases.

**Trigram only.** Rejected. Cannot bridge zero-overlap pairs, which is the actual requirement.

**Curated multilingual aliases as the mechanism.** Rejected and demoted to an override layer
(ADR-0037). Unbounded curation across disjoint demographic product sets.

**Dedicated vector database.** Rejected. Colocation removes a synchronisation problem at this
scale.

## Revisit trigger

Measured recall@k below target after reranking, or HNSW index build time exceeding the
maintenance window.
