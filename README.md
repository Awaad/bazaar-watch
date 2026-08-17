# Bazaar Watch

A grocery price dataset for Northern Cyprus, and the system that produces it.

Prices for identical goods differ substantially between shops on the same street, and the
ordering is conditional on category rather than fixed. No public source captures any of it.
The dataset is the product; the applications are how it is collected and how it is read.

## Status

Pre-implementation. The design is complete and accepted; no code yet.

## Documentation

Read in order. `docs/00-overview.md` first.

| Document | Contents |
|---|---|
| [00-overview](docs/00-overview.md) | Scope, principles, glossary, phases |
| [01-architecture](docs/01-architecture.md) | Module map, boundaries, ingestion flow |
| [02-stack](docs/02-stack.md) | Technology choices and rejected alternatives |
| [03-data-model](docs/03-data-model.md) | Schema, conventions, state machines |
| [04-api-contracts](docs/04-api-contracts.md) | Contract generation, auth, errors, idempotency |
| [05-ingestion](docs/05-ingestion.md) | Capture to observation |
| [06-catalog-lexicon](docs/06-catalog-lexicon.md) | Product identity, taxonomy, resolution |
| [07-integrity-trust](docs/07-integrity-trust.md) | Signals, review tiers, trust |
| [08-index-methodology](docs/08-index-methodology.md) | Index construction, governance, limitations |
| [09-contribution-economy](docs/09-contribution-economy.md) | Ledger, bounties, anti-farming |
| [10-geo-registry](docs/10-geo-registry.md) | POI discovery, verification, access scoping |
| [11-i18n-localization](docs/11-i18n-localization.md) | Locales, Turkish text handling, RTL |
| [12-security-compliance](docs/12-security-compliance.md) | PII, erasure, key management |
| [13-infra-devops](docs/13-infra-devops.md) | Environments, CI/CD, backups, runbooks |
| [14-observability-analytics](docs/14-observability-analytics.md) | System and data health |
| [15-repo-structure-standards](docs/15-repo-structure-standards.md) | Layout, module laws, CI gates |
| [16-split-basket](docs/16-split-basket.md) | Reachable set, assignment, substitution |
| [17-public-surfaces-notifications](docs/17-public-surfaces-notifications.md) | Public web, notifications |

Architecture decisions are in [`docs/adr/`](docs/adr/0000-adr-index.md). All 87 records are
accepted. Changing one requires a superseding ADR, never an edit in place.


## Getting started

Requires [uv](https://docs.astral.sh/uv/), [pnpm](https://pnpm.io/) (via `corepack enable`)
and Docker. Node and Python versions are pinned in `.nvmrc` and `.python-version`.

```bash
make install    # tooling, workspace dependencies, git hooks
make check      # everything CI runs
make help       # all targets
```

Ports are deliberately non-default so nothing collides with a local install:

| Service | Port |
|---|---|
| Postgres | 55432 |
| Redis | 56379 |
| API | 58000 |
| Console | 53000 |
| Web | 53001 |

## Repository layout

```
apps/        api, worker, console, web, app
packages/    generated API clients and types, i18n
tools/       gates, geo-gen, bakeoff harnesses
config/      tuning.json and other validated data
docs/        design documents and ADRs
```

See [docs/15-repo-structure-standards.md](docs/15-repo-structure-standards.md) for the module
laws and the full CI gate list.

## Working here

- Accepted ADRs are never edited in place. Changing a decision requires a superseding record.
- Tuning constants live in `config/tuning.json`, never in code or a DDL default.
- Generated clients are committed and never hand-edited.
- `tools/gates/` guards the mistakes that produce no error and no test failure, only quietly
  wrong data. Read `tools/gates/README.md` before adding a `noqa`.
