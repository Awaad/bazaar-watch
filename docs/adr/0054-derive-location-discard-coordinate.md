# ADR-0054: Derive at ingest, discard the coordinate

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Every feature consuming location needs only one thing: whether the capture happened near
the claimed branch. None of them needs the coordinate itself.

Storing the coordinate creates a retention obligation, a breach exposure, an assessment burden, and a
re-identification vector, in exchange for nothing.

EXIF is the loophole. An image can carry GPS even when the application never stores a coordinate
field, which would silently defeat this decision.

## Decision

The server computes whether the capture position was within a threshold distance of the
claimed branch, stores `location_matched` and `location_confidence`, and discards the coordinate.

The coordinate is never written to a column, never logged, and never sent to analytics.

Images are re-encoded on ingest, which strips EXIF including embedded GPS (ADR-0068). Without this,
the coordinate would persist inside the file.

## Consequences

Breach exposure, retention obligation and assessment burden collapse at no functional
cost.

The threshold is a tuning parameter and changing it does not retroactively re-evaluate past
submissions, since the coordinate is gone. Accepted.

Location cannot later be used for a feature that genuinely needs coordinates without a new consent
and a new decision, which is the correct default.

The EXIF dependency must not be broken: any path that stores an image without re-encoding silently
reintroduces the coordinate.

## Alternatives considered

**Store coordinates with a retention window.** Rejected. Creates every obligation for
no additional capability.

**Store a coarse geohash.** Rejected. Still a location trace, still re-identifying in a small market,
still no additional capability.

**Compute client-side and send only the boolean.** Rejected. A client-computed match is trivially
forged, which removes what little signal value it had.

## Revisit trigger

A feature emerges that genuinely requires coordinates, which would need its own consent and
its own record.
