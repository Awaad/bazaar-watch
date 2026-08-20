# ADR Index

> Working name "Bazaar Watch"; replace globally once branding is decided.
> Baseline v1.0, accepted 2026-08-17. All 87 records are Accepted. 0088 was added during
> implementation, when the gate `docs/15` described turned out to be unwritable as specified. Five carry a named open
> parameter, which is a value still to be measured rather than a decision still to be made; the
> decision in each of those is settled and the parameter cannot change it.
> Changing an Accepted record requires a superseding ADR, never an edit in place.
> Timeline is deliberately not fixed; parallel agent-driven workstreams make contract discipline
> (0042) the binding constraint, not calendar.
> Region: Northern Cyprus (KKTC). Base currency: TRY.
> UI locales: TR, EN, RU, DE at launch; AR RTL-ready from day one, catalog untranslated.
> Content language: Turkish, because receipts and fascias are Turkish. See ADR-0032 for why
> these are two separate decisions and not one.

Format: Status, Context, Decision, Consequences, Alternatives considered, Revisit trigger.
Full records live in `NNNN-slug.md` beside this file. All 87 are written. The table below is a
navigation aid; the record is authoritative.
Superseding an ADR requires a new numbered ADR referencing the old one; never edit an
Accepted ADR in place. An ADR is Accepted only when its Revisit trigger is a falsifiable
condition, not a feeling.

## Foundation

| # | Title | Decision in one line | Status |
|---|---|---|---|
| 0001 | Modular monolith in a monorepo | One FastAPI deployable, module-owned tables, `import-linter` enforced boundaries; the only split is the inference worker (0043); everything else stays in-process behind enforced boundaries | Accepted |
| 0002 | PostgreSQL + PostGIS single datastore | Postgres 18 (native `uuidv7()`, so DB-side defaults get insert locality too); PostGIS is core rather than decorative because access-scoping (0035) makes geography load-bearing on every read path; Alembic owns all DDL | Accepted |
| 0003 | App-generated UUIDv7 PKs; client IDs are idempotency keys | Server-side `core/ids.py::new_id()`; clients generate an opaque `client_idempotency_key` (v4) for offline sync dedupe and never a PK; public surfaces use slugs, never UUIDs | Accepted |
| 0004 | Money as integer minor units | `amount_minor BIGINT` + `currency CHAR(3)`; TRY base; observations carry their observed currency, never a converted value; FX applied at read time with a recorded rate | Accepted |
| 0005 | Redis for cache, rate limiting, locks and job queue; domain event bus deferred | Redis is day-one infrastructure and the extraction pipeline needs a queue regardless; the transactional outbox and a domain event bus are deferred because no cross-module async consumer exists yet, keeping the seam without the machinery | Accepted |

## Data core (the part that is unfixable later)

| # | Title | Decision in one line | Status |
|---|---|---|---|
| 0006 | Observations are immutable; normalization is a separate versioned layer | `receipt_lines` and `price_observations` record what the source literally said and are never edited; product resolution is a revisable mapping, so a catalog mistake is repaired by reprocessing, not by data loss | Accepted |
| 0007 | Product identity is curated, not derived | A canonical product is defined by a human; GTIN is a one-to-many **attribute**, never the identity; private label carries `owner_chain_id` and is excluded from cross-chain comparison | Accepted |
| 0008 | Lexicon: `(chain_id, sku)` preferred, `(chain_id, normalized_raw_text)` fallback | Exact-match resolution table; every row is simultaneously a search alias and a training label; resolving a string applies retroactively to all prior observations of it | Accepted |
| 0009 | Taxonomy is a closed curated set; tags are open | Hierarchical category tree editable only by operators, versioned, with published index figures naming the taxonomy version; facets (`halal`, `imported`, `refrigerated`) are open | Accepted |
| 0010 | Variable-weight and in-store barcodes are not product identities | EAN-13 with a `2` prefix encodes weight or price, not product; detected at ingest and routed to the weight-item path; loose produce is first-class, not an afterthought | Accepted |
| 0011 | Model suggests, human decides | Lexicon suggestion ranks candidates only; it never writes a mapping; hybrid retrieval over the shared embedding index (0024, 0040) with trigram for exact and brand matches, optionally reranked; every accepted decision becomes a training label | Accepted |

## Capture and extraction

| # | Title | Decision in one line | Status |
|---|---|---|---|
| 0012 | Receipt-first by weight, not by capability | One receipt yields 20 to 40 attributed, timestamped, arithmetically checkable observations and covers produce and bakery carrying no barcode, so it gets the app UX emphasis; barcode and manual shelf capture are the same `price_observation` with a different `source_type` and are supported from day one, never retrofitted | Accepted |
| 0013 | Pluggable `ExtractionProvider`; dual output; every run versioned | VLM extraction behind an interface with at least a fake; **per-line bounding boxes are a hard selection criterion**, because cropped review (0057) is impossible without spatial anchors and purely generative extractors often omit them; one pass emits both `raw_text` verbatim (immutable, feeds the lexicon key and trigram) and `interpreted_text` expanded to natural language (feeds the embedding, since `CC KOLA 1LT PET` is not a sentence); `extraction_method` and `extraction_version` stored per receipt so the entire corpus can be reprocessed when the model improves | Accepted, parameter open |
| 0014 | Generative extraction is treated as untrusted input | A VLM misreading `45.90` as `46.90` emits no low-confidence signal; defences are arithmetic reconciliation, dual-model agreement on price fields above a threshold, and human review on mismatch | Accepted |
| 0015 | Offline-first capture; at-least-once sync | Durable client queue, client-generated idempotency key, retry with backoff, partial-upload recovery; supermarket interiors have bad signal and this is not optional | Accepted |
| 0016 | Media storage and retention | Receipt images to object storage, never the database; cropping does not replace the original, which retains date, branch and store-name evidence and remains the reprocessing corpus; see 0063 to 0070 for the storage architecture; retention window and redaction status recorded per submission | Accepted, parameter open |

## Integrity and economy

| # | Title | Decision in one line | Status |
|---|---|---|---|
| 0017 | Integrity signals: reconciliation, fingerprint, perceptual hash | Line items plus KDV must reconcile to the printed total; `(branch, receipt_datetime, total, line_count)` fingerprint catches resubmission; aHash catches recycled images | Accepted |
| 0018 | Soft enforcement, never accusation | A low integrity score reduces reward and routes to review; it never hard-blocks and never accuses; missing EXIF is neutral because clients strip it | Accepted |
| 0019 | Points are an append-only ledger | No mutable score column anywhere; balances and leaderboards are derived; clawback is a compensating negative entry referencing the original, never a delete | Accepted |
| 0020 | Reward marginal information value, not volume | Award on **acceptance**, weighted by how stale or empty the `(branch, product)` cell was; volume-based points instruct contributors to farm the nearest store, and they will | Accepted |
| 0021 | Tuning lives in data, not code | Economy constants, thresholds, and bounty weights in a validated `tuning.json`; retuning must not require a deploy | Accepted |
| 0033 | No naive global outlier rejection; robust conditional anomaly scoring | Cross-branch dispersion is genuinely enormous, so global bounds would delete real data; compare instead against the same product at the same branch over a recent window, using median and MAD, scoring on change rather than level, judging the receipt jointly; statistical deviation is one input to a review score alongside reconciliation, fingerprint, perceptual hash and contributor trust, never an authority; flagged rows are excluded from published figures, never deleted (ADR-0006 holds) | Accepted |

## Geo, search, language

| # | Title | Decision in one line | Status |
|---|---|---|---|
| 0022 | POI source: Overture **Places theme** specifically | Places carries no OSM data and no share-alike; buildings and transportation are ODbL and must never be pulled into the same derived database; optionally filter `source = Foursquare` (Apache 2.0, own terms) for a purely CDLA dataset; `operating_status` and per-record `confidence` feed branch verification directly; 639 named POIs at 100% naming vs OSM's 139 at 67.6% on the Kyrenia harbour bbox; a sampled record confirms `supermarket` exists in the taxonomy and that independents are present in Girne, so the open question is recall rather than viability | Accepted, parameter open |
| 0087 | Independents are chains of one | An independent shop such as `H.Gül Market` has no chain, but `branches.chain_id` is `NOT NULL` because the lexicon namespace is keyed on it and an independent's receipts still need their own keyspace; the answer is a chain row with a single branch, recorded explicitly so nobody later "fixes" it by making the column nullable and silently breaks resolution | Accepted |
| 0023 | Open map data seeds candidates, never branches | No price attaches to a branch lacking `verified_by_human`; `source_ref` and `geocode_confidence` recorded; closed stores, wrong pins, and cross-provider duplicates are expected | Accepted |
| 0045 | Branches may be locationless | `branch_kind` of `physical` or `online` with nullable geometry; online sellers are real price sources and appear in item lookup and history, but are excluded from access-scoped basket comparison (0035) and from per-category chain indices, because a failed online store's pricing is not evidence about the physical market | Accepted |
| 0046 | Seeded catalog rows are provenance-tagged and unverified | Products imported from scraped online catalogs carry `source` and a verification state so a scraper's spelling and category errors are never mistaken for operator-confirmed ground truth | Accepted |
| 0024 | Hybrid retrieval in Postgres (`pg_trgm` + `pgvector`); no Elasticsearch | Cross-lingual grocery search has zero character overlap in the hard cases (`Käse`/`peynir`, `гречка`/`karabuğday`), so lexical matching alone cannot work; dense multilingual embeddings handle meaning across languages while trigram and exact matching handle brands, barcodes and SKUs, fused by reciprocal rank fusion; both live in one Postgres via HNSW, so no second datastore; **revisit trigger: measured recall@k below target after reranking, or index build time exceeding the maintenance window** | Accepted, parameter open |
| 0025 | Turkish fold governs source data, not the interface | One fold function (`ı/İ/ş/ğ/ç/ö/ü`) applied identically on index and query side; locale-naive `upper()` / `toUpperCase()` banned by CI, because the dotted and dotless i will corrupt lexicon keys silently; the fold is deliberately lossy and applies to lexicon keys and trigram **only**; embedding input is the unfolded `interpreted_text` from 0013, because stripping diacritics degrades a model trained on natural text; orthogonal to ADR-0026 | Accepted |
| 0026 | Multi-locale UI from day one; no hardcoded strings | TR, EN, RU, DE at launch, AR RTL-ready from commit one via logical layout properties; ICU MessageFormat, keys from server, CI fails on literal strings and on locale-file parity gaps | Accepted |
| 0032 | Content language and UI language are separate decisions | Observations are Turkish because receipts are; the interface is not; the bridge is dense cross-lingual retrieval (0024), not a translation project, because the catalog has no supply side to localise it the way a retailer's would | Accepted |
| 0037 | Aliases are an override layer, not the mechanism | Dense retrieval (0024) handles cross-lingual matching at scale; curated aliases exist only for what embeddings cannot know, meaning TRNC-only brands, private label and regional names, which is dozens of corrections rather than thousands of translations; taxonomy translation is done because browse and filter need it, not as a search strategy | Accepted |
| 0039 | Query logs are the alias mining pipeline | Every search is logged with locale, result count, and downstream click; a zero-result query followed by a successful reformulation and a click is a labelled synonym pair, which is how large retailers build synonym dictionaries without anyone writing them; feeds the override layer and the reranker, and produces a demand-ranked backlog for human curation | Accepted |
| 0040 | One embedding index, two consumers | The vector index that lets a German find `peynir` is the same index that ranks candidates for `EMMENTAL PEYNIR 200G` from a receipt line (0011); multilingual search and lexicon suggestion are one retrieval problem pointed in two directions, which moves the embedding investment earlier rather than later | Accepted |
| 0038 | Segment collections are first-class | Dietary and national product sets (German staples, Russian staples, halal) are curated collections, not tags or baskets; different demographics want disjoint product sets and this is a differentiating surface for the expat audience, not only a translation cost | Accepted |

## Product surface and scope

| # | Title | Decision in one line | Status |
|---|---|---|---|
| 0027 | One Expo app, one Next.js operator console, one public web surface | Contributor app and console are thin clients over the same versioned API; the console is built **first** because normalization throughput, not collection, is the real bottleneck | Accepted |
| 0028 | Auth: phone OTP via pluggable `SmsProvider` | Preload as the initial implementation, interface-first so it is swappable | Accepted |
| 0029 | Index methodology is published and defensible | Fixed basket, stated weighting, explicit staleness window, explicit missing-data policy; two consumers with different needs (a single defensible figure over time for publication, an actionable split for the user) and they are never conflated; a figure that cannot survive a journalist asking how it was calculated does not ship | Accepted |
| 0034 | The index is plural: per-chain, per-branch, and per-category | A single blended basket number destroys the actionable signal, which is category-specific ("napkins here, meat there"); chain-level tendencies are real and stable but conditional on category, so the fixed-basket figure is kept for publication while per-category indices carry the user-facing value | Accepted |
| 0035 | Comparison is access-scoped; geography is load-bearing | A cheap branch outside the user's reachable set is excluded from comparison, not ranked last; reachability is a first-class filter on every basket query, which makes PostGIS core from day one rather than decorative | Accepted |
| 0036 | Split basket, not a league table, is the consumer surface | Given a list, a store-count budget and a reachability constraint, return where to buy what; deterministic optimisation over the price table with an explicit substitution and missing-item policy; explainable to a user who asks why | Accepted |
| 0030 | Fulfilment is out of scope and carries no schema commitment | Delivery is deferred with no tables, no fields, and no contributor promises that presuppose it; revisiting requires a superseding ADR that first resolves the transparency conflict with the platform's core claim | Accepted |
| 0031 | Data protection: KVKK-aligned, GDPR-grade hygiene | Receipts carry card digits, loyalty numbers, and sometimes staff names; PII redaction at ingest is mandatory; contributor consent is explicit and separable | Accepted, parameter open |

| 0041 | Strict matching by default; substitutions offered, never auto-applied | The split basket (0036) matches at canonical product level only; alternatives (different brand, different pack size with a better unit price) are surfaced as explicit opt-in suggestions, because a recommendation the user did not expect costs more trust than the saving is worth | Accepted |

## Contracts and parallel workstreams

| # | Title | Decision in one line | Status |
|---|---|---|---|
| 0042 | Contracts are generated, never hand-written | OpenAPI emitted **from** the FastAPI app so the spec cannot lie; TypeScript clients, enums and constants generated for Expo and console; hand-written API calls fail CI; contract-diff gate fails on breaking changes; mock server generated from the spec so client work precedes endpoints; `/v1` from the first commit. This is the binding safety mechanism for agent-driven parallel development, where drift is the primary risk | Accepted |
| 0043 | One split only: the inference worker | VLM extraction and embedding generation have a different resource shape, scaling curve, deploy cadence and a multi-gigabyte dependency tree, so they do not belong in the HTTP-serving container; it is a queue consumer writing to Postgres, not a service with an API, so it adds one deployable and near-zero conceptual complexity; splitting anything else for interest would trade attention away from the genuinely hard problems (entity resolution, integrity under dispersion, index methodology) | Accepted |
| 0044 | Tile rendering and POI data are separate decisions | Tile provider (MapLibre, Mapbox, Protomaps) is swappable behind an interface and chosen on cost; POI **data** is not, because commercial places APIs restrict storage and you would be renting your own branch table; 0022 is chosen for ownership, not for coverage | Accepted |

## Community contribution

| # | Title | Decision in one line | Status |
|---|---|---|---|
| 0047 | Peer review verifies extraction, not price | A reviewer was not at the shelf and cannot adjudicate whether a price was correct; they verify what the source says, which drains the lexicon gap queue and directly attacks the throughput bottleneck | Accepted |
| 0057 | Review is tiered by what it must expose | **T1 lexicon mapping** (which product is this string?) is text only, carries zero PII by construction, needs no bounding boxes, is the highest volume, and unblocks the actual bottleneck; **T2 transcription check** shows one cropped line region, making PII structurally absent rather than redacted-and-hopefully-gone; **T3 full receipt** stays operator-only. T1 and T2 therefore ship without waiting on 0031 | Accepted |
| 0058 | Route on residual, disagreement and novelty, never on self-reported confidence | A generative model reading a faded `45.90` as `46.90` reports high confidence because it is generating plausible text, so it will not flag exactly the cases that matter; reconciliation residual is the strongest free signal (a 1.00 gap ranks candidate lines by which digit flip closes it), joined by dual-extractor disagreement, unseen raw strings, and per-region blur, skew and contrast | Accepted |
| 0059 | One line per receipt per reviewer | A single crop leaks nothing, but many crops from one receipt let a reviewer reassemble the basket, and basket contents are themselves sensitive (medication, pregnancy tests, alcohol) | Accepted |
| 0060 | Closed questions, not open transcription | "Does this say 45.90 or 46.90?" is faster, comparable across reviewers and yields clean agreement statistics; free-text transcription has high variance and is hard to score | Accepted |
| 0061 | Honeypots give immediate reviewer scoring | Crops with known answers injected into the queue produce an accuracy signal at once rather than waiting for eventual corroboration, strengthening 0049 | Accepted |
| 0062 | Verified crops are the extraction fine-tune corpus | Each confirmed T2 review is an (image region, confirmed text) pair on real local receipts in real conditions, accumulating as a byproduct of the review loop; this is the correct dataset for a domain fine-tune, unlike a scraped product catalog which contains no query or image supervision | Accepted |
| 0048 | Independence, not bridging | Community Notes uses bridging-based ranking because its ground truth is contested along an ideological axis; a receipt line objectively does or does not say 45.90, so the requirement is reviewer independence from the submitter (no shared history, referral, or device fingerprint), which is cheaper and better matched to the problem | Accepted |
| 0049 | Reviewers scored on eventual agreement, never on volume | Points for reviewing produce a rubber stamp that launders bad data with a veneer of validation; reviewer weight derives from agreement with later corroboration or operator adjudication, and decays for those who approve indiscriminately; same principle as 0020 | Accepted |
| 0050 | Provisional acceptance, confirmed later | Peer review gives fast provisional status so a contributor is not left in silence for days waiting on operator review, with the ledger entry confirmed or clawed back (0019) on final adjudication | Accepted |
| 0051 | Submitter identity is never shown to reviewers | In a market this small, "someone who shops at the Esentepe branch on Tuesday evenings" can identify one person | Accepted |
| 0052 | Structured store attributes only, never free text | Fixed ordinal dimensions (produce freshness, stock breadth, queue length), recency-weighted because freshness last March says nothing about today, suppressed below a minimum sample count, and rigorously excluded from the price index so a subjective rating cannot contaminate a published inflation figure; free-text store reviews are declined for defamation exposure in a small market | Accepted |

## Location

| # | Title | Decision in one line | Status |
|---|---|---|---|
| 0053 | Point-in-time foreground location only | Capture-moment fix, no history, no background tracking; peer review targeting uses prior contributions at that branch, already in `submissions`, so deriving it from stored location would be strictly more invasive for the same result | Accepted |
| 0054 | Derive at ingest, discard the coordinate | Store "capture position was within N metres of the claimed branch" plus a confidence, never the raw point or a trace; every consuming feature needs only the derived signal, so this collapses breach exposure, retention obligation and DPIA burden at no functional cost | Accepted |
| 0055 | Location is a soft signal, never a gate | Indoor GPS commonly degrades to 50 to 100 metres and cannot separate adjacent units in a shopping centre; mock location is a developer-settings toggle on Android; it therefore joins the integrity score under 0018 and never blocks a submission | Accepted |
| 0056 | Background geofenced reminders deferred | The only feature requiring Always-permission; Apple scrutinises the request and Google Play requires a background location declaration, so the cost is app-store risk plus likely user denial; revisit once retention justifies it, with foreground and time-based nudges first | Accepted |

## Media storage

| # | Title | Decision in one line | Status |
|---|---|---|---|
| 0063 | Two buckets, not one bucket with two policies | `receipts-original` (never public, no contributor URL ever, versioned or object-locked, replicated) and `receipts-crop` (derived, PII-free by construction); bucket-level policy is far harder to misconfigure than per-object ACLs, and 0057 made safety structural rather than procedural, so the same principle applies one layer down | Accepted |
| 0064 | Crops are pre-generated in the worker; the API holds no credential for originals | The worker already has the original open during extraction, so generating crops there means the request-serving path has no access to the private bucket at all; isolation by capability rather than by check, removing an entire class of authorization bug; crops are a few KB so duplicate storage is negligible and the review queue gets faster | Accepted |
| 0065 | Proxy the small things, sign the big things | Crops served through the API for per-request authorization and a free audit trail at trivial bandwidth cost; originals via short-TTL (minutes) signed URLs to operators and the worker only, because long-lived signed URLs end up in chat logs and browser history | Accepted |
| 0066 | SSE at rest, with an honest threat model | Server-side encryption is free and goes on, but it does not defeat the realistic threat, which is a leaked credential, since the provider decrypts transparently for any valid key; what actually protects the corpus is credential scoping, rotation and bucket policy; application-level encryption is declined because it breaks server-side image processing and adds key management a solo operator should not own | Accepted |
| 0067 | S3 API, not a provider SDK | Provider becomes a config value; Hetzner Object Storage as the default given same-network transfer and latency to Cyprus, R2 if egress ever becomes material; self-hosted MinIO declined as operational surface bought for nothing | Accepted |
| 0068 | Re-encode at ingest; never store the upload verbatim | EXIF can carry GPS, so storing the file untouched would retain the precise coordinate that 0054 exists to discard, in a place nobody thinks to look; re-encoding strips EXIF, normalizes format and neutralises malformed-image parser exploits in one step | Accepted |
| 0069 | Originals are a strategic asset and must be backed up | The reprocess-when-the-model-improves strategy in 0013 depends entirely on originals surviving; object storage is durable but not backed up, and durability does not protect against a bug or a compromised key deleting things, so versioning or object lock plus replication is mandatory | Accepted |
| 0070 | Two-phase presigned upload | Request slot, PUT direct to storage, confirm; multi-megabyte uploads through the API tie up request workers and interact badly with the offline retry queue (0015); the client idempotency key from 0003 ties the phases together and a content hash at confirm dedupes offline retries for free | Accepted |

## Erasure and methodology

| # | Title | Decision in one line | Status |
|---|---|---|---|
| 0071 | Erasure by crypto shredding, scoped to three tiers | Backups and immutable replicas exist by mandate (0069) and ordinary deletion cannot reach them, so destroying a per-subject key is the only erasure mechanism compatible with never losing the corpus; **Tier A** (originals, crops, raw PII) is envelope-encrypted under a per-subject KEK and shredded; **Tier B** (observations, receipt lines, ledger) is severed to the shared tombstone of 0084 and retained in plaintext, because a shelf price is not personal data once unlinked and encrypting it would destroy the aggregate queryability that is the entire product; **Tier C** (phone, credentials, sessions) is deleted outright | Accepted |
| 0072 | Key store backup retention is shorter than the erasure SLA | If KEK backups outlive a shred, nothing was shredded; this is the loophole that ordinary sensible backup configuration creates by accident | Accepted |
| 0073 | Crops share their original's subject key | Shredding an original while its crops persist retains fragments of exactly the sensitive content; erasure consequently shrinks the extraction fine-tune corpus (0062), which is accepted and stated rather than discovered | Accepted |
| 0074 | Crypto shredding is defensible, not guaranteed | Widely accepted practice, but some supervisory authorities have questioned whether strongly encrypted data with a destroyed key is fully erased; recorded here rather than presented as settled | Accepted |
| 0084 | One shared tombstone, never a per-user pseudonym | A unique random id per erased user keeps every one of their submissions linkable to each other, reconstituting a shopping profile; that is pseudonymisation, which remains personal data and leaves the obligation intact after doing the work. All erased references point at a single well-known `deleted-contributor` row, which dissolves the linkage and actually anonymises. The lost ability to count one departed person's submissions is recovered, if wanted, by an aggregate counter carrying no identifier | Accepted |
| 0085 | Receipt-level grouping is never exposed outside the operator surface | `receipt_lines` grouped by `receipt_id` is a basket even after the contributor is severed, and a basket carries inferences about health, religion, pregnancy and alcohol use; in a market this small one submission from a rural branch at 21:47 is attributable. Public and contributor surfaces expose observations, which are individually unremarkable; baskets stay internal | Accepted |
| 0086 | Object lock is what forces crypto shredding | Versioning plus replication would permit real deletion and need no key store, but 0069 mandates lock so the corpus cannot be lost, and locked objects cannot be deleted before expiry. The decisive argument is evidentiary rather than architectural: a destroyed key is demonstrable, whereas proving every copy across every replica and version was reached is not, and erasure is an obligation that may have to be shown rather than merely performed | Accepted |
| 0075 | Two-level index: Jevons elementary, chained Laspeyres above | Jevons at the elementary level because it is transitive and the international standard, with Carli rejected for its documented upward bias; expenditure weights only exist above that level, and chaining lets the basket refresh without a discontinuity | Accepted |
| 0076 | Weights derived from observed expenditure | Receipts carry quantities, so the corpus is expenditure data and weights refresh continuously; statistical offices buy this with an annual household survey, which is their most expensive input | Accepted |
| 0077 | Class mean imputation, never carry-forward | Repeating last period's price systematically dampens the index toward zero change, which is exactly the wrong bias in a high-inflation setting; `imputed_pct` is published on every value | Accepted |
| 0078 | Two labelled currency series, never one blended number | `try_nominal` primary because TRY inflation is what a TRY-earning household experiences, `fx_deflated` secondary for the substantial foreign-currency-earning segment; neither is presented as the real one | Accepted |
| 0079 | Methodology changes are announced, parallel-run and linked | Announce before the first figure under the new method; publish both series for three cycles; publish a linking factor; sunset without deleting; **never restate a published figure**, issue an erratum instead. A taxonomy restructure counts as a methodology change | Accepted |
| 0080 | Limitations are published with the figures | Non-random self-selected sample skewed urban and toward bounty targets is the principal validity threat and does not diminish with volume; disclosed up front, because a critic will find it either way and pre-disclosure is the difference between a caveat and a scandal | Accepted |
| 0081 | Reconciliation is KDV-inclusive | TRNC receipts print prices inclusive of KDV and show tax as an informational breakdown; treating it as an addend makes every healthy receipt fail reconciliation, disabling the strongest integrity signal in the system | Accepted |
| 0082 | Extraction runs supersede, never coexist | A second extraction of the same submission marks the first superseded and moves its observations to `superseded` in one transaction; without this every reprocessed receipt double-counts and the reprocessing strategy in 0013 and 0069 is unimplementable | Accepted |
| 0083 | Operators require a second factor | They are the only role that reaches receipt originals and therefore the only role that sees PII; treating them as ordinary users with a wider role check would leave the most sensitive path the least protected, and every action they take is written to `audit_log` | Accepted |
| 0088 | Index and comparison reach branches only through named selectables | The ADR-0045 and ADR-0023 exclusions are two predicates from two records that every index query must remember, and omitting either yields a plausible number rather than an error; a published wrong figure costs an erratum under 0079, so the exclusion is carried by `index_eligible_branches()` and `public_branches()` and enforced by the `branch-scope` gate | Accepted |

## Open questions blocking Acceptance

| Blocks | Question | How it gets answered |
|---|---|---|
| 0029, 0034 | Which categories show stable chain-level ordering and which do not, and over what window? | Falls out of the seed corpus at no extra cost: per-category basket cost by branch per collection week, then rank correlation between consecutive weeks per category. This is the **first analytical deliverable of the system**, and it determines which per-category indices are worth publishing. |
| 0013 | Which extraction provider, at what accuracy and cost per receipt? | Bake-off harness: 20 receipts across as many chains and POS vendors as obtainable, hand-labelled once, scored on line count, description accuracy, price exactness, reconciliation, **and bounding-box quality**, which may narrow the candidate list sharply |
| 0022 | What is Overture's **recall** for supermarkets in residential Girne and Lefkoşa? A sampled record confirms presence; presence is not recall. | Re-run the existing coverage report on two or three residential bboxes; half a day |
| 0016, 0031 | May raw receipt images be retained, and for how long? | Local legal review; not guessable |
| 0008, 0027 | Do local receipts print an item code alongside the description? | Inspect real receipts. Determines whether the lexicon keys on the strong `(chain_id, sku)` or the weak `(chain_id, raw_text)`, which materially changes normalization throughput and therefore the console-before-app ordering in 0027. |
| 0031 | Is receipt PII redaction working end to end? | Downgraded from a blocking prerequisite by 0057: tiered review means T1 and T2 expose no PII by construction, so redaction now gates only T3 full-receipt review and general retention. Still needed, no longer on the critical path. |
| 0024, 0040 | Which multilingual embedding model, at what recall and what hosting cost? | Small eval set built by hand: ~100 query/product pairs spanning TR, EN, RU, DE, deliberately weighted to zero-overlap cases (`Käse`/`peynir`, `гречка`/`karabuğday`) and to local brands with no semantic footprint. Score recall@10 for BGE-M3 and EmbeddingGemma-300M. The local-brand failures are the ones that size the alias override layer in 0037. |
