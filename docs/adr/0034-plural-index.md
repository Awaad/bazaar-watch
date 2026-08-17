# ADR-0034: The index is plural: per-chain, per-branch and per-category

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Chain-level price tendencies are real and reasonably stable. Some chains are generally
dear, others generally cheap.

But the tendency is **conditional on category**. The actionable observation is that one shop is
cheap on household goods while another is cheap on meat, and a single blended basket number destroys
exactly that signal by averaging it away.

A single headline number is also what a price index is conventionally expected to be, and it is what
makes the figure publishable and comparable over time.

## Decision

The index is computed at multiple scopes: `market`, `chain`, `branch` and `category`.

The market-level fixed-basket figure is retained for publication and time-series comparison.

Per-category indices carry the user-facing value, because category is where the stable, actionable
differences live.

`index_values.scope_kind` and `scope_id` express the scope, with `scope_id` null at market level,
which is why that table needed a surrogate key.

## Consequences

Publication and usefulness are served by the same computation rather than by
competing ones.

Per-category coverage is thinner than aggregate coverage, so more category values will fall below
the suppression floor.

The number of published values multiplies by scope, which makes the coverage and staleness columns
per value rather than per run essential.

Which categories show stable chain-level ordering is an empirical question answered by the corpus,
and it determines which per-category indices are worth publishing at all.

## Alternatives considered

**Single blended market index only.** Rejected. Publishable and useless, since it
averages away the actionable signal.

**Per-category only, no market figure.** Rejected. Loses the comparable headline series that makes
the work legible to press and researchers.

**Store-level league table as the headline.** Rejected in favour of the split basket (ADR-0036),
because a ranking is only actionable if the ordering is stable and unconditional, which it is
not.

## Revisit trigger

Measured rank stability per category, from the corpus, showing that some categories are
too volatile to publish at all.
