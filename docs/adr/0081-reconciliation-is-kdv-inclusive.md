# ADR-0081: Reconciliation is KDV-inclusive

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Reconciliation is the strongest integrity signal in the system. It drives duplicate
detection, review routing and acceptance (ADR-0017, ADR-0058).

The obvious formula adds tax to the sum of line items and compares with the printed total. That is
correct in jurisdictions where prices are quoted exclusive of tax.

TRNC receipts, following Turkish practice, print prices **inclusive** of KDV. The tax line is an
informational breakdown, not an addend.

Applying the wrong formula produces a residual equal to the KDV amount on every healthy receipt,
which disables the primary defence entirely while appearing to work.

## Decision

```
residual = printed_total - ( sum(item lines) - sum(discount lines) )
```

KDV is recorded in `receipts.tax_total_minor` as a reported breakdown and is **never an addend**.

`receipts.discount_total_minor` records the discount sum, and discount lines link to the item they
adjust through `receipt_lines.modifies_line_id`.

A zero residual is `balanced`. A non-zero residual is `residual`, flagged, with targeted review tasks
created. An unparseable total is `unparseable` and goes to the operator queue.

## Consequences

The primary integrity signal works on healthy data rather than firing constantly.

Residual-based review routing becomes usable, including ranking candidate lines by which digit flip
would close a specific gap (ADR-0058).

The formula assumes KDV-inclusive pricing across all local receipts. This should be confirmed against
a real receipt rather than assumed, since the entire integrity layer rests on it.

A receipt from a system that prints exclusive prices would fail reconciliation systematically, which
would be visible as a per-chain pattern rather than as random noise.

## Alternatives considered

**Add tax to line items.** Rejected, and this was a defect found in the v1 audit. It
would make every healthy receipt fail.

**Ignore tax entirely and compare items to total.** This is what the decision does, and stating the
KDV treatment explicitly is what prevents someone reintroducing the addend later.

**Skip reconciliation.** Rejected. It is the strongest and cheapest integrity signal available.

## Revisit trigger

A POS system is encountered that prints tax-exclusive line prices, which would require
per-chain formula selection driven by `chains.pos_vendor`.
