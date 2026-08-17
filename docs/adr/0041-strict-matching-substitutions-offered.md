# ADR-0041: Strict matching by default; substitutions offered, never auto-applied

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

A shopping list says "milk". The cheapest reachable branch stocks only a brand the user did
not name, or a 2 by 500g pack where the list said 1kg.

Auto-substituting produces a lower headline saving and a recommendation the user did not ask for. If
they act on it and dislike the result, the platform loses trust for a small gain.

Not offering substitutes at all discards genuine value, since a better unit price on a different
pack size is exactly the kind of thing the dataset is good at spotting.

## Decision

The split basket matches at canonical product level only.

Alternatives, meaning a different brand or a different pack size with a better unit price, are
surfaced as explicit opt-in suggestions and never applied automatically.

`product_groups` defines which substitutions are admissible at all, so the suggestion set is curated
rather than inferred.

Private label never substitutes across chains, because it is not the same good (ADR-0007).

## Consequences

A recommendation always matches what the user asked for, which makes it trustworthy
even when the saving is smaller.

Users who want the saving can take it in one interaction, so the value is not lost.

Missing items are shown as missing rather than silently filled, which makes coverage visible to the
user and is honest about the corpus.

`product_groups` needs curation for substitution to be useful at all, which is operator work.

## Alternatives considered

**Auto-substitute within a product group.** Rejected. An unexpected recommendation
costs more trust than the saving is worth.

**No substitution at all.** Rejected. Discards real value that the unit-price data makes visible.

**Let the user configure substitution tolerance.** Deferred. A setting nobody changes, with a default
that then does the deciding anyway.

## Revisit trigger

Usage shows people habitually accept the offered substitutions, suggesting the default
could invert with a clear indication.
