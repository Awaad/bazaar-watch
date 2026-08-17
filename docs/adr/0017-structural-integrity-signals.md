# ADR-0017: Integrity signals: reconciliation, fingerprint, perceptual hash

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

The corpus must resist deliberate manipulation without rejecting real data. In this market
those pull hard against each other, because genuine price dispersion is enormous and an
implausible-looking price is usually real (ADR-0033).

Statistical detection is therefore weak here. Structural detection is not: a receipt either
reconciles arithmetically or it does not, and that judgement is objective and free.

## Decision

Integrity rests primarily on structural checks recorded in `integrity_signals`:

- **`reconciliation`**: item lines minus discounts equals printed total, KDV-inclusive (ADR-0081).
  The strongest signal, and free.
- **`fingerprint_duplicate`**: `(branch, receipt_datetime, total, line_count)`. Catches
  resubmission, which becomes constant once contribution is rewarded.
- **`phash_duplicate`**: perceptual hash of the original. Catches recycled or lightly edited images.
- **`extractor_disagreement`**, **`novel_string`**, **`image_quality`**, **`location_mismatch`**,
  **`conditional_anomaly`** as supporting signals of varying weight.

No signal rejects on its own. All feed a review score (ADR-0018).

## Consequences

Detection works on objective properties rather than on judgements about
plausibility, which is what makes it usable in a high-dispersion market.

A fabricated receipt that reconciles arithmetically, has a novel fingerprint and a novel image is
expensive to produce, which is the point.

Reconciliation correctness is load-bearing. A wrong formula disables the primary defence, which is
why the KDV treatment warranted its own record.

Perceptual hashing must run on the re-encoded image, since re-encoding at ingest changes the bytes
and therefore the content hash.

## Alternatives considered

**Statistical outlier rejection as the primary mechanism.** Rejected in ADR-0033.

**Manual review of everything.** Rejected. Does not scale.

**Cryptographic receipt verification.** Not available. POS systems here emit no signed artefact.

## Revisit trigger

A new fabrication pattern is observed that passes all structural checks.
