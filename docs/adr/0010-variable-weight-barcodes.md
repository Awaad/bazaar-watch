# ADR-0010: Variable-weight and in-store barcodes are not product identities

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

EAN-13 codes beginning with `2` are reserved for in-store restricted circulation.
Supermarkets commonly use them for deli, butcher and produce items, encoding weight or price
into the code itself.

Two packs of the same cheese therefore scan as two different barcodes. Treating these as product
identifiers would generate thousands of phantom products, each with a single observation,
poisoning the catalog and every coverage metric derived from it.

Loose produce frequently carries no identifier at all, and it is the category with the highest
price variance.

## Decision

Barcodes are prefix-checked at ingest. Codes in the restricted-circulation range are
routed to the weight-item path and never treated as product identities.

`product_gtins.gtin_kind` distinguishes `ean13`, `ean8`, `upc`, `plu` and `chain_internal`.
Global uniqueness applies only to real GTINs; `chain_internal` codes are scoped by `chain_id`
because they legitimately collide across chains.

Loose produce is a first-class capture path, not an afterthought.

## Consequences

Weight items resolve through the lexicon by description rather than by code, which
is slower to bootstrap and correct.

Catalog pollution from a well-known trap is avoided before it starts.

Barcode capture UX must handle the case where a scan yields no product and falls through to
description entry.

`product_gtins` carries two partial unique indexes rather than one constraint, which is slightly
more complex and correctly models two distinct namespaces.

## Alternatives considered

**Treat all barcodes uniformly.** Rejected. Generates phantom products at scale.

**Reject restricted-range barcodes.** Rejected. Deli and butcher items are real observations and
high-variance ones.

**Parse weight out of the barcode.** Deferred. The encoding is chain-specific and undocumented;
the printed line already carries quantity.

## Revisit trigger

A chain's encoding is documented well enough to extract weight reliably, which would
improve unit-price derivation for weight items.
