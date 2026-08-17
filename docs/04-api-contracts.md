# 04. API Contracts

Two clients (Expo app, operator console) and a public web surface consume one API. Those
workstreams run in parallel, frequently by different agents/devs, against a specification that
is still moving. Contract drift is therefore the primary engineering risk in this project,
and the machinery in this document is the mitigation. (ADR-0042)

## 1. The generation chain

```
FastAPI route + Pydantic model
        |  (emitted, never hand-written)
        v
   openapi.json  ---- committed to the repo, diffed in CI
        |
        +--> packages/api-client-ts   (Expo + console)
        +--> mock server              (client work precedes endpoints)
        +--> packages/api-types       (enums, constants, error codes)
```

**The specification is emitted from the implementation.** It is never authored by hand and
never edited after generation. A hand-maintained spec eventually lies about the code, and
a spec that lies is worse than no spec because both clients trust it.

**Clients are generated from the specification.** A hand-written `fetch` call against an
API route is a CI failure, not a style preference.

**Enumerations and constants are generated too.** Drift usually enters through a status
string rather than through a shape. `StrEnum` in Python is the single definition; it flows
to OpenAPI, to TypeScript, and to the database `CHECK` constraint.

**The mock server is generated.** Client workstreams build and test against it before the
endpoint exists, which is what makes parallel work possible at all.

## 2. CI gates

| Gate | Fails when |
|---|---|
| `openapi-fresh` | Regenerating `openapi.json` produces a diff. The spec is stale. |
| `contract-diff` | The diff against the **merge base of the target branch** contains a breaking change without a version bump. Comparing against the previous commit gives false passes on any branch with more than one commit. |
| `client-fresh` | Regenerating clients produces a diff. |
| `no-handwritten-calls` | Any `fetch(` or `axios(` targeting an API path outside the generated client. |
| `enum-parity` | A `CHECK` constraint and its `StrEnum` disagree. |
| `i18n-parity` | A locale file is missing keys present in another. |

Breaking changes: removing a field, narrowing a type, adding a required request field,
removing an enum member, changing an error code. Adding an optional field or a new enum
member that clients may ignore is additive.

## 3. Versioning

`/v1` from the first commit. Within `v1`, additive change only.

Clients send `X-Client-Version`. The server may respond `426 Upgrade Required` with a
problem document when a client is below the minimum supported build, which is the only
mechanism available once an app is in users' hands.

## 4. Authentication

Phone OTP through a pluggable `SmsProvider`. (ADR-0028)

```
POST /v1/auth/otp/request     { phone_e164 }              -> 202
POST /v1/auth/otp/verify      { phone_e164, code }        -> { access, refresh }
POST /v1/auth/refresh         { refresh }                 -> { access, refresh }
POST /v1/auth/logout          { refresh }                 -> 204
```

Short-lived access token, rotating refresh token. Rate limits on `otp/request` per phone
and per IP, enforced in Redis. (ADR-0005)

Roles are `contributor`, `moderator`, `operator`, `admin`. Authorization is enforced in the
service layer, never in the route decorator alone, because the same operation is reachable
from more than one route.

Operators and admins are the only roles that can reach receipt originals and therefore the
only roles that see PII. They require a second factor, shorter session lifetimes, and every
action they take is written to `audit_log`. Treating them as ordinary users with a wider
role check would make the most sensitive access path the least protected.

## 5. Errors

RFC 9457 problem details, `application/problem+json`.

```json
{
  "type": "https://bazaarwatch.dev/errors/submission-duplicate",
  "title": "Submission already received",
  "status": 409,
  "detail": "A submission with this idempotency key was already accepted.",
  "code": "SUBMISSION_DUPLICATE",
  "instance": "/v1/submissions",
  "errors": [{ "field": "client_idempotency_key", "code": "DUPLICATE" }]
}
```

`code` is the contract. `title` and `detail` are human-facing and may change without a
version bump; clients never branch on them. Error codes are generated into
`packages/api-types` and are covered by `contract-diff`.

Validation failures return `422` with a populated `errors` array. Every field code is
translatable client-side, so no server string is ever shown to a user directly.

## 6. Idempotency

Every mutating endpoint accepts `Idempotency-Key`. For submissions this is the
`client_idempotency_key` generated offline by the app, which is a v4 token and never a
primary key. (ADR-0003)

Replay semantics: the same key with the same body returns the original response and the
original resource. The same key with a different body returns `409`.

"Same body" is decided by a canonical hash of the request body, stored in Redis alongside
the original response for 24 hours, keyed by `(user_id, endpoint, idempotency_key)`. The
window is bounded because an offline queue that has not drained in a day has a worse
problem than replay.

This is not optional for the app. An offline queue retries, networks fail mid-request, and
at-least-once delivery is the only honest assumption. (ADR-0015)

## 7. Pagination

Cursor-based only. Offset pagination is banned: it produces duplicates and gaps under
concurrent inserts, and `price_observations` is the most insert-heavy table in the system.

```
GET /v1/observations?branch_id=...&limit=50&cursor=<opaque>
```

```json
{ "items": [...], "next_cursor": "...", "has_more": true }
```

UUIDv7 primary keys are time-ordered, so keyset pagination on `(created_at, id)` is both
correct and index-friendly. The cursor is opaque and its encoding is not part of the
contract.

## 8. Media upload

Two-phase. Multi-megabyte uploads through the API tie up request workers and interact
badly with an offline retry queue. (ADR-0070)

```
POST /v1/media/upload-slot
  { submission_key, mime_type, byte_size }
  -> { media_id, upload_url, expires_at }

PUT <upload_url>                      (direct to object storage)

POST /v1/media/{media_id}/confirm
  { content_hash }
  -> { media_id, status }
```

The server validates the object exists, matches the declared size and hash, re-encodes it
to strip EXIF and normalise format, and only then marks it usable. (ADR-0068)

Contributors never receive a URL for an original. The endpoint that issues signed URLs has
no code path to the originals bucket for non-operator roles, and the API process holds no
credential for that bucket at all. (ADR-0064, ADR-0065)

## 9. Endpoint groups

| Group | Purpose | Roles |
|---|---|---|
| `/v1/auth/*` | OTP, tokens | public |
| `/v1/me/*` | Profile, locale, points balance, submission history | contributor |
| `/v1/submissions/*` | Create, confirm, status | contributor |
| `/v1/media/*` | Upload slot, confirm | contributor |
| `/v1/review/tasks` | Next task (leased), submit answer, skip | contributor |
| `/v1/branches/{slug}/attributes` | Aggregated ordinal ratings; submit a rating | public read, contributor write |
| `/v1/me/notifications` | Push token registration, preferences | contributor |
| `/v1/catalog/*` | Product read, search, taxonomy | public |
| `/v1/branches/*` | Branch read, nearby | public |
| `/v1/prices/*` | Observations for a product, history, staleness | public |
| `/v1/baskets/*` | Basket definition, split basket computation | public |
| `/v1/index/*` | Published index values | public |
| `/v1/ops/*` | Lexicon queue, catalog curation, branch verification, adjudication | operator |

`/v1/ops/*` is a distinct group rather than a role check on shared routes. It carries
different rate limits, different audit logging, and different response shapes, and the
separation makes an authorization mistake structurally harder.

## 10. Response conventions

Public identifiers are slugs. Internal UUIDs never appear on public read surfaces, both
because they are not stable public contracts and because time-ordered identifiers on a
public price page let an observer estimate submission volume, which is commercially
sensitive while coverage is thin.

Money is always an object, never a bare number:

```json
{ "amount_minor": 4590, "currency": "TRY" }
```

Every price-bearing response carries observation provenance:

```json
{
  "price": { "amount_minor": 4590, "currency": "TRY" },
  "observed_at": "2026-08-14T09:12:00Z",
  "staleness_days": 2,
  "confidence": 0.87,
  "price_kind": "regular",
  "source_kind": "receipt_line"
}
```

There is no endpoint that returns a price without its age. A read surface that hides
staleness is lying during exactly the volatile periods that matter most.

## 11. Rate limiting

Redis-backed, per user and per IP, returning `429` with `Retry-After`. Tighter limits on
`otp/request`, `submissions`, and `review/tasks`, since those are the abuse surfaces:
OTP for cost, submissions for spam, review for point farming.

## 12. What the contract does not carry

The API is the boundary of the system, not a window into it. Extraction versions, integrity
signal scores, reviewer identities, trust weights and honeypot status are internal and
never serialised to a contributor client. Exposing them is an invitation to game them.
