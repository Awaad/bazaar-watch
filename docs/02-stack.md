# 02. Stack

Choices, and what was rejected. Exact versions live in `uv.lock` and `pnpm-lock.yaml`; this
document records major versions and the reasoning, which is the part that goes stale
slowly.

## 1. Backend

| Component | Choice | Reasoning |
|---|---|---|
| Language | Python 3.13+ | The hard work (extraction, embeddings, entity resolution, index computation) is all in the Python ecosystem. Splitting languages to avoid it would mean an RPC hop for the core of the product. |
| Framework | FastAPI | OpenAPI is emitted from the implementation rather than maintained beside it, which is the mechanism the whole contract discipline rests on (ADR-0042) |
| Validation | Pydantic v2 | Single definition flowing to OpenAPI and then to generated TypeScript |
| ORM | SQLAlchemy 2.0 | Explicit, typed, and does not fight raw SQL where the index computation needs it |
| Migrations | Alembic | Owns all DDL, no exceptions |
| Jobs | Celery + Redis | Prefork suits CPU-bound model inference naturally; mature retry, scheduling and visibility. An asyncio-native queue would have needed executor gymnastics for exactly the workload that matters most. |
| Cache, locks, rate limits | Redis | Day-one infrastructure regardless of the queue (ADR-0005) |
| Server | Uvicorn behind Caddy | |

**Rejected:** NestJS or Go for the API. Both are fine, and either would have put a network
boundary between the API and the model work. Consistency with the existing Python
codebases in this style is the stronger argument.

**Deferred:** transactional outbox and a domain event bus. Redis is present and the queue
is used, but there are no cross-module async consumers yet. Keep the seam, skip the
machinery. (ADR-0005)

## 2. Data

| Component | Choice | Reasoning |
|---|---|---|
| Database | PostgreSQL 18 | Native `uuidv7()`, so DB-side defaults get insert locality too (ADR-0003) |
| Geospatial | PostGIS | Access-scoped comparison makes reachability a filter on every basket read, not a map decoration (ADR-0035) |
| Vectors | pgvector, HNSW | Cross-lingual retrieval without a second datastore (ADR-0024) |
| Fuzzy text | pg_trgm, GIN | Brands, near-literal matches, SKUs |
| Hierarchy | ltree | Category tree with efficient subtree queries |
| Object storage | S3 API via boto3 | Provider is configuration. Hetzner Object Storage by default; R2 if egress becomes material (ADR-0067) |

**Rejected:** Elasticsearch. The cross-lingual problem is real (`Käse` to `peynir` has zero
character overlap and trigram cannot bridge it), but `pgvector` plus `pg_trgm` fused by
reciprocal rank fusion solves it inside the existing database. A second stateful service to
run, back up and keep in sync is a poor trade at a catalog of a few thousand products.
Revisit on measured recall failure or index build time exceeding the maintenance window.

**Rejected:** self-hosted MinIO. Operational surface bought for nothing.

## 3. Machine learning

| Component | Choice | Reasoning |
|---|---|---|
| Receipt extraction | Undecided, behind `ExtractionProvider` | Per-line bounding boxes are a hard selection criterion, because cropped review is impossible without spatial anchors (ADR-0013, ADR-0057) |
| Embeddings | Undecided, behind `EmbeddingProvider` | Multilingual, self-hostable. Candidates evaluated against a hand-built set weighted toward zero-overlap cross-lingual pairs and local brands. Vector dimension is deliberately unpinned in the schema until the choice is made, since candidates differ (768 and 1024 are both common) and HNSW requires a fixed dimension |
| Serving | In the Celery worker | Not in the API container. Multi-gigabyte dependency trees, slow cold starts, wrong scaling axis (ADR-0043) |

Both providers have fake implementations for local and test runs. Both record a version
string on every artefact they produce, so the entire corpus can be reprocessed when a
model improves. That reprocessing capability is why originals must be backed up.
(ADR-0069)

Generative extraction is treated as untrusted input. A model misreading `45.90` as `46.90`
reports high confidence, because it is generating plausible text rather than recognising
glyphs. Defences are arithmetic reconciliation, dual-extractor disagreement on price
fields, and targeted human review. (ADR-0014, ADR-0058)

## 4. Clients

| Component | Choice | Reasoning |
|---|---|---|
| Contributor app | Expo, React Native | One codebase, mature camera and permissions handling |
| Offline queue | expo-sqlite | Durable across app restarts. AsyncStorage is not a queue. |
| Console | Next.js, App Router | Operator surface |
| Public web | Next.js, App Router | Server rendering for local search visibility |
| Data fetching | TanStack Query over the generated client | Retry, caching, and offline mutation semantics |
| TypeScript | 7.x for `tsc`, 6.0 aliased for tooling | See below |
| i18n | i18next with ICU | Locales TR, EN, RU, DE; Arabic RTL structurally supported from the first commit (ADR-0026) |
| Maps | MapLibre GL | Tiles are swappable and chosen on cost, unlike POI data (ADR-0044) |

Console and public web are separate Next.js applications. Different audiences, different
auth, different deploy cadence, and the separation makes an operator surface leaking to
the public web structurally harder.

### TypeScript 7 and the programmatic API gap

TypeScript 7.0 is the Go-native compiler and is roughly an order of magnitude faster on
type-checking, which matters for a monorepo with three TypeScript workspaces.

It ships without a stable programmatic API, which arrives in 7.1. Tools that import the compiler
directly cannot run on it: typescript-eslint, ts-jest, ts-morph and custom AST transformers. A
TypeScript 7 support request against typescript-eslint was closed as not planned, because the fix
sits on the compiler side. Force-installing takes ESLint down entirely.

The supported arrangement is to run both, wired through npm aliases because typescript-eslint
resolves `typescript` through peer dependencies:

- `typescript` aliased to `@typescript/typescript6`, which re-exports the 6.0 API and provides
  `tsc6`, so ESLint and any other API consumer keeps working
- TypeScript 7 providing `tsc` for type-checking and emit

This is a package.json arrangement only. `tsconfig.base.json` is unaffected: TypeScript 7 turns
6.0 deprecations into hard errors and makes `strict` and `esnext` the defaults, and every option
we set is explicit rather than inherited.

Revisit when 7.1 ships with the stable API, at which point the alias can be removed. Until then
this is a two-package arrangement, not a version bump, and it is verified empirically when the
first TypeScript workspace arrives rather than assumed here.

Arabic is untranslated at launch but layout-ready. Logical properties (`margin-inline`,
`padding-inline`) from the first commit cost nothing; retrofitting RTL across a built UI is
expensive. The operator console is LTR-only by decision, since moderators work in Turkish
or English and dense bidirectional review tables are the hardest RTL case there is.

## 5. Contract generation

| Component | Choice |
|---|---|
| Spec | `openapi.json`, emitted from FastAPI, committed, diffed in CI |
| TS types | `openapi-typescript` |
| TS client | `openapi-fetch` |
| Mock server | Prism, from the committed spec |
| Contract tests | Schemathesis against the running API |

This is the machinery that makes parallel workstreams safe. Details and CI gates are in
`04-api-contracts.md`.

## 6. Quality gates

| Tool | Enforces |
|---|---|
| ruff | Lint and format |
| mypy, strict | Types |
| import-linter | Module boundaries from `01-architecture.md` |
| pytest + testcontainers | Real Postgres with all four extensions, never SQLite |
| Schemathesis | Spec matches implementation |
| TypeScript strict, ESLint | Client correctness |
| Custom grep gates | Banned `upper()` and `toUpperCase()` on Turkish text; banned float arithmetic on price fields; banned hand-written API calls; banned literal UI strings |

The grep gates exist because those four mistakes produce no error and no test failure. They
produce quietly wrong data, discovered weeks later.

Testing against real Postgres is not negotiable. PostGIS, pgvector, `ltree`, partial
indexes, `CHECK` constraints and `NUMERIC` semantics are all things SQLite would silently
misrepresent, and every one of them carries a correctness invariant here.

## 7. Repository

```
/apps
  api/            FastAPI, modules per 01-architecture
  worker/         Celery tasks, providers
  console/        Next.js operator surface
  web/            Next.js public surface
  app/            Expo contributor client
/packages
  api-client-ts/  generated, never edited
  api-types/      generated enums, constants, error codes
  i18n/           locale files, parity-checked
/tools
  geo-gen/        Overture Places to branch candidates
  bakeoff/        extraction and embedding evaluation harnesses
/docs
  *.md, adr/
```

Python dependencies with `uv`, TypeScript with `pnpm` workspaces.

`generated/` directories are committed so that a diff is visible in review and CI can fail
on staleness, and are never hand-edited.

## 8. Infrastructure

| Component | Choice | Reasoning |
|---|---|---|
| Hosting | EU VPS, Hetzner | Latency to Cyprus, cost, and object storage on the same network |
| Orchestration | Docker Compose behind Caddy | Kubernetes for one engineer and six deployables is overhead without benefit. Revisit when horizontal scaling is an actual constraint rather than an anticipated one. |
| CI | GitHub Actions | |
| Logging | structlog, JSON | |
| Errors | Sentry | |
| Tracing | OpenTelemetry | |
| Secrets | Environment, injected at deploy | |

Object storage credentials are scoped per process. The API key has no access to the
originals bucket at all, which is the protection that actually matters, since server-side
encryption decrypts transparently for any valid key. (ADR-0066)

## 9. Open selections

| Selection | Blocked on |
|---|---|
| Extraction provider | Bake-off across chains and POS vendors, scored on line count, description accuracy, price exactness, reconciliation and bounding-box quality |
| Embedding model | Hand-built evaluation set, recall@10, weighted to zero-overlap cross-lingual pairs and local brands |
| Object storage retention | Legal review on receipt image retention |
| Replication target | Cross-region within one provider covers most failure modes; cross-provider covers account-level loss. The corpus is irreplaceable and small, which argues for cross-provider. |
