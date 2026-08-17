# ADR-0037: Aliases are an override layer, not the retrieval mechanism

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

An earlier framing treated curated multilingual aliases as the way to make a Turkish
catalog searchable in four languages. That does not scale: different demographics want disjoint
product sets, so the curation surface grows without bound and with the catalog.

Dense retrieval handles cross-lingual matching at scale without curation.

What a web-trained model cannot know is the local specifics: TRNC-only brands, private label,
regional product names with no presence in any training corpus.

## Decision

Cross-lingual matching is dense retrieval (ADR-0024). Aliases exist for what embeddings
cannot know.

That is dozens of corrections, not thousands of translations.

Four alias sources, in ascending cost: lexicon entries (free, every resolved receipt string is an
alias), query mining (ADR-0039), contributor proposals through the moderation queue, and operator
curation ranked by logged zero-result volume per locale.

Taxonomy translation is done because browse and filter need it, not as a search strategy.

## Consequences

The curation backlog is demand-ordered and bounded rather than speculative and
unbounded.

Aliases accumulate as a byproduct of work already being done, which is the cheapest possible source.

Embedding failures on local brands are the thing that sizes the alias layer, which is why the model
evaluation set is deliberately weighted toward them.

Contributor-proposed aliases need moderation, adding a queue type.

## Alternatives considered

**Curated aliases as the mechanism.** Rejected. Unbounded, and it was the earlier
position.

**No aliases at all.** Rejected. Local brands have no semantic footprint and dense retrieval will
miss them.

**Machine-translate canonical names into aliases.** Rejected. Confident nonsense on local brand
names, and it pollutes the very layer meant to correct model failures.

## Revisit trigger

Measured embedding failure rate on local brands is high enough that the override layer
becomes a curation burden rather than a correction set.
