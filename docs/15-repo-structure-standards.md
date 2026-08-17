# 15. Repository Structure and Standards

One monorepo. Boundaries are enforced by tooling, because boundaries maintained by discipline
erode, and this repository will be worked on by parallel agent workstreams where drift is the
primary risk. (ADR-0042)

## 1. Layout

```
/apps
  api/              FastAPI. Modules per 01-architecture
    app/
      core/         ids, money, turkish_fold, tuning, errors. Imports no domain module
      modules/
        identity/   models.py service.py schemas.py router.py
        geo/
        catalog/
        lexicon/
        ingest/
        observations/
        integrity/
        economy/
        indexing/
        search/
      workflows/    Route handlers and Celery tasks. The only layer that may import any module
      migrations/   Alembic
  worker/           Celery app, provider implementations, fakes
  console/          Next.js operator surface
  web/              Next.js public surface
  app/              Expo contributor client
/packages
  api-client-ts/    GENERATED. Never edited
  api-types/        GENERATED. Enums, constants, error codes
  i18n/             Locale files, parity-checked
/infra
  docker/
    postgres/       Postgres 18 image: PostGIS, pgvector, initdb bootstrap
/tools
  geo-gen/          Overture Places to branch candidates
  bakeoff/          Extraction and embedding evaluation harnesses
/config
  tuning.json       Validated. Deployed independently of code
  poi_roles.json    Provider category to grocery role
/docs
  *.md
  adr/
docker-compose.yml  Root, because `docker compose` looks here by default
```

### Where infrastructure lives

`infra/` holds what is not any single application's concern: backing-service
images, reverse proxy configuration, compose overrides, backup and restore
scripts, deployment configuration.

**An application's Dockerfile lives with the application**, at
`apps/api/Dockerfile`, not in `infra/`. How the API is built is part of the API,
and the Dockerfile needs to sit next to the source it copies. Collecting every
Dockerfile in `infra/` would mean build contexts spanning the whole repository
and coupling that is no longer visible from either end.

`tools/` is developer tooling that runs on a developer's machine: gates,
generators, evaluation harnesses. A service image is not that.

Python with `uv`. TypeScript with `pnpm` workspaces.

## 2. Module laws

Non-negotiable, all machine-checked.

1. **A module owns its tables.** No other module writes them, and no other module imports its
   SQLAlchemy models.
2. **Cross-module access goes through the service layer.** `from modules.catalog.service import
   resolve_product` is legal. `from modules.catalog.models import Product` from outside
   `catalog` is not.
3. **Dependency direction is downward only**, per the map in `01-architecture.md`. No cycles.
4. **`core` imports no domain module.** Ever.
5. **Modules never orchestrate each other.** Sequencing that crosses modules lives in
   `workflows/`, which may import any module and which no module may import. It owns transaction
   boundaries and holds no domain logic.
6. **Every module has a `service.py`.** If a module has no service surface, it should not be a
   module.

Enforced by `import-linter` with the layer definition committed alongside the code. A violation
fails the build rather than producing a review comment.

## 3. Generated code

`packages/api-client-ts` and `packages/api-types` are generated and committed.

Committed so that a diff is visible in review and CI can fail on staleness. Never hand-edited: a
manual fix to generated code survives until the next regeneration and then vanishes, usually
silently and usually at the worst moment.

`openapi.json` is emitted from the FastAPI app and committed. It is never authored by hand. A
hand-maintained specification eventually lies about the implementation, and both clients trust it.

## 4. CI gates

| Gate | Fails when |
|---|---|
| `ruff` | Lint or format violation |
| `mypy --strict` | Type error |
| `import-linter` | A module boundary or dependency direction is violated |
| `openapi-fresh` | Regenerating the spec produces a diff |
| `contract-diff` | A breaking change against the merge base without a version bump |
| `client-fresh` | Regenerating clients produces a diff |
| `enum-parity` | A `CHECK` constraint and its `StrEnum` disagree |
| `no-handwritten-calls` | `fetch(` or `axios(` targeting an API path outside the generated client |
| `no-naive-casing` | `upper()`, `toUpperCase()` or `casefold()` on a text path |
| `no-float-money` | Float arithmetic on a price field |
| `no-literal-strings` | A user-visible literal in UI code |
| `no-server-formatting` | A response field carrying a pre-formatted number, currency or date |
| `branch-kind-predicate` | An index or comparison query over `price_observations` joined to `branches` without a `branch_kind` predicate |
| `observation-status-predicate` | An aggregate over `price_observations` without a status predicate |
| `i18n-parity` | A locale file missing keys present in another |
| `taxonomy-i18n-complete` | A taxonomy version marked active with incomplete `name_i18n` |
| `updated-at-triggers` | A table with `updated_at` and no trigger |
| `privacy-invariant-tests` | The three adversarial tests are absent or skipped |
| `pytest` | Any test failure. Testcontainers Postgres, never SQLite |
| `schemathesis` | Implementation diverges from the specification |

Seven of these exist because the corresponding mistake produces **no error and no test failure**,
just quietly wrong data discovered weeks later: naive casing, float money, server-side
formatting, missing `updated_at` triggers, hand-written API calls, a missing `branch_kind`
predicate (which contaminates a physical-market figure with online pricing, ADR-0045), and a
missing status predicate (which double-counts superseded observations after reprocessing,
ADR-0082).

`privacy-invariant-tests` is a gate rather than a convention because those three invariants
cannot be database constraints and a skipped test would leave them unguarded.

## 5. Testing

**Real Postgres via testcontainers.** PostGIS, pgvector, `ltree`, partial indexes, `CHECK`
constraints and `NUMERIC` semantics each carry a correctness invariant here. SQLite would
silently misrepresent every one.

**Providers are faked, never mocked ad hoc.** Extraction, embedding, SMS and storage each have a
fake implementation living beside the real one and satisfying the same interface. A test that
patches a provider inline is testing the patch.

**Three adversarial tests are mandatory**, per `12-security-compliance.md` section 7: reviewer
independence, one line per receipt per reviewer, and ownership checks on submission detail. They
live separately from feature tests and may not be skipped.

**Migrations are tested**, forward and backward, against a database containing representative
data.

## 6. Commits and pull requests

Conventional commits, scoped by module: `feat(lexicon):`, `fix(ingest):`, `docs(adr):`.

A pull request that changes a decision recorded in an ADR must include the superseding ADR. ADRs
are never edited in place once Accepted; a new numbered record references the old one.

A pull request touching `03-data-model.md` must include the corresponding Alembic migration. The
document and the schema drifting apart is how the schema stops being trustworthy.

A pull request adding an endpoint must include the regenerated spec and clients in the same
commit, so the diff shows what clients will see.

## 7. Documentation

Documents are numbered and read in order. `docs/adr/0000-adr-index.md` is the spine and lists
every record with its decision in one line.

An ADR is Accepted only when its revisit trigger is a falsifiable condition rather than a
feeling. Records blocked on an open question stay Proposed and name what blocks them, so an
unanswered question is visible rather than quietly assumed away.

Cross-references use ADR numbers, never prose descriptions, so a reference stays valid when a
decision is superseded.

## 8. Naming

| Context | Convention |
|---|---|
| Python | `snake_case`, modules singular, services `verb_noun` |
| SQL | `snake_case`, tables plural, columns singular, `_id` on references |
| TypeScript | `camelCase` values, `PascalCase` types |
| API paths | plural nouns, kebab-case where multiword |
| Slugs | lowercase, hyphenated, ASCII-folded from Turkish |
| Reason codes | `subject.action`, e.g. `submission.confirmed` |
| Audit actions | `subject.verb`, e.g. `lexicon.decide` |

Slugs are ASCII-folded so a URL is typeable on any keyboard. The fold used for slugs is the same
`turkish_fold` used for lexicon keys, which keeps one implementation rather than two that drift.
