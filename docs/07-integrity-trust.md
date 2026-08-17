# 07. Integrity and Trust

Two things must be true at once: the corpus must resist deliberate manipulation, and it must
not reject real data. In this market those pull hard against each other, because genuine
price dispersion is enormous and an implausible-looking price is usually real.

## 1. The governing constraint

**Do not reject on magnitude.** Cross-branch dispersion here is large enough that a global
outlier bound would systematically delete the most valuable observations in the corpus, which
are precisely the surprising ones. (ADR-0033)

Everything below follows from that. Integrity rests primarily on **structural** checks, which
are objective and cheap, with statistical signals used only in a **conditional** form and only
as an input to a review score.

## 2. Signal catalogue

Recorded in `integrity_signals`, one row per signal per subject. Nothing here rejects on its
own.

| Signal | Basis | Strength |
|---|---|---|
| `reconciliation` | Item lines minus discounts equals printed total, KDV-inclusive (ADR-0081) | Strongest. Objective, free, catches most single-digit extraction errors and most fabrications |
| `fingerprint_duplicate` | `(branch, receipt_datetime, total, line_count)` | Strong. Catches resubmission, which will be constant once contributions are rewarded |
| `phash_duplicate` | Perceptual hash of the original | Strong. Catches a recycled or lightly edited image |
| `extractor_disagreement` | Two providers differing on a price field | Strong, and far better than either provider's self-reported confidence |
| `novel_string` | A raw key never seen at that chain | Neutral. Routes to review rather than suspicion |
| `image_quality` | Blur, skew, contrast on the region | Weak. Routes to review |
| `location_mismatch` | Derived at ingest, coordinate discarded | Weak. Indoor GPS drift and trivial spoofing (ADR-0057) |
| `conditional_anomaly` | See below | Weak, and easily misread |

### Conditional anomaly

Never against a global distribution. Against the **same product at the same branch** over a
recent window, where variance is small even when cross-branch variance is enormous.

- Median and MAD, not mean and standard deviation. MAD is resistant to heavy tails.
- Score on **change**, not level. A 3% weekly move is background inflation. A 60% drop that
  reverts next week is a signal.
- Judge the receipt jointly. One odd line inside an otherwise reconciling receipt is probably
  a genuine promotion. The same line on a receipt that fails arithmetic is not.

## 3. Soft enforcement

A low integrity score reduces reward and routes to review. It never hard-blocks and never
accuses. Missing EXIF is neutral, because clients legitimately strip it and the server
re-encodes anyway. (ADR-0018)

The reason is asymmetric cost. A false accusation loses a contributor permanently in a small
community where contributors are the scarcest resource. A false acceptance costs one flagged
observation that is excluded from published figures.

## 4. Review tiers

Tiered by what each must expose, so that privacy is structural rather than procedural.
(ADR-0057)

| Tier | Task | Sees | PII exposure | Audience |
|---|---|---|---|---|
| T1 | Lexicon mapping: which product is this string? | Text only | None by construction | Contributors |
| T2 | Transcription check: does this crop say 45.90 or 46.90? | One cropped line | Structurally minimal | Contributors |
| T3 | Full receipt review | Whole image | Real | Operators only |

**T1 is the highest-value tier.** It requires no image, no bounding boxes and no redaction, and
it drains the lexicon gap queue, which is the throughput bottleneck of the entire system. A
reviewer was not at the shelf and cannot adjudicate whether a price was correct; they verify
what the source says. (ADR-0047)

T1 and T2 ship without waiting on the retention question, which gates only T3.

## 5. Question design

Closed form, never open transcription. "Does this say 45.90 or 46.90?" is faster, comparable
across reviewers, and produces clean agreement statistics. Free-text has high variance and is
hard to score. (ADR-0060)

For T1 the options are ranked candidates from hybrid retrieval over the shared embedding
index, plus an explicit "none of these" that escalates to an operator. (ADR-0011, ADR-0040)

## 6. Assignment rules

Three rules that cannot be expressed as database constraints and therefore need direct
adversarial test coverage.

**Independence.** A reviewer never receives a task tracing to their own submission, or to a
submitter with whom they share referral, device fingerprint or a history of mutual review.
Community Notes uses bridging-based ranking because its ground truth is contested along an
ideological axis. A receipt line objectively does or does not say 45.90, so what is needed here
is independence, which is cheaper and better matched. (ADR-0048)

**One line per receipt per reviewer.** A single crop leaks nothing. Many crops from one receipt
let a reviewer reassemble the basket, and baskets carry inferences about health, religion,
pregnancy and alcohol use. (ADR-0059)

**Anonymity.** Submitter identity is never shown to a reviewer. In a market this small,
"someone who shops at the Esentepe branch on Tuesday evenings" can be one person. (ADR-0051)

## 7. Quorum and leases

`review_tasks.required_responses` and `agreement_threshold` come from `tuning.json`, so quorum
can be retuned without a deploy. (ADR-0021)

Leases prevent a task being handed to more reviewers than the quorum needs. A lease expires and
is reclaimed by a scheduled sweep, so an abandoned task returns to the queue rather than
blocking.

Resolution requires weighted agreement at or above the threshold. Weight is
`contributor_trust.review_weight` **snapshotted at answer time** into `review_responses.weight`,
so a later trust recomputation cannot retroactively rewrite a past decision.

Failure to reach the threshold escalates to an operator rather than defaulting either way.

## 8. Honeypots

Tasks whose answer is already known, injected into the queue.

They give an **immediate** accuracy signal rather than waiting for eventual corroboration, which
is what makes reviewer scoring work from a contributor's first session rather than their
fiftieth. (ADR-0061)

Honeypot status is never serialised to a client. Rate is a tuning parameter. Honeypots are drawn
from previously adjudicated tasks so they look exactly like real work.

## 9. Trust

`contributor_trust` is derived and recomputed on adjudication. It is never edited by hand.

| Field | Meaning |
|---|---|
| `submission_accuracy` | Accepted over adjudicated |
| `review_accuracy` | Agreement with ground truth, including honeypots |
| `review_weight` | Seeded low from tuning, rises with demonstrated accuracy, decays with disagreement |

**Reviewers are scored on eventual agreement, never on volume.** Points for reviewing would
produce a rubber stamp that launders bad data with a veneer of validation, and a reviewer who
approves everything to farm points would earn the most. Weight decay is what makes indiscriminate
approval worthless. (ADR-0049)

Trust values are internal. Exposing them to a client is an invitation to game them.

## 10. Adjudication

Operators are the final authority on flagged submissions, escalated review tasks, and disputes.

Every operator action writes to `audit_log` with before and after state. Integrity in this system
rests on human decisions, so those decisions need a record independent of the tables they mutate.

Operators are the only role that reaches receipt originals and therefore the only role that sees
PII. They require a second factor and shorter sessions. (ADR-0083)

Adjudication outcomes:

| Outcome | Effect |
|---|---|
| Confirm | Observations to `accepted`; provisional ledger entry confirmed |
| Reject | Observations to `flagged`; compensating negative ledger entry (ADR-0019) |
| Duplicate | Receipt to `duplicate`; no observations; no points |
| Re-extract | New `extraction_runs` row; previous run superseded (ADR-0082) |

Nothing is deleted at any stage.

## 11. Adversarial cases

| Attack | Defence |
|---|---|
| Store submits fake low prices for itself | Independence rules, fingerprint and phash dedupe, corroboration requirement, receipt arithmetic. A fabricated receipt that reconciles is expensive to produce |
| Store submits fake high prices for a rival | Same, plus conditional anomaly on change within that branch |
| Point farming by volume | Reward tracks marginal information value, not count (ADR-0020) |
| Point farming by rubber-stamp review | Honeypots plus weight decay (ADR-0049, ADR-0061) |
| Collusion ring | Independence rules on referral, device and mutual-review history |
| Resubmitting old receipts | Fingerprint dedupe; recency window on reward eligibility |
| Recycled or edited images | Perceptual hash; re-encoding on ingest removes trivial metadata manipulation |
| Mock GPS | Location is never a gate (ADR-0057) |

The honest limit: a determined actor who photographs genuine receipts from a store they control
can inject real, reconciling, correctly located data. Nothing here prevents that. What prevents it
mattering is corroboration from independent contributors at the same branch, which is a coverage
problem before it is an integrity problem.
