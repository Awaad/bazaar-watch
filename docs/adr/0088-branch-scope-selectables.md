# ADR-0088: Index and comparison reach branches only through named selectables

**Status:** Accepted
**Accepted:** 2026-08-20
**Date:** 2026-08-20
**Supersedes:** none
**Superseded by:** none

## Context

Two Accepted records exclude rows from published figures, and both express the
exclusion as a predicate every query must remember.

ADR-0045 keeps online branches in item lookup and price history and out of
access-scoped comparison and per-category chain indices. Its own consequences
section says the quiet part: every index and comparison query carries a
`branch_kind` predicate, and forgetting it is a silent correctness bug rather
than an error.

ADR-0023 does the same for verification. No price attaches to a branch with
`verified_by_human = FALSE`, and observations against an unverified branch are
created but excluded from indices and comparison.

So an index query needs two predicates, from two different records, for two
unrelated reasons, and omitting either produces a plausible number rather than
a failure. The number is then published, and ADR-0079 forbids restating a
published figure: the remedy is an erratum. The cost of the mistake is
therefore not a bug fix, it is a public correction.

`docs/15-repo-structure-standards.md` anticipated a `branch-kind-predicate`
gate that inspects index and comparison queries for the predicate. Attempting
to write it showed why it does not work. Queries are composed across functions
and a join can be assembled in a helper, so a textual gate matching both table
names in one file both misses real violations and fires on prose. A gate that
looks like protection and is not is worse than no gate, by the same argument
this repository uses against placeholder code.

The system already made this move once. Contributor privacy is not a rule
reviewers follow, it is a property of the tiered review structure: T1 sees text
only, T2 sees a cropped line, and the originals bucket has one credential in
one process. The guarantee is structural rather than procedural because a
procedure has to be remembered.

## Decision

Index and comparison code never references the `branches` table. It obtains
branches from one of two named selectables on the `geo` service surface, each of
which carries the exclusions.

`index_eligible_branches()` is physical and human-verified. It is the source for
per-category chain indices (ADR-0034), basket index computation and
access-scoped comparison (ADR-0035).

`public_branches()` is human-verified, of any kind. It is the source for item
lookup and price history, which ADR-0045 keeps online sellers inside.

Neither filters on `operating_status`. A permanently closed branch has real
history, and an index recomputed over a past period must still see the prices
that were observed then. Excluding closed branches here would silently rewrite
history, which is exactly what ADR-0079 forbids. Current-state filtering is a
presentation concern and belongs at the call site that wants it.

The rule is enforced by the `branch-scope` gate: the identifiers `branches` and
`Branch` may not appear in `modules/indexing` or `modules/search`, and raw SQL
naming the `branches` table may not appear outside `modules/geo` and the
migrations.

The selectables return a fresh object per call rather than a module-level
constant, so one query can use the same scope twice without an alias collision.

## Consequences

An exclusion is written once and reviewed once. Adding a third reason to exclude
a branch from indices is an edit to one function rather than an audit of every
query.

The two scopes are visible as names, so a reader of an index query can see which
exclusions apply without holding two ADRs in their head.

`modules/search` may not import `geo` at all under the module map, so its half of
the gate is about raw SQL and table names rather than about the selectables. That
is the correct outcome: search reaches branches through `catalog`, not directly.

The gate is textual and therefore defeatable by anyone determined to defeat it.
It is aimed at forgetting, not at circumvention.

A database view was considered and deferred. Nothing reads raw analytical SQL
yet, and a view with no consumer is the placeholder this repository does not
ship.

## Alternatives considered

**A gate that inspects queries for the predicate**, as `docs/15` originally
described. Rejected. It cannot be written honestly against composed SQLAlchemy
queries, and it cannot fire until the queries exist.

**One selectable instead of two.** Rejected. It would collapse the ADR-0045
exclusion into the ADR-0023 one and lose the case those records exist to
distinguish: an online seller appears in price history and not in a basket
comparison.

**Enforce it in review.** Rejected. That is the procedure this decision replaces,
and the failure mode is silent.

**Row-level security on `branches`.** Rejected. The exclusion depends on what the
query is for, not on who is asking, and RLS cannot express that.

## Revisit trigger

The first consumer of raw analytical SQL over `branches`, at which point the
scopes also become database views so that SQL outside the application cannot
bypass them.
