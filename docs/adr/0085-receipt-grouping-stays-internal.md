# ADR-0085: Receipt-level grouping is never exposed outside the operator surface

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

`receipt_lines` grouped by `receipt_id` is a basket, even after the contributor reference is
severed to the tombstone.

A basket carries inferences about health, religion, pregnancy and alcohol use. In a market this size,
a single submission from a rural branch at an unusual hour is attributable to a specific person by
someone who knows the area.

Individual observations are unremarkable. The grouping is what carries the sensitivity, which means
severing identity is not sufficient on its own.

## Decision

Public and contributor-facing surfaces expose observations, never receipt-level grouping.

Baskets are visible only on the operator surface.

The exception is a contributor viewing their own submission history, which is their own data. That
endpoint must check ownership before returning grouped lines, which is the most common authorization
bug there is and therefore requires a direct adversarial test rather than incidental coverage.

This joins reviewer independence (ADR-0048) and the one-line cap (ADR-0059) as the three privacy
invariants that live in service code rather than in database constraints.

## Consequences

Basket reconstruction through the public API is prevented by design rather than by
severing alone.

The three service-layer invariants are the thinnest ice in the system and are gated in CI as
mandatory non-skippable tests (`15-repo-structure-standards.md`).

Some legitimate analysis, such as showing a contributor an anonymised example basket, is unavailable
on public surfaces.

Analytics events must never carry receipt composition, which is a separate path that could leak the
same thing by a side door.

## Alternatives considered

**Expose grouped receipts publicly with the contributor severed.** Rejected.
Severing does not defeat re-identification from branch, time and basket composition in a small
market.

**Expose grouping only to high-trust contributors.** Rejected. Adds a privilege tier without changing
the underlying risk.

**Aggregate baskets before exposure.** Deferred. Potentially useful for research output, and it needs
its own disclosure analysis.

## Revisit trigger

A research use case emerges that genuinely needs basket-level data, which would require a
separate anonymisation assessment.
