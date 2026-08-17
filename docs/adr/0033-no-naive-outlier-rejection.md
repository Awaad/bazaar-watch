# ADR-0033: No naive global outlier rejection; robust conditional anomaly scoring

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Genuine cross-branch price dispersion in this market is enormous, and the ordering between
shops is conditional on category rather than fixed. A shop cheap on household goods may be dear on
meat.

This is the founding observation of the project. It also means an implausible-looking price is
usually real, and a global outlier bound would systematically delete the most valuable observations
in the corpus.

Within-branch, within-product variance over a short window is a different matter entirely and is
small even when cross-branch variance is huge.

## Decision

No rejection on magnitude against a global distribution.

Anomaly scoring is conditional: same product, same branch, recent window. Median and MAD rather than
mean and standard deviation, since MAD is resistant to heavy tails.

Score on **change**, not level. A 3% weekly move is background inflation; a 60% drop that reverts is
a signal.

Judge the receipt jointly. One odd line inside an otherwise reconciling receipt is probably a
promotion; the same line on a receipt that fails arithmetic is not.

Statistical deviation is one input to a review score alongside reconciliation, fingerprint,
perceptual hash and contributor trust. It is never an authority.

Flagged rows stay in the corpus and are excluded only from published figures. Nothing is deleted
(ADR-0006).

## Consequences

Integrity rests primarily on structural checks, which is why ADR-0017 carries the
weight it does.

Surprising but real prices survive, which is the entire point of the dataset.

Some fabricated prices within the plausible range will pass, mitigated only by independent
corroboration at the same branch.

Conditional anomaly requires history per cell, so it is weak precisely where coverage is thin, which
is where new branches start.

## Alternatives considered

**Global outlier bounds.** Rejected. Deletes the signal the project exists to
capture.

**Reject anything outside a percentage band of the market median.** Rejected for the same reason,
and it would encode an assumption about market efficiency that the founding observation contradicts.

**No statistical detection at all.** Rejected. Conditional detection is genuinely useful; it simply
cannot be an authority.

## Revisit trigger

Measured dispersion falls far enough that global bounds become informative, which would
itself be a significant finding about the market.
