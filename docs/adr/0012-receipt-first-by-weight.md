# ADR-0012: Receipt-first by weight, not by capability

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Four capture paths exist: receipt photo, barcode scan, manual shelf entry and scrape.

A receipt yields 20 to 40 attributed, timestamped observations with an arithmetic self-check, and
covers produce, bakery and butcher items that carry no barcode. A barcode scan yields one
observation and requires photographing shelves in a shop that may not permit it.

Product effort is finite and must be concentrated. Backend capability is cheap to build once and
expensive to retrofit.

## Decision

Receipt capture receives the app UX emphasis and the reward weighting.

Barcode and manual shelf capture are supported from day one. They are the same
`price_observation` with a different `source_kind`, not a separate pipeline.

Nothing downstream branches on capture method except where provenance is explicitly relevant.

## Consequences

The highest-yield path gets the design attention, and the categories with the
greatest price variance are covered.

No refactoring is required to add barcode prominence later, because the backend already treats it
as a first-class source.

Receipt capture depends on extraction quality, which is a provider risk concentrated in one
place (ADR-0013).

Shelf capture remains the answer to "what does this cost right now", which a receipt cannot
answer.

## Alternatives considered

**Barcode-first.** Rejected. One observation per interaction, no produce coverage,
no arithmetic self-check, and higher social friction in-store.

**Receipt-only.** Rejected. Retrofitting a second source into an ingest pipeline that assumed one
is exactly the avoidable cost.

**Manual entry only.** Rejected. Does not scale past a single operator.

## Revisit trigger

Extraction accuracy proves unusable on local receipts, which would invert the relative
value of the two paths.
