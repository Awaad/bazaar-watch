# ADR-0057: Review is tiered by what it must expose

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Community review means showing one contributor another contributor's data. Receipt images
carry card digits, loyalty numbers, occasionally names, and the complete basket of one person at one
place and time.

Redacting them is possible but procedural: it depends on a pipeline correctly identifying every PII
region across every POS layout, and a miss is invisible.

Not all review needs an image. Mapping `CC KOLA 1LT PET` to a canonical product is a pure text
question, and it is also the highest-volume task and the actual bottleneck.

Verifying a specific digit needs only the line, not the document. PII lives in the header and footer;
line items are product and price.

## Decision

Three tiers, distinguished by what each must expose.

**T1, lexicon mapping.** Text only. No image, no bounding boxes, zero PII by construction. Highest
volume, and it unblocks the bottleneck.

**T2, transcription check.** One cropped line region. PII is structurally absent rather than
redacted, because it is not present in the crop.

**T3, full receipt.** Operator only.

T1 and T2 therefore ship without waiting on the retention question, which gates only T3.

Cropping does not replace originals, which remain the reprocessing corpus and the evidence behind
disputes (ADR-0016).

## Consequences

Safety is structural rather than procedural, which is the same principle as capability
isolation in ADR-0064: make the dangerous thing absent rather than check for it.

The legal retention question moves off the critical path for community contribution, which was the
worst dependency in the plan.

Per-line bounding boxes become a hard extraction provider requirement, since T2 is impossible without
spatial anchors (ADR-0013).

Reviewers lose context. A crop cannot be checked for reconciliation, store match or duplication,
which is why those remain structural checks and operator work.

Crops must share the subject key of their original, or shredding leaves fragments (ADR-0073).

## Alternatives considered

**Full-receipt review for everyone after redaction.** Rejected. Depends on a redaction
pipeline being perfect across every layout, and a miss is invisible.

**Operator-only review.** Rejected. It is the bottleneck.

**Blur PII regions in place.** Rejected. Same dependency as redaction, with the original still
present in the delivered image.

## Revisit trigger

A review need emerges that genuinely requires whole-document context from non-operators,
which would require the retention answer first.
