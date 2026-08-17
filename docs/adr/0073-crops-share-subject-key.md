# ADR-0073: Crops share their original's subject key

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Crops are derived from originals and live in a different bucket with different access
rules.

If crops were encrypted independently, or not encrypted at all, shredding an original would leave
crops readable. Those crops are line items from the erased contributor's basket, which is exactly the
sensitive content the shredding was meant to destroy.

Partial destruction is worse than none, because it creates a belief that erasure happened.

## Decision

Crops are encrypted under the same per-subject KEK as the original they derive from.

`media_objects.subject_user_id` records the subject for every object regardless of role, and
`wrapped_dek` holds the object's data key wrapped by that subject's KEK.

Shredding a subject key renders originals and crops unreadable in the same operation.

## Consequences

Erasure is complete across derived artefacts, not just the source.

The extraction fine-tuning corpus (ADR-0062) shrinks with each erasure, since the image half of each
pair becomes unreadable. The confirmed text labels survive severed, retaining lexicon value but not
vision training value. Stated rather than discovered.

Crop generation must know the subject at generation time, which it does because it runs in the worker
with the submission in hand.

Reviewers holding a crop in memory at the moment of shredding are outside the system's control, which
is an inherent limit rather than a design gap.

## Alternatives considered

**Encrypt crops independently.** Rejected. Leaves readable fragments after shredding.

**Delete crops on erasure rather than shred.** Rejected. Crops are in a bucket without object lock so
deletion would work, but a two-mechanism erasure is more likely to have a gap than a single one.

**Do not encrypt crops.** Rejected for the same reason.

## Revisit trigger

Never, while crops derive from personal media.
