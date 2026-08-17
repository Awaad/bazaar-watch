# 00. Overview

Working name: **Bazaar Watch**. Region: Northern Cyprus (KKTC). Base currency: TRY.

## 1. What this is

A grocery price dataset for Northern Cyprus, and the system that produces it.

Prices for identical goods differ substantially between shops on the same street, and the
ordering is conditional rather than fixed: a chain that is cheap on household goods may be
dear on meat, and a cheap chain thirty kilometres away is worth nothing to a shopper who
cannot reach it. There is no public source for any of this. Retailers run on-premise POS
systems with no external interfaces.

The dataset is the product. The applications are how it is collected and how it is read.

## 2. What we are building

| Surface | Purpose |
|---|---|
| Backend | Ingest, extraction, normalization, integrity, index computation, API |
| Inference worker | Receipt extraction, crop generation, embedding generation |
| Contributor app (Expo) | Capture receipts and shelf prices, offline queue, review tasks, personal history |
| Operator console (Next.js) | Lexicon resolution, catalog curation, branch verification, adjudication |
| Public web (Next.js) | Price lookup, published index, SEO surface |

Three clients over one versioned contract. Console and public web are separate applications rather
than one with role-gated routes, so an operator surface cannot leak to the public through a routing
mistake (ADR-0027).

## 3. Principles

These govern every decision downstream. Where a later document appears to conflict with
one of these, the principle wins and the document is wrong.

**Raw facts are immutable.** What a receipt said is recorded permanently and never edited.
Interpretation is a separate, versioned, revisable layer. A catalog mistake is repaired by
reprocessing, not by data loss. (ADR-0006)

**Identity is curated.** A canonical product is defined by a human. Barcodes, receipt
strings and scraped names are attributes and evidence, never identity. (ADR-0007)

**The model suggests, the human decides.** No automated process writes a product mapping,
a merge, or a branch verification. (ADR-0011)

**Nothing is deleted.** Duplicates, fabrications and errors are marked, not removed.
Points are reversed by compensating entries. Merges write redirects. (ADR-0019, ADR-0033)

The one exception is erasure, which is a legal right and not negotiable. It is honoured by
severing identity rather than destroying facts: the contributor reference is repointed to a
single shared tombstone, observations and ledger entries survive, and media is rendered
permanently unreadable by destroying its subject key. The tombstone is shared rather than a
per-user pseudonym, because a unique identifier would keep an erased contributor's
submissions mutually linkable and therefore still personal data (ADR-0084). Crypto shredding is used because backups and immutable
replicas exist by mandate (ADR-0069) and ordinary deletion cannot reach them. (ADR-0071)

**Safety is structural, not procedural.** Where a guarantee can be achieved by making the
dangerous thing absent rather than by checking for it, do that. The review tiers hold no
PII because none is present, not because it was redacted. The API cannot leak originals
because it holds no credential for them. (ADR-0057, ADR-0064)

**Contracts are generated.** The API specification is emitted from the implementation and
clients are generated from the specification. Hand-written API surface is a CI failure.
(ADR-0042)

**Published figures must be defensible.** Any number we publish carries its methodology
version, its coverage, and its staleness. A figure that cannot survive a journalist asking
how it was calculated does not ship. (ADR-0029)

## 4. Scope

### In scope

Receipt and shelf price capture; receipt extraction and normalization; a curated product
catalog and taxonomy; branch registry with human verification; integrity and trust
scoring; tiered community review; a contribution economy; multilingual retrieval; per
category and per branch price indices; access-scoped basket comparison; a public read
surface.

### Out of scope

**Fulfilment and delivery.** No tables, no columns, no contributor-facing promises that
presuppose it. Revisiting requires a superseding ADR. The raw observation layer stays
complete and queryable so that an unforeseen consumer can be served later without a
schema commitment now. (ADR-0030)

**Retailer integration.** No POS integration, no supplier feeds, no negotiated data
sharing. The system assumes an adversarial or indifferent supply side.

**Payments to contributors as a platform feature.** The points ledger records value
earned. Converting points to money is an operational process outside the system until a
legal entity and a payment rail exist.

## 5. Languages

Two separate decisions that are frequently conflated. (ADR-0032)

**Interface locales**: TR, EN, RU, DE. Arabic is structurally supported from the first
commit through logical layout properties, with the catalog untranslated.

**Content language**: Turkish. Receipts, fascias and packaging are Turkish, and no
supply side exists to localise them. Cross-language retrieval is solved by dense
multilingual embeddings rather than by a translation project. (ADR-0024)

The Turkish fold (`ı İ ş ğ ç ö ü`) is a lossy normalization used for lexicon keys and
trigram matching only. It is never applied to embedding input. (ADR-0025)

## 6. Glossary

| Term | Meaning |
|---|---|
| **Chain** | A retail brand. Prices never attach to a chain. |
| **Branch** | A specific outlet. `physical` with geometry, or `online` without. Prices attach here. |
| **Submission** | One contributor act of capture. Carries media, a client idempotency key, and capture context. |
| **Receipt** | An extracted document header: branch, datetime, printed total, tax total. |
| **Receipt line** | One immutable line as printed, including discount, tax and tender lines. |
| **Observation** | One price fact: branch, product, time, amount. Produced by a receipt line, a shelf capture, or a scrape. |
| **Canonical product** | The curated identity a human defines. |
| **Lexicon entry** | A mapping from a chain-specific key to a canonical product. |
| **Raw text** | The receipt line verbatim. Immutable. Feeds the lexicon key and trigram. |
| **Interpreted text** | The same line expanded to natural language. Feeds the embedding. Versioned. |
| **Taxonomy** | The closed, curated, versioned category tree. |
| **Basket** | A fixed, weighted set of products or product groups used to compute an index. |
| **Reachable set** | The branches a given user can plausibly shop at. Comparison is scoped to it. |
| **Reconciliation residual** | Printed total minus (item lines minus discounts). Zero is healthy. KDV is an inclusive breakdown on TRNC receipts and is never an addend. |
| **Review tier** | T1 text-only lexicon mapping, T2 cropped line transcription, T3 full receipt (operator only). |

## 7. Phases

Phases describe capability order, not calendar. Workstreams run in parallel behind
generated contracts (ADR-0042), so these overlap.

**P1. Corpus.** Ingest, extraction, immutable raw layer, catalog and lexicon, operator
console, branch registry entered by hand, integrity by reconciliation and fingerprint and
perceptual hash. Contributor app capture with offline queue. Points ledger accruing.
Outcome: a growing, clean, attributed price corpus.

**P2. Community.** Tiered review, honeypots, contributor trust, bounties on cold cells,
structured store attributes. Outcome: throughput that does not depend on one person.

**P3. Retrieval.** Catalog embeddings, hybrid search, query logging, alias mining.
Outcome: the corpus becomes findable in four languages.

Embedding-based lexicon suggestion is pulled forward into P2 rather than waiting for P3.
Suggestion and search are one retrieval problem pointed in two directions (ADR-0040), and
T1 review throughput is materially worse without ranked candidates. The public search
surface still lands in P3; only the index and the suggestion path move earlier.

**P4. Intelligence.** Index methodology, per-category indices, access-scoped comparison,
split basket, public web. Outcome: published figures and a consumer surface.

The first analytical deliverable falls out of P1 at no extra cost: per-category basket
cost by branch by week, and the rank correlation between consecutive weeks. That
measurement determines which per-category indices in P4 are worth publishing at all.

## 8. External dependencies

| Dependency | Role | Status |
|---|---|---|
| Overture Places | Branch discovery, `operating_status`, `confidence` | CDLA Permissive 2.0 and Apache 2.0. Places only. Buildings and transportation are ODbL and must never enter the same derived database. (ADR-0022) |
| Extraction model | Receipt image to structured lines with bounding boxes | Provider undecided. Bounding boxes are a hard selection criterion. (ADR-0013) |
| Embedding model | Cross-lingual retrieval and lexicon suggestion | Undecided. (ADR-0024) |
| SMS provider | Phone OTP | Preload. Behind a pluggable interface. (ADR-0028) |
| Object storage | Receipt originals and crops | S3 API, provider is configuration. (ADR-0067) |
| Scraped online catalogs | Product name seed, and locationless price sources | Provenance-tagged and unverified on import. (ADR-0046, ADR-0045) |

## 9. Open questions

These are tracked in the ADR index and gate specific decisions.

1. **Extraction bake-off.** Which provider, at what text accuracy, what bounding-box
   quality, and what cost per receipt. Gates ADR-0013 and shapes the review architecture.
2. **Overture residential coverage.** Whether Places knows where supermarkets are in
   residential Girne and Lefkoşa, as distinct from the harbour district. Gates ADR-0022.
3. **Receipt item codes.** Whether local receipts print a code alongside the description.
   Determines whether the lexicon keys on `(chain_id, sku)` or `(chain_id, raw_text)`,
   which materially changes normalization throughput.
4. **Retention.** Whether raw receipt images may be retained and for how long. Gates the
   storage lifecycle policy and T3 review.
5. **Embedding model selection.** Measured against a hand-built evaluation set weighted
   toward zero-overlap cross-lingual pairs and local brands.

## 10. Document map

| Doc | Contents |
|---|---|
| `00-overview.md` | This document |
| `01-architecture.md` | Module map, boundaries, ingestion flow, failure modes |
| `02-stack.md` | Exact choices and versions |
| `03-data-model.md` | Schema, conventions, state machines |
| `04-api-contracts.md` | Conventions, auth, errors, idempotency, code generation |
| `05-ingestion.md` | Capture to observation |
| `06-catalog-lexicon.md` | Product identity, taxonomy, resolution, merges |
| `07-integrity-trust.md` | Signals, review tiers, trust, adjudication |
| `08-index-methodology.md` | Basket definition, staleness, missing data, publication |
| `09-contribution-economy.md` | Ledger, bounties, leaderboards |
| `10-geo-registry.md` | Discovery pipeline, licensing, verification |
| `11-i18n-localization.md` | Locales, ICU, Turkish text handling |
| `12-security-compliance.md` | Data protection, PII, retention, consent |
| `13-infra-devops.md` | Environments, CI/CD, storage, backups |
| `14-observability-analytics.md` | Event taxonomy, data-health SLOs |
| `15-repo-structure-standards.md` | Monorepo layout, module laws, CI gates |
| `16-split-basket.md` | Reachable set, assignment, substitution, missing items |
| `17-public-surfaces-notifications.md` | Public web, what it publishes and withholds, notifications |
| `adr/` | Architecture decision records |
