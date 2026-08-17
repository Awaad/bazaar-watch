# ADR-0068: Re-encode at ingest; never store the upload verbatim

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

An uploaded image carries more than pixels. EXIF can contain GPS coordinates, device
identifiers and timestamps.

Storing the file verbatim would retain the precise coordinate that ADR-0054 exists to discard, inside
the file, where nobody thinks to look. That is a silent contradiction between two decisions that both
appear correct in isolation.

Image parsers also have a long history of vulnerabilities, and accepting arbitrary uploaded bytes into
a processing pipeline is an attack surface.

## Decision

Every uploaded image is re-encoded on ingest. The upload is never stored verbatim.

Re-encoding accomplishes three things in one step: it strips EXIF including embedded GPS, it
normalises format and colour space, and it neutralises malformed-image exploits by producing a fresh
file from decoded pixels.

`media_objects.reencoded` records that it happened.

Content hashing for deduplication runs on the re-encoded bytes, since those are what is stored, and
perceptual hashing likewise.

## Consequences

The location minimisation decision actually holds, rather than being defeated by
file metadata.

Upload handling is safe by construction rather than by validation, which is the same principle as
elsewhere in the design.

Some image quality is lost to re-encoding, which is immaterial for receipt legibility.

Any future path that stores an image without re-encoding silently reintroduces the coordinate, so
this is an invariant rather than a preference.

## Alternatives considered

**Strip EXIF without re-encoding.** Rejected. Solves one of three problems and leaves
the parser attack surface intact.

**Trust clients to strip EXIF.** Rejected. Clients vary, and ADR-0018 treats missing EXIF as neutral
precisely because it cannot be relied upon either way.

**Store verbatim, strip on serve.** Rejected. The coordinate persists at rest, which is what the
decision exists to prevent.

## Revisit trigger

Never.
