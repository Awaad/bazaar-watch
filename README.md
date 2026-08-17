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
