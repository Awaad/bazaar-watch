# 01. Architecture

A modular monolith in a monorepo, with exactly one process split. Boundaries are enforced
by tooling rather than by convention, because the alternative is that they erode.
(ADR-0001)

## 1. Deployables

| Deployable | Runs | Why separate |
|---|---|---|
| `api` | FastAPI, HTTP | The request-serving surface |
| `worker` | Celery, prefork | Multi-gigabyte model dependencies, CPU-bound, batch-friendly, different scaling curve and deploy cadence |
| `beat` | Celery beat | Scheduled index runs, staleness sweeps, bounty recomputation |
| `console` | Next.js | Operator surface |
| `web` | Next.js | Public read surface |
| `app` | Expo | Contributor client |

Backing services: PostgreSQL, Redis, S3-compatible object storage.

The worker is the only split, and it is a queue consumer rather than a service. It exposes
no API, requires no message bus, and holds no synchronous contract with anything. It reads
jobs from Redis and writes results to Postgres. That is one more deployable and close to
zero conceptual complexity. (ADR-0043)

Splitting anything else would trade attention away from the problems that are actually
hard here: entity resolution on receipt text, integrity under high price dispersion, and a
defensible index methodology. Service topology is not one of them.

## 2. Capability isolation

The `api` process holds **no credential** for the originals bucket. Crops are generated in
the worker, which already has the original open during extraction, and written to a
separate bucket that the API may read.

This removes an entire class of authorization bug. The API cannot leak an original because
it cannot reach one, not because a check passed. (ADR-0063, ADR-0064)

| Process | `receipts-original` | `receipts-crop` | Postgres | Redis |
|---|---|---|---|---|
| `api` | none | read | read/write | read/write |
| `worker` | read/write | write | read/write | read/write |

Operator access to originals is mediated: the console requests a short-TTL signed URL from
an `/v1/ops/*` endpoint, which the worker mints. (ADR-0065)

## 3. Module map

```
                    indexing        search
                        |              |
      economy           |              |
         |              v              v
     integrity  -->  observations  -->  catalog  <--  lexicon
         |               |    |            |
         v               v    v            v
       ingest  ------>  geo  ...       identity
                              \
                               core
```

Dependency direction is downward only. `core` imports nothing from any domain module.

| Module | Owns | May import |
|---|---|---|
| `core` | ids, money, Turkish fold, time, tuning loader, errors | nothing domain |
| `identity` | users, trust | core |
| `geo` | chains, branches, candidates | core |
| `catalog` | products, taxonomy, brands, aliases, collections, search docs | core, identity, geo |
| `lexicon` | chain lexicon | core, identity, geo, catalog |
| `ingest` | submissions, media, receipts, lines | core, identity, geo |
| `observations` | price observations | core, geo, catalog, lexicon, ingest |
| `integrity` | signals, review tasks, responses | core, identity, ingest, observations |
| `economy` | points ledger, bounties | core, identity, integrity, observations |
| `indexing` | baskets, runs, values | core, geo, catalog, observations |
| `search` | query log, retrieval | core, catalog |

Enforced by `import-linter` in CI. A module reaches another only through its service layer,
never by importing its SQLAlchemy models. Violations fail the build.

### Orchestration

Modules never call downward across the graph. The ingestion flow crosses `ingest`,
`lexicon` and `observations`, and none of them may import the next, so the sequencing lives
in a thin **workflow layer** that sits above every module and owns transaction boundaries.

Celery tasks and API route handlers are the only members of that layer. They compose module
services and hold no domain logic of their own. `import-linter` treats it as a separate top
layer permitted to import any module, while no module may import it.

## 4. What lives in `core`

Deliberately small, and deliberately the place where the silent-corruption risks live.

| Component | Reason it is centralised |
|---|---|
| `new_id()` | UUIDv7 generation. Clients never generate primary keys. (ADR-0003) |
| `Money` | Integer minor units plus currency. Prevents float from ever touching a price. (ADR-0004) |
| `turkish_fold()` | The dotted and dotless i corrupts lexicon keys silently. One implementation, used on both index and query side, never on embedding input. (ADR-0025) |
| `tuning` | Economy constants, thresholds, bounty weights, loaded from validated JSON. Retuning must not require a deploy. (ADR-0021) |
| `problem()` | RFC 9457 error construction with generated codes |

`turkish_fold` and `Money` are the two where a wrong call site produces no error and no
test failure, just quietly wrong data. Both are covered by a CI grep banning the naive
alternatives (`upper()`, `toUpperCase()`, float arithmetic on price fields).

## 5. Ingestion flow

```
app (offline queue)
  |  POST /v1/media/upload-slot
  |  PUT direct to storage
  |  POST /v1/media/{id}/confirm      -> re-encode, strip EXIF, hash, dedupe
  |  POST /v1/submissions             -> Idempotency-Key
  v
submissions [received]
  |  enqueue extract job
  v
worker: extract
  |  VLM -> lines with raw_text, interpreted_text, bbox
  |  receipts + receipt_lines written (immutable)
  |  reconciliation computed -> integrity_signals
  |  fingerprint + phash -> integrity_signals
  |  crops generated for low-confidence regions -> receipts-crop
  v
submissions [extracted]
  |
  v
resolve: for each item line
  |  key = sku_text or turkish_fold(raw_text)
  |  lexicon hit  -> price_observation with product_id
  |  lexicon miss -> price_observation with product_id NULL
  |                  + T1 review task, priority = blocked observation count
  v
observations [pending]
  |
  |  peer review (T1/T2) -> provisional
  |  operator adjudication -> accepted | flagged
  v
observations [accepted]
  |
  +--> points ledger entry (or compensating reversal)
  +--> eligible for index runs
```

Two things worth noting about this flow.

Resolution is retroactive. When a lexicon entry is created, a job repoints every existing
observation carrying that key. The first receipt from a chain is fully manual; the
fiftieth is nearly automatic.

Nothing in this flow deletes or edits a raw fact. A better extraction model produces a new
run against the stored original, with a new `extraction_version`, leaving the previous
lines in place. (ADR-0006, ADR-0069)

## 6. Synchronous versus asynchronous

| Synchronous | Asynchronous |
|---|---|
| Auth, reads, search, submission creation, review answer capture | Extraction, crop generation, embedding, lexicon repointing, index runs, staleness sweeps, bounty recomputation, notifications |

The rule: anything touching a model, an image, or a full-table pass is a job. A submission
returns as soon as it is durably recorded, because the app is often on a poor connection
and a long request is a failed request.

All jobs are idempotent and keyed. A retried extraction produces the same
`extraction_version` output or a new run, never a partial duplicate.

## 7. Where the invariants live

Most invariants are database constraints, which is where they belong. Three are not
expressible there and therefore need direct test coverage, because a failure would be
silent.

| Invariant | Location | Failure if broken |
|---|---|---|
| A reviewer never sees a task tracing to their own submission or to a submitter they share history with (ADR-0048) | `integrity` service, task assignment | Collusion, and validation becomes theatre |
| No more than one line from a given receipt goes to the same reviewer (ADR-0059) | `integrity` service, task assignment | Basket reconstruction, a privacy leak |
| No automated process writes a lexicon entry, a merge, or a branch verification (ADR-0011) | `lexicon`, `catalog`, `geo` services | Catalog degradation with no audit trail |

## 8. Failure modes

| Failure | Behaviour | Rationale |
|---|---|---|
| Extraction model unavailable | Submission stays `received`, job retries with backoff | The original is already durable; nothing is lost |
| Extraction returns no bounding boxes | Lines stored, T2 crop review unavailable for that receipt, T1 unaffected | Text extraction is still valuable; review degrades rather than fails |
| Reconciliation residual non-zero | Receipt flagged, lines still stored, targeted T2 tasks created on candidate lines | A residual is a pointer, not a rejection (ADR-0058) |
| Duplicate fingerprint or phash | Receipt marked `duplicate`, observations not created, no points awarded | Nothing deleted; the submission remains as evidence |
| Branch unverified | Submission accepted, observations created but excluded from indices and comparison | Access-scoped comparison makes a mis-pinned branch actively harmful (ADR-0023) |
| Object storage unreachable | Upload slot requests fail fast with `503`; the app queue retries | Better than accepting a submission whose media never arrived |
| Redis unreachable | API serves reads; writes that enqueue jobs fail with `503` | Rate limiting and queueing both depend on it |
| Embedding model unavailable | Search falls back to trigram only, degraded cross-lingual recall, logged | Partial search beats no search |
| Postgres unreachable | Full outage | Single datastore is a deliberate trade (ADR-0002) |

## 9. Environments

`local` (Docker Compose, fake extraction and SMS providers), `staging` (full stack, real
providers, synthetic contributors), `production`.

Every external provider sits behind an interface with a fake implementation. Extraction,
SMS, object storage and embeddings can all run offline, which is what makes the test suite
fast and deterministic and what lets a parallel client workstream develop against a mock
server without any provider credentials. (ADR-0042)
