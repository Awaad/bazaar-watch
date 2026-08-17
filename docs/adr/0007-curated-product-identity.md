# ADR-0007: Product identity is curated, not derived

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

A canonical product is the anchor for price history, basket composition, index
computation and comparison. If identity is wrong, every downstream feature is wrong in a way
that is difficult to detect and expensive to unwind.

Barcodes look like identity and are not. The same code is reused after a product is
discontinued, one product carries several codes across packaging revisions, and variable-weight
codes encode weight rather than product. Scraped catalog names carry the scraper's spelling and
categorisation errors. Receipt strings are truncated abbreviations that differ per chain.

Automated identity resolution over these sources would be confidently wrong at scale.

## Decision

A canonical product is defined by a human. Barcodes, receipt strings and scraped names
are attributes and evidence, never identity.

Separate products: different net content, different formulation, private label from different
chains. `product_groups` handles substitution where a feature needs it.

Same product: packaging revisions with different barcodes, regional name variants of an identical
SKU. These become GTIN rows and aliases.

Merges are operator actions. A merge writes `merged_into_id`, repoints lexicon entries, and
leaves the losing row in place.

Seeded rows from scraping carry `source = 'scrape'` and `verification_state = 'unverified'`
(ADR-0046).

## Consequences

Catalog quality is bounded by operator attention, which makes the lexicon
resolution rate the single most important operational metric (`14-observability-analytics.md`).

Merges are reversible, which matters because a merge of two genuinely distinct products is a
mistake that will be made and must be recoverable.

Net content and brand are effectively required on any `active` product, since without them
shrinkflation is invisible and comparison is unsound.

Private label carries `owner_chain_id` and is excluded from cross-chain comparison, so basket
indices do not silently compare goods that are not the same good.

## Alternatives considered

**GTIN as primary identity.** Rejected. Code reuse, multi-code products,
variable-weight codes and unbarcoded produce each break it independently.

**Automated clustering of receipt strings.** Rejected. It would be wrong at a rate that is
invisible until an index is published and challenged.

**Accept scraped catalogs as ground truth.** Rejected. Inheriting another party's errors as fact
is worse than having no seed at all, because the errors are then invisible.

## Revisit trigger

Operator curation becomes the binding constraint on growth and a measured
suggestion-acceptance rate is high enough to justify supervised bulk approval.
