# 13. Infrastructure and Operations

## 1. Environments

| Environment | Purpose |
|---|---|
| `local` | Docker Compose. Fake extraction, SMS, storage and embedding providers. No credentials required |
| `staging` | Full stack, real providers, synthetic contributors, separate buckets and keys |
| `production` | |

Every external provider sits behind an interface with a fake implementation. This is what keeps
the test suite fast and deterministic, and what lets a parallel client workstream develop
against a generated mock server with no provider credentials at all. (ADR-0042)

Staging never shares a bucket, a database or a key store with production. A staging job that
reprocesses the corpus must be incapable of touching production originals.

## 2. Topology

Single VPS to start, Hetzner, EU. Latency to Cyprus is good and object storage sits on the same
network.

```
Caddy (TLS)
  |-- api        (uvicorn, N replicas)
  |-- console    (Next.js)
  |-- web        (Next.js)
  |-- worker     (Celery, prefork)
  |-- beat       (Celery beat, exactly one)
  |-- postgres   (18 + postgis + pgvector + pg_trgm + ltree + pgcrypto)
  +-- redis
```

Docker Compose rather than Kubernetes. Six deployables and one engineer do not produce the
problems Kubernetes solves, and they do produce the operational surface it costs. Revisit when
horizontal scaling is an actual constraint rather than an anticipated one.

`beat` must run as exactly one instance. Two schedulers produce duplicate index runs, which are
prevented by the uniqueness on `index_runs` but would still waste a lot of compute.

## 3. Migrations

Alembic owns all DDL, without exception. No table is created by application code, no column is
added by hand.

Deploy order is migrate, then release. Every migration must be safe against the previous
application version, since the two overlap during rollout.

Rules:

- Additive first. Add a column nullable, backfill in a job, add the constraint in a later
  migration.
- No blocking operations on `price_observations` or `receipt_lines`, which are the largest and
  most insert-heavy tables. Indexes are created `CONCURRENTLY`.
- Every migration has a tested downgrade or an explicit, documented statement that it is
  irreversible.
- The migration that pins the embedding vector dimension also creates the HNSW index, which
  cannot exist on an unpinned `VECTOR` column. Until then, search is not runnable. (ADR-0024)

## 4. Storage

Two buckets with genuinely different policies, not one bucket with per-object ACLs. Bucket-level
policy is much harder to misconfigure. (ADR-0063)

| Bucket | Policy |
|---|---|
| `receipts-original` | Never public. No contributor URL ever. Object lock. Versioned. Replicated. Written by worker only |
| `receipts-crop` | Never public. Served through the API for per-request authorization and audit. Written by worker only |

Credentials are scoped per process. The API key has no access to `receipts-original` at all,
which is the protection that actually matters, since server-side encryption decrypts
transparently for any valid key. (ADR-0066)

Lifecycle rules are blocked on the retention decision.

## 5. Backups

Three distinct assets with three distinct rules. The third is the one that will be got wrong.

**Postgres.** Nightly base backup plus continuous WAL archiving to a different provider than the
primary host. Restore is tested quarterly against a scratch instance, because an untested backup
is a hypothesis.

**Object storage.** Originals are the reprocessing corpus, and the entire
improve-the-model-and-reprocess strategy depends on them surviving. Object storage is durable
but not backed up, and durability does not protect against a bug or a compromised key deleting
things. Versioning plus object lock plus cross-provider replication. Cross-provider rather than
cross-region because the corpus is irreplaceable, small, and account-level loss is a real failure
mode. (ADR-0069)

**Key store.** Backed up, and **backup retention must be shorter than the erasure SLA.** If KEK
backups outlive a shred, nothing was shredded, no error is raised, and the failure is invisible.
This is the single most likely way the erasure guarantee gets silently broken, and it will happen
because someone applies sensible backup practice uniformly. (ADR-0072)

## 6. CI/CD

| Stage | Contents |
|---|---|
| Lint | ruff, mypy strict, ESLint, TypeScript strict |
| Boundaries | import-linter against the module map in `01-architecture.md` |
| Custom gates | naive casing, float on price fields, hand-written API calls, literal UI strings, server-side formatting, updated_at trigger coverage, enum parity, branch_kind predicate, observation status predicate |
| Contract | `openapi-fresh`, `contract-diff` against the merge base, `client-fresh` |
| Test | pytest with testcontainers Postgres, Schemathesis against the running API |
| Build | Images tagged by commit |
| Deploy | Migrate, then rolling release |

Testing runs against real Postgres with all extensions, never SQLite. PostGIS, pgvector, `ltree`,
partial indexes, `CHECK` constraints and `NUMERIC` semantics each carry a correctness invariant
here, and SQLite would silently misrepresent every one.

The three privacy invariants in `12-security-compliance.md` section 7 have dedicated adversarial
tests, separate from feature tests, and those tests are not allowed to be skipped.

## 7. Configuration and secrets

Environment-injected at deploy. Never committed.

`tuning.json` is **not** configuration and does not live in environment variables. It is
validated data, deployed independently of code, holding economy constants, thresholds, quorum
sizes and bounty weights. Retuning must never require a deploy. (ADR-0021)

Provider selection (extraction, embedding, SMS, storage) is configuration. Provider
implementations are code behind interfaces.

## 8. Scheduled work

| Job | Cadence | Purpose |
|---|---|---|
| Staleness sweep | Daily | Age cells, generate `stale_cell` bounties |
| Coverage sweep | Daily | Detect empty basket cells, generate `empty_cell` bounties |
| Review lease reclaim | Frequent | Return abandoned tasks to the queue |
| Trust recomputation | Daily | Recompute `contributor_trust` from adjudications |
| Honeypot refresh | Weekly | Rotate the honeypot pool from newly adjudicated tasks, so regular reviewers do not learn to recognise them (ADR-0061) |
| Orphan media sweep | Daily | Reclaim objects whose `media_objects` row was never confirmed (ADR-0070) |
| Index run | Per index cycle | Compute and publish, with methodology and taxonomy version recorded |
| Search doc rebuild | On catalog change plus nightly reconciliation | Keep `product_search_docs` current |
| Backup verification | Weekly | Confirm the last backup is restorable |
| Key store retention check | Quarterly | Confirm KEK backup retention is still inside the erasure SLA |

## 9. Runbooks

| Situation | Response |
|---|---|
| Extraction provider outage | Submissions accumulate at `received`. No action required; drain on recovery. Alert if depth exceeds threshold |
| Reprocessing backfill | Open new `extraction_runs` in batches; verify supersession moved prior observations; never delete |
| Erasure request | Delete Tier C, shred subject KEK, repoint Tier B to the tombstone, increment `erasure_counters`, record in `audit_log` |
| Leaked storage credential | Rotate immediately, audit access logs, assess exposure via `media_objects.subject_user_id` |
| Bad lexicon entry discovered | Supersede the entry, reprocess affected observations. Never edit raw facts |
| Index figure found wrong after publication | Issue an erratum as a new figure. Never restate a published value (ADR-0079) |
| Postgres restore | From base plus WAL to a scratch instance first, verify, then promote |

## 10. Capacity

Small by any normal standard. A few thousand products, tens of branches, thousands of receipts
per month at maturity, a handful of contributors concurrently.

The one component with a non-trivial resource profile is the worker, because model inference is
CPU-bound and memory-hungry. It scales independently, which is the whole reason it is a separate
deployable. (ADR-0043)

If capacity ever becomes a genuine constraint rather than an anticipated one, the first move is
more worker replicas, not a different architecture.
