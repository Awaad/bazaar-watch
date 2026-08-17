# ADR-0008: Lexicon keyed on chain plus SKU, falling back to folded raw text

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Receipt line descriptions are chain-specific truncated abbreviations. `CC KOLA 1LT PET`
means the same thing on every receipt from a given chain, forever, but nothing outside that chain.

Some point-of-sale systems print an item code alongside the description and some do not, and a
single chain may do both depending on terminal and transaction type. A code, where present, is
stable, unambiguous within the chain, and immune to description changes.

Manual resolution of every receipt line does not scale. Automated fuzzy resolution produces
misattributions that propagate to every past and future observation carrying that string.

## Decision

Resolution is exact match on `(chain_id, key_kind, key_value)`, not fuzzy match.

`key_kind` is `sku` where a code is printed, otherwise `raw_text` holding the Turkish-folded
description. Both kinds coexist for one chain. Resolution tries `sku`, then falls back to
`raw_text`. When a line resolves by text while carrying a code, the SKU entry is created as well.

Exactly one `active` entry per key, enforced by partial unique index. Superseded history
accumulates without limit.

`decided_by` is never null. No automated process writes here (ADR-0011).

## Consequences

Resolving a key applies retroactively to every observation already ingested
carrying it, and automatically to every future one. The first receipt from a chain is fully
manual; the fiftieth is nearly automatic.

The operator console's purpose is "resolve unknown keys", not "process receipts", and the queue
is ordered by how many pending observations each key blocks.

Every resolved entry is simultaneously a mapping, a search alias and a labelled training example.

A chain without printed codes gets a weaker key that breaks when a description changes. That is
handled by superseding the entry, not by fuzzy matching.

The Turkish fold must be applied identically at write and lookup, which is why it is centralised
in `core` and guarded by CI (ADR-0025).

## Alternatives considered

**Global product-string mapping.** Rejected. The same abbreviation means different
things at different chains.

**Fuzzy matching at resolution time.** Rejected. Silent misattribution propagates retroactively,
which is the worst failure shape available.

**SKU only.** Rejected. It would exclude every chain whose receipts omit codes, which is a
material share of the market.

## Revisit trigger

A chain is encountered whose receipt descriptions are unstable enough that `raw_text`
keys churn faster than they can be maintained.
