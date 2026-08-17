# ADR-0087: Independents are chains of one

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Overture returns independent shops as well as chain branches. A record such as
`H.Gül Market` in Girne has a name, a category and a point, and no chain.

`branches.chain_id` is `NOT NULL`, which looks wrong when confronted with an independent shop and
invites a well-meaning correction to make it nullable.

The constraint exists because `chain_lexicon` is keyed on `chain_id`. An independent's receipts still
need their own key namespace, since their POS abbreviations are theirs alone.

## Decision

An independent shop gets a `chains` row with exactly one branch.

`branches.chain_id` stays `NOT NULL`.

The reason is recorded here explicitly, because the constraint reads as a modelling error on
inspection and the consequence of "fixing" it is that lexicon resolution silently loses its
namespace.

Chains of one are also the natural home for `pos_vendor`, which matters for receipt layout regardless
of whether a shop is part of a group.

## Consequences

Lexicon resolution works uniformly for chains and independents with no special
casing.

The `chains` table contains many single-branch rows, which is slightly odd to read and entirely
correct.

Chain-level index scopes will include many chains of one, which needs handling in presentation:
a chain index for a single independent shop is really a branch index.

Branch candidate promotion must create a chain row where none matches, which is an extra operator
step for independents.

## Alternatives considered

**Nullable `chain_id`.** Rejected. The lexicon loses its namespace and receipt strings
from different independents would collide.

**A single synthetic "independent" chain for all of them.** Rejected. Worse than nullable: all
independents would share one lexicon namespace and their abbreviations would collide with each
other.

**Separate `independent_shops` table.** Rejected. Duplicates the entire branch model and every query
against it.

## Revisit trigger

Never, while the lexicon is chain-scoped.
