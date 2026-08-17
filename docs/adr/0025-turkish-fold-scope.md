# ADR-0025: One Turkish fold, applied to lexical matching only

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Turkish casing is locale-dependent in a way that breaks naive implementations: `i`
uppercases to `İ` in Turkish and `I` elsewhere, and `I` lowercases to `ı`. A lexicon key built with
the wrong casing silently fails to match, and nothing raises an exception.

The lexicon is exact-match on folded text, so write-side and read-side folding must be byte-identical
or resolution fails invisibly.

Embedding models are trained on natural text with diacritics. Stripping them degrades retrieval, and
the degradation is not visible without measurement.

## Decision

One fold function in `core`: `ı İ` to `i`, `ş` to `s`, `ğ` to `g`, `ç` to `c`, `ö` to
`o`, `ü` to `u`, plus `tr_TR` case normalisation, whitespace collapse and trailing quantity artifact
stripping.

It has exactly two consumers: lexicon keys and trigram matching. It is deliberately lossy.

**It is never applied to embedding input.** `product_search_docs` carries `lexical_text` (folded) and
`semantic_text` (unfolded) as separate columns so the paths cannot be confused.

Locale-naive `upper()`, `toUpperCase()` and `casefold()` are banned by a CI grep gate.

The fold is mirrored as an immutable SQL function for index expressions, so index and query agree.

Turkish collation (`tr-TR-x-icu`) governs display ordering, which is a different concern and is not
conflated with matching.

## Consequences

Lexicon resolution is reliable across chains and clients.

The two-column design costs storage and a rebuild step, and buys correctness on both paths.

Any new text path must consciously choose folded or unfolded, which is a small ongoing tax and the
point.

`unaccent` alone is insufficient, so the implementation cannot be delegated to a Postgres extension
and must be kept in sync between application and SQL.

## Alternatives considered

**Postgres `unaccent`.** Rejected. Does not handle the dotless i correctly.

**Fold everything including embedding input.** Rejected. Degrades cross-lingual retrieval quietly.

**Store only unfolded text and fold at query time.** Rejected. Cannot index on it efficiently and
invites write and read paths diverging.

## Revisit trigger

Never, absent a change in how Turkish text is encoded.
