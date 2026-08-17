# ADR-0070: Two-phase presigned upload

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Receipt images are multiple megabytes. Uploading them through the API ties up request
workers for the duration of a slow mobile upload.

The offline queue retries, so a partially completed upload must be resumable or restartable without
creating duplicates.

The server must nevertheless validate what arrived, since a client-declared upload cannot be
trusted.

## Decision

Three steps.

```
POST /v1/media/upload-slot   -> media_id, presigned PUT url, expires_at
PUT  <presigned url>         -> direct to receipts-original
POST /v1/media/{id}/confirm  -> content_hash
```

On confirm the server verifies the object exists and matches the declared size and hash, re-encodes
it (ADR-0068), and wraps a data key under the contributor's subject key (ADR-0071).

The client idempotency key from ADR-0003 ties the phases together.

If the content hash already exists as an original, confirm **links to the existing object rather than
erroring**. Identical bytes are an identical image, and an offline retry or an honestly duplicated
photo must not fail a submission.

## Consequences

API workers are not held open for mobile uploads, which matters on a small host.

Retries are safe and deduplication is free, since the hash identifies the object.

The upload URL is a bearer credential and is short-lived accordingly.

An abandoned upload leaves an orphaned object, which a scheduled sweep reclaims against unconfirmed
`media_objects` rows.

## Alternatives considered

**Single multipart POST through the API.** Rejected. Ties up workers and interacts
badly with retries.

**Direct upload with no confirm step.** Rejected. Nothing validates what arrived, and the server
would never re-encode.

**Error on duplicate content hash.** Rejected, and this was a defect found in the v1 audit. It fails
a legitimate retry and a legitimate duplicate photograph.

## Revisit trigger

Never, while media is uploaded from mobile clients.
