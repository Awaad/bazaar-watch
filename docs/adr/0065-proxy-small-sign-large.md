# ADR-0065: Proxy the small things, sign the big things

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Two ways to deliver media to a client: proxy the bytes through the API, or issue a signed
URL and let the client fetch directly from storage.

Proxying gives per-request authorization and an audit trail, at the cost of bandwidth through the
application.

Signed URLs avoid that bandwidth, at the cost of creating a bearer credential that exists outside the
request path and can be shared, logged or cached.

Crops are a few kilobytes. Originals are multiple megabytes.

## Decision

Crops are served **through the API**. Per-request authorization and a free audit trail,
at trivial bandwidth cost. A signed URL for a few kilobytes buys nothing and creates a leakable
artefact.

Originals are served via **short-TTL signed URLs**, minutes rather than hours, to operators and the
worker only. Long-lived signed URLs end up in chat logs, browser history and log aggregators, which
turns a temporary credential into a durable one.

Signed URLs are never logged (`14-observability-analytics.md`).

## Consequences

Every crop delivery is attributable to a request and a reviewer, which supports the
one-line-per-receipt rule and any later investigation.

API bandwidth scales with review volume, which is acceptable at crop sizes and would not be at
original sizes.

Operator access is time-bounded, so a leaked URL expires rather than persisting.

Short TTLs mean a slow operator may need to re-request, which is a small friction accepted for the
bound.

## Alternatives considered

**Signed URLs for everything.** Rejected. Loses per-request authorization and audit
on the highest-volume path.

**Proxy everything.** Rejected. Multi-megabyte originals through the application is bandwidth for no
benefit, and operators are few.

**Long-lived signed URLs.** Rejected. Effectively a permanent credential in an uncontrolled
location.

## Revisit trigger

Crop serving bandwidth becomes material, which would mean review volume has grown
dramatically and is a good problem.
