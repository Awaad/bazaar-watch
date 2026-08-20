# 03. Data Model

One PostgreSQL 18 database with PostGIS and pgvector. Alembic owns all DDL. Tables are
owned by exactly one module; cross-module reads go through the owning module's service
layer, never by importing another module's models. (ADR-0001, ADR-0002)

## 1. Conventions

Applied without exception. A migration that violates one of these fails review.

| Rule | Form |
|---|---|
| Primary keys | `id UUID PRIMARY KEY DEFAULT uuidv7()`. Application generates via `core.ids.new_id()`; the DB default exists for fixtures and manual inserts. (ADR-0003) |
| Client identifiers | Clients generate `client_idempotency_key UUID` only. Never a primary key. A skewed device clock would destroy the insert locality that justifies v7. |
| Public identifiers | `slug TEXT UNIQUE` on anything user-visible. Internal UUIDs are never exposed on public surfaces. |
| Timestamps | `TIMESTAMPTZ`, stored UTC. `created_at` on every table, `updated_at` where mutable. |
| Money | `*_minor BIGINT` plus `currency CHAR(3)`. Never float, never numeric-for-money. Observations store the observed currency and never a converted value. (ADR-0004) |
| Quantities | `NUMERIC(12,4)` with an explicit unit of measure column. |
| Enumerations | Defined once as a Python `StrEnum`, emitted to OpenAPI, enforced by `TEXT` plus `CHECK`. Native PG enums are avoided because altering them is painful and they do not generate cleanly. |
| Deletion | None. Status columns and compensating entries only. |
| Foreign keys | Always declared. `ON DELETE RESTRICT` by default. |
| Geometry | `geography(Point, 4326)`. Nullable only on `branches`, where `branch_kind = 'online'`. |
| Naming | `snake_case`, plural table names, singular column names, `_id` suffix on references. |

## 2. Module ownership

| Module | Tables |
|---|---|
| `identity` | `users`, `contributor_trust`, `subject_keys`, `erasure_counters`, `push_tokens` |
| `geo` | `chains`, `branches`, `branch_candidates`, `branch_attribute_ratings` |
| `catalog` | `brands`, `categories`, `products`, `product_gtins`, `product_aliases`, `product_groups`, `product_group_members`, `collections`, `collection_members`, `product_search_docs` |
| `lexicon` | `chain_lexicon` |
| `ingest` | `submissions`, `media_objects`, `extraction_runs`, `receipts`, `receipt_lines` |
| `observations` | `price_observations` |
| `integrity` | `integrity_signals`, `review_tasks`, `review_leases`, `review_responses` |
| `economy` | `points_ledger`, `bounties` |
| `indexing` | `baskets`, `basket_items`, `index_runs`, `index_values` |
| `search` | `search_queries` |

## 3. identity

```sql
CREATE TABLE users (
    id                UUID PRIMARY KEY DEFAULT uuidv7(),
    slug              TEXT UNIQUE NOT NULL,
    phone_e164        TEXT UNIQUE,             -- nulled on erasure
    display_name      TEXT,
    locale            TEXT NOT NULL DEFAULT 'tr',
    role              TEXT NOT NULL DEFAULT 'contributor'
                      CHECK (role IN ('contributor','moderator','operator','admin')),
    status            TEXT NOT NULL DEFAULT 'active'
                      CHECK (status IN ('active','suspended','deleted')),
    erased_at         TIMESTAMPTZ,             -- identity stripped; references repoint to the tombstone
    is_tombstone      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT erased_users_are_stripped
        CHECK (erased_at IS NULL OR (phone_e164 IS NULL AND display_name IS NULL))
);
CREATE UNIQUE INDEX users_single_tombstone_uq ON users (is_tombstone) WHERE is_tombstone;

-- Erasures are counted, not identified.
CREATE TABLE erasure_counters (
    period_month DATE PRIMARY KEY,
    erasures     INTEGER NOT NULL DEFAULT 0
);

-- Per-subject key encrypting key. Erasure destroys the wrapped KEK, rendering every
-- media object under it permanently unreadable, including in immutable replicas and
-- versioned objects that ordinary deletion cannot reach. (ADR-0071)
-- All erased contributor references point at one well-known row, not at per-user
-- pseudonyms. A unique id per erased user would keep their submissions mutually
-- linkable, which is pseudonymisation rather than anonymisation. (ADR-0084)
-- Seeded by migration with a fixed UUID.
-- users.is_tombstone = TRUE, exactly one row.

CREATE TABLE subject_keys (
    user_id      UUID PRIMARY KEY REFERENCES users(id),
    kek_ref      TEXT,                          -- pointer into the external key store
    shredded_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT shredded_has_no_ref
        CHECK (shredded_at IS NULL OR kek_ref IS NULL)
);

-- Derived, recomputed on adjudication. Never edited by hand.
CREATE TABLE contributor_trust (
    user_id             UUID PRIMARY KEY REFERENCES users(id),
    submission_accuracy NUMERIC(5,4),          -- accepted / adjudicated
    review_accuracy     NUMERIC(5,4),          -- agreement with ground truth, incl. honeypots
    review_weight       NUMERIC(5,4) NOT NULL,   -- seeded from tuning.json, never a DDL default
    submissions_total   INTEGER NOT NULL DEFAULT 0,
    reviews_total       INTEGER NOT NULL DEFAULT 0,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

```sql
-- Tier C under ADR-0071: deleted outright on erasure.
CREATE TABLE push_tokens (
    id           UUID PRIMARY KEY DEFAULT uuidv7(),
    user_id      UUID NOT NULL REFERENCES users(id),
    platform     TEXT NOT NULL CHECK (platform IN ('ios','android')),
    token        TEXT NOT NULL,
    locale       TEXT NOT NULL,
    enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    last_seen_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (platform, token)
);
CREATE INDEX push_tokens_user_ix ON push_tokens (user_id) WHERE enabled;
```

`review_weight` starts low and rises with demonstrated accuracy. It decays for reviewers
who approve indiscriminately, which is what stops peer review becoming a rubber stamp.
(ADR-0049)

## 4. geo

```sql
CREATE TABLE chains (
    id                 UUID PRIMARY KEY DEFAULT uuidv7(),
    slug               VARCHAR(64) UNIQUE NOT NULL,
    name               VARCHAR(200) NOT NULL,
    pos_vendor         VARCHAR(64),            -- receipt layout is per POS, not per chain
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE branches (
    id                 UUID PRIMARY KEY DEFAULT uuidv7(),
    chain_id           UUID NOT NULL REFERENCES chains(id) ON DELETE RESTRICT,
    slug               VARCHAR(64) UNIQUE NOT NULL,
    name               VARCHAR(200) NOT NULL,
    branch_kind        VARCHAR(16) NOT NULL DEFAULT 'physical'
                       CHECK (branch_kind IN ('physical','online')),
    geom               geography(Point, 4326),
    address            TEXT,
    city               TEXT,
    source_provider    VARCHAR(32),            -- 'overture' | 'manual' | 'scrape'
    source_id          VARCHAR(128),
    source_confidence  NUMERIC(4,3),
    operating_status   VARCHAR(24) NOT NULL DEFAULT 'open'
                       CHECK (operating_status IN ('open','temporarily_closed','permanently_closed')),
    verified_by_human  BOOLEAN NOT NULL DEFAULT FALSE,
    verified_by        UUID REFERENCES users(id) ON DELETE RESTRICT,
    verified_at        TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT physical_has_geom
        CHECK (branch_kind <> 'physical' OR geom IS NOT NULL),
    CONSTRAINT online_has_no_geom
        CHECK (branch_kind <> 'online' OR geom IS NULL),
    -- Verification is an operator action with an actor and a time. A true flag
    -- with neither recorded is a claim nobody made, and it gates every
    -- published figure.
    CONSTRAINT verification_has_an_actor
        CHECK (NOT verified_by_human OR (verified_by IS NOT NULL AND verified_at IS NOT NULL)),
    CONSTRAINT confidence_in_range
        CHECK (source_confidence IS NULL OR source_confidence BETWEEN 0 AND 1)
);

-- Partial: manual entry is a first-class path and carries no source key, so a
-- total unique index would allow exactly one manually entered branch.
CREATE UNIQUE INDEX uq_branches_source
    ON branches (source_provider, source_id)
    WHERE source_id IS NOT NULL;

CREATE INDEX ix_branches_geom ON branches USING GIST (geom);
CREATE INDEX ix_branches_chain_id ON branches (chain_id);

-- Pipeline output. Never joined to prices. Promotion to `branches` is explicit.
CREATE TABLE branch_candidates (
    id                 UUID PRIMARY KEY DEFAULT uuidv7(),
    source_provider    VARCHAR(32) NOT NULL,
    source_id          VARCHAR(128) NOT NULL,
    raw                JSONB NOT NULL,
    name               VARCHAR(200),
    geom               geography(Point, 4326),
    suggested_chain_id UUID REFERENCES chains(id) ON DELETE RESTRICT,
    operating_status   VARCHAR(24),
    source_confidence  NUMERIC(4,3),
    status             VARCHAR(16) NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending','promoted','rejected','duplicate')),
    promoted_branch_id UUID REFERENCES branches(id) ON DELETE RESTRICT,
    -- The survivor. ADR-0023 marks a duplicate with a reference to it, so a
    -- re-run does not resurrect the row and an operator can see what it was
    -- folded into.
    duplicate_of_id    UUID REFERENCES branch_candidates(id) ON DELETE RESTRICT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Re-runs upsert on the source key and operators move status, so the row
    -- mutates. Without this there is nothing to sort stale candidates by.
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (source_provider, source_id),
    -- Nullable, because a provider may say nothing. When it does, ingest
    -- normalises to our vocabulary rather than storing the provider spelling.
    CONSTRAINT status_known_if_present
        CHECK (operating_status IS NULL
               OR operating_status IN ('open','temporarily_closed','permanently_closed')),
    CONSTRAINT confidence_in_range
        CHECK (source_confidence IS NULL OR source_confidence BETWEEN 0 AND 1),
    -- Both directions, so a rejected candidate cannot carry a branch reference
    -- and a promoted one cannot lack it.
    CONSTRAINT promoted_iff_branch
        CHECK ((status = 'promoted') = (promoted_branch_id IS NOT NULL)),
    CONSTRAINT duplicate_iff_survivor
        CHECK ((status = 'duplicate') = (duplicate_of_id IS NOT NULL)),
    -- Following the survivor chain must terminate.
    CONSTRAINT not_its_own_duplicate
        CHECK (duplicate_of_id IS NULL OR duplicate_of_id <> id)
);

CREATE INDEX ix_branch_candidates_status ON branch_candidates (status);
```

```sql
-- ADR-0052: fixed ordinal dimensions, no free text.
CREATE TABLE branch_attribute_ratings (
    id             UUID PRIMARY KEY DEFAULT uuidv7(),
    branch_id      UUID NOT NULL REFERENCES branches(id) ON DELETE RESTRICT,
    contributor_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    dimension      VARCHAR(24) NOT NULL
                   CHECK (dimension IN ('produce_freshness','stock_breadth','queue_length')),
    score          SMALLINT NOT NULL CHECK (score BETWEEN 1 AND 5),
    observed_at    TIMESTAMPTZ NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (branch_id, contributor_id, dimension, observed_at)
);
CREATE INDEX ix_branch_attribute_ratings_recent
    ON branch_attribute_ratings (branch_id, dimension, observed_at DESC);
```

Ordinal only, recency-weighted on read, and suppressed below a minimum sample count. Rigorously
excluded from any index computation: a subjective quality rating contaminating a published
inflation figure would destroy its defensibility (ADR-0029, ADR-0052).

The unique key is an **idempotency guard against a resubmitted rating, not a rate limit**, and it
cannot be one: the same contributor can rate the same branch fifty times a day at different
timestamps and every row is legal. The aggregate handles it instead. **One rating per contributor
per dimension counts, the most recent within the window.** Fifty submissions become one vote, and
manipulation then requires multiple accounts, which is the general problem already carried by phone
OTP, device fingerprinting and the trust model rather than a new special case. This is not
inferable from the constraint, which is why it is written here.

No price attaches to a branch with `verified_by_human = FALSE`. Open map data has closed
stores, wrong pins, and cross-provider duplicates, and access-scoped comparison means a
mis-pinned branch corrupts results rather than merely showing a wrong dot. (ADR-0023)

Online branches are real price sources and appear in item lookup and history, but are
excluded from access-scoped basket comparison and from per-category chain indices, because
an online seller's pricing is not evidence about the physical market. (ADR-0045)

Those two exclusions are **not predicates that each query writes**. Index and comparison code
reaches branches through `geo.service.index_eligible_branches()` (physical and verified) or
`geo.service.public_branches()` (verified, any kind), and the `branch-scope` gate enforces it.
Neither scope filters `operating_status`: a permanently closed branch has real history, and an
index recomputed over a past period must still see the prices observed then. (ADR-0088)

## 5. catalog

```sql
CREATE TABLE brands (
    id              UUID PRIMARY KEY DEFAULT uuidv7(),
    slug            TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    is_private_label BOOLEAN NOT NULL DEFAULT FALSE,
    owner_chain_id  UUID REFERENCES chains(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT private_label_has_owner
        CHECK (NOT is_private_label OR owner_chain_id IS NOT NULL)
);

-- ADR-0089: a shape of the tree, named by every figure computed under it.
-- `index_runs` and `index_values` both carry `taxonomy_version`; before this
-- table they named an integer no row defined.
CREATE TABLE taxonomy_versions (
    version      INTEGER PRIMARY KEY,
    status       VARCHAR(16) NOT NULL DEFAULT 'draft'
                 CHECK (status IN ('draft','active','superseded')),
    activated_at TIMESTAMPTZ,
    notes        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Without this an active version can carry no activation time, and the
    -- announcement date ADR-0079 rule 2 requires has nowhere to come from.
    CONSTRAINT activated_iff_not_draft
        CHECK ((status = 'draft') = (activated_at IS NULL))
);

-- At most one active version. ADR-0079 rule 3 runs two series in parallel, but
-- the second is computed under a draft or superseded version.
CREATE UNIQUE INDEX uq_taxonomy_versions_active
    ON taxonomy_versions (status) WHERE status = 'active';

-- Identity. Stable across restructures, and what a product points at. No status
-- column: membership in a version's structure is what makes a node live.
CREATE TABLE categories (
    id               UUID PRIMARY KEY DEFAULT uuidv7(),
    -- Globally unique and stable, because it is a URL.
    slug             VARCHAR(64) UNIQUE NOT NULL,
    name_i18n        JSONB NOT NULL,
    -- Where a merged node's history went. Same shape as duplicate_of_id.
    superseded_by_id UUID REFERENCES categories(id) ON DELETE RESTRICT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- `tr` at write; the remaining launch locales before a version is
    -- activated, which spans rows and is therefore a trigger.
    CONSTRAINT has_turkish_name CHECK (name_i18n ? 'tr'),
    CONSTRAINT not_its_own_successor
        CHECK (superseded_by_id IS NULL OR superseded_by_id <> id)
);

-- Shape, per version. Two trees coexist as two sets of rows.
CREATE TABLE category_structure (
    category_id      UUID NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    taxonomy_version INTEGER NOT NULL
                     REFERENCES taxonomy_versions(version) ON DELETE RESTRICT,
    parent_id        UUID,
    -- Derived, maintained by trigger, never written by the application. Labels
    -- are the slug with hyphens mapped to underscores, which cannot collide
    -- because slugify never emits an underscore.
    path             LTREE NOT NULL,
    sort_order       SMALLINT NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (category_id, taxonomy_version),
    -- Composite, so a parent is necessarily a node in the same version. A plain
    -- reference to categories would let a path be built across two trees.
    FOREIGN KEY (parent_id, taxonomy_version)
        REFERENCES category_structure(category_id, taxonomy_version) ON DELETE RESTRICT,
    CONSTRAINT not_its_own_parent
        CHECK (parent_id IS NULL OR parent_id <> category_id)
);

CREATE INDEX ix_category_structure_path ON category_structure USING GIST (path);
CREATE INDEX ix_category_structure_parent
    ON category_structure (taxonomy_version, parent_id);

CREATE TABLE products (
    id                 UUID PRIMARY KEY DEFAULT uuidv7(),
    slug               TEXT UNIQUE NOT NULL,
    canonical_name     TEXT NOT NULL,          -- Turkish, as it appears locally
    brand_id           UUID REFERENCES brands(id),
    category_id        UUID NOT NULL REFERENCES categories(id),
    net_content_value  NUMERIC(12,4),
    net_content_uom    TEXT,                   -- 'g','kg','ml','l','piece'
    unit_basis         TEXT NOT NULL DEFAULT 'per_piece'
                       CHECK (unit_basis IN ('per_l','per_kg','per_piece')),
    owner_chain_id     UUID REFERENCES chains(id),   -- private label only
    source             TEXT NOT NULL DEFAULT 'operator'
                       CHECK (source IN ('operator','scrape','contributor')),
    verification_state TEXT NOT NULL DEFAULT 'unverified'
                       CHECK (verification_state IN ('unverified','verified')),
    status             TEXT NOT NULL DEFAULT 'active'
                       CHECK (status IN ('draft','active','merged','retired')),
    merged_into_id     UUID REFERENCES products(id),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT merged_points_somewhere
        CHECK (status <> 'merged' OR merged_into_id IS NOT NULL)
);

CREATE TABLE product_gtins (
    id           UUID PRIMARY KEY DEFAULT uuidv7(),
    product_id   UUID NOT NULL REFERENCES products(id),
    gtin         TEXT NOT NULL,
    gtin_kind    TEXT NOT NULL
                 CHECK (gtin_kind IN ('ean13','ean8','upc','plu','chain_internal')),
    chain_id     UUID REFERENCES chains(id),   -- required for chain_internal namespace
    is_primary   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT internal_gtin_is_chain_scoped
        CHECK (gtin_kind <> 'chain_internal' OR chain_id IS NOT NULL)
);
-- Global namespace: one product per code.
CREATE UNIQUE INDEX product_gtins_global_uq
    ON product_gtins (gtin, gtin_kind) WHERE gtin_kind <> 'chain_internal';
-- Chain-internal namespace: codes legitimately collide across chains.
CREATE UNIQUE INDEX product_gtins_chain_uq
    ON product_gtins (chain_id, gtin) WHERE gtin_kind = 'chain_internal';

CREATE TABLE product_aliases (
    id           UUID PRIMARY KEY DEFAULT uuidv7(),
    product_id   UUID NOT NULL REFERENCES products(id),
    locale       TEXT NOT NULL,
    alias_text   TEXT NOT NULL,
    source       TEXT NOT NULL
                 CHECK (source IN ('operator','contributor','mined','lexicon')),
    status       TEXT NOT NULL DEFAULT 'active'
                 CHECK (status IN ('pending','active','rejected')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (product_id, locale, alias_text)
);

-- Substitution grouping. 1L and 1.5L Coke are separate products, one group.
CREATE TABLE product_groups (
    id         UUID PRIMARY KEY DEFAULT uuidv7(),
    slug       TEXT UNIQUE NOT NULL,
    name       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE product_group_members (
    group_id   UUID NOT NULL REFERENCES product_groups(id),
    product_id UUID NOT NULL REFERENCES products(id),
    PRIMARY KEY (group_id, product_id)
);

-- Dietary and national sets. Schema only until query logs justify curation.
CREATE TABLE collections (
    id         UUID PRIMARY KEY DEFAULT uuidv7(),
    slug       TEXT UNIQUE NOT NULL,
    name_i18n  JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE collection_members (
    collection_id UUID NOT NULL REFERENCES collections(id),
    product_id    UUID NOT NULL REFERENCES products(id),
    PRIMARY KEY (collection_id, product_id)
);

-- Materialised retrieval document. Rebuilt on product or alias change.
CREATE TABLE product_search_docs (
    product_id    UUID PRIMARY KEY REFERENCES products(id),
    lexical_text  TEXT NOT NULL,        -- Turkish-folded: canonical name + brand + aliases
    semantic_text TEXT NOT NULL,        -- unfolded natural language, embedding input
    embedding     VECTOR,          -- dimension pinned by migration once ADR-0024 resolves
    model_version TEXT NOT NULL,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX product_search_lex_gix
    ON product_search_docs USING GIN (lexical_text gin_trgm_ops);
-- HNSW requires a fixed dimension; this index is created by the migration that pins it.
-- CREATE INDEX product_search_emb_hnsw
--     ON product_search_docs USING hnsw (embedding vector_cosine_ops);
```

`lexical_text` and `semantic_text` are deliberately different. The fold is lossy and
correct for trigram; it degrades a model trained on natural diacritics. (ADR-0025)

## 6. lexicon

```sql
CREATE TABLE chain_lexicon (
    id           UUID PRIMARY KEY DEFAULT uuidv7(),
    chain_id     UUID NOT NULL REFERENCES chains(id),
    key_kind     TEXT NOT NULL CHECK (key_kind IN ('sku','raw_text')),
    key_value    TEXT NOT NULL,        -- sku verbatim, or Turkish-folded raw text
    product_id   UUID NOT NULL REFERENCES products(id),
    confidence   NUMERIC(4,3) NOT NULL DEFAULT 1.000,
    decided_by   UUID NOT NULL REFERENCES users(id),
    decided_via  TEXT NOT NULL
                 CHECK (decided_via IN ('operator','review_t1')),
    status       TEXT NOT NULL DEFAULT 'active'
                 CHECK (status IN ('active','superseded')),
    superseded_by UUID REFERENCES chain_lexicon(id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- One ACTIVE entry per key. Superseded history accumulates without limit.
CREATE UNIQUE INDEX chain_lexicon_active_uq
    ON chain_lexicon (chain_id, key_kind, key_value) WHERE status = 'active';
```

Exact match, not fuzzy match. Resolving a key applies retroactively to every observation
already ingested with that key and automatically to every future one. `decided_by` is
never null: no automated process writes here. (ADR-0008, ADR-0011)

## 7. ingest

```sql
CREATE TABLE submissions (
    id                     UUID PRIMARY KEY DEFAULT uuidv7(),
    contributor_id         UUID NOT NULL REFERENCES users(id),
    client_idempotency_key UUID NOT NULL UNIQUE,
    channel                TEXT NOT NULL
                           CHECK (channel IN ('app','console','scrape')),
    kind                   TEXT NOT NULL
                           CHECK (kind IN ('receipt','shelf_manual','shelf_barcode')),
    claimed_branch_id      UUID REFERENCES branches(id),
    captured_at            TIMESTAMPTZ NOT NULL,
    received_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    location_matched       BOOLEAN,             -- derived at ingest
    location_confidence    NUMERIC(4,3),        -- coordinate itself is discarded
    status                 TEXT NOT NULL DEFAULT 'received'
                           CHECK (status IN ('received','extracting','extracted',
                                             'in_review','accepted','rejected','failed')),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE media_objects (
    id            UUID PRIMARY KEY DEFAULT uuidv7(),
    submission_id UUID REFERENCES submissions(id),
    role          TEXT NOT NULL CHECK (role IN ('original','crop')),
    bucket        TEXT NOT NULL,
    object_key    TEXT NOT NULL,
    content_hash  TEXT NOT NULL,
    mime_type     TEXT NOT NULL,
    byte_size     BIGINT NOT NULL,
    width         INTEGER,
    height        INTEGER,
    reencoded     BOOLEAN NOT NULL DEFAULT FALSE,
    subject_user_id UUID NOT NULL REFERENCES users(id),   -- whose KEK wraps this object
    wrapped_dek   BYTEA NOT NULL,                          -- data key, wrapped by the subject KEK
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (bucket, object_key)
);
-- Crops share the subject of their original: shredding an original while its crops
-- persist would retain fragments of exactly the sensitive content.
CREATE INDEX media_subject_ix ON media_objects (subject_user_id);
-- Identical bytes mean an identical image. The confirm endpoint detects the existing
-- row and links to it rather than erroring. (G10)
CREATE INDEX media_content_hash_ix
    ON media_objects (content_hash) WHERE role = 'original';

-- Reprocessing the corpus when a model improves (ADR-0013, ADR-0069) requires that a
-- second extraction supersede the first rather than coexist with it. Without this,
-- every reprocessed receipt double-counts its observations.
CREATE TABLE extraction_runs (
    id                 UUID PRIMARY KEY DEFAULT uuidv7(),
    submission_id      UUID NOT NULL REFERENCES submissions(id),
    extraction_method  TEXT NOT NULL,
    extraction_version TEXT NOT NULL,
    is_current         BOOLEAN NOT NULL DEFAULT TRUE,
    superseded_by      UUID REFERENCES extraction_runs(id),
    started_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at       TIMESTAMPTZ,
    status             TEXT NOT NULL DEFAULT 'running'
                       CHECK (status IN ('running','completed','failed','superseded')),
    UNIQUE (submission_id, extraction_method, extraction_version)
);
CREATE UNIQUE INDEX extraction_runs_current_uq
    ON extraction_runs (submission_id) WHERE is_current;

CREATE TABLE receipts (
    id                         UUID PRIMARY KEY DEFAULT uuidv7(),
    submission_id              UUID NOT NULL REFERENCES submissions(id),
    extraction_run_id          UUID NOT NULL REFERENCES extraction_runs(id),
    branch_id                  UUID REFERENCES branches(id),
    receipt_datetime           TIMESTAMPTZ,
    printed_total_minor        BIGINT,
    tax_total_minor            BIGINT,          -- KDV breakdown, informational, NOT an addend
    discount_total_minor       BIGINT,
    currency                   CHAR(3) NOT NULL DEFAULT 'TRY',
    fingerprint                TEXT,            -- branch + datetime + total + line_count
    reconciliation_status      TEXT NOT NULL DEFAULT 'unchecked'
                               CHECK (reconciliation_status IN
                                     ('unchecked','balanced','residual','unparseable')),
    reconciliation_residual_minor BIGINT,
    status                     TEXT NOT NULL DEFAULT 'pending'
                               CHECK (status IN ('pending','accepted','flagged','duplicate','rejected','superseded')),
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (extraction_run_id)
);
CREATE INDEX receipts_fingerprint_ix ON receipts (fingerprint);

CREATE TABLE receipt_lines (
    id                   UUID PRIMARY KEY DEFAULT uuidv7(),
    receipt_id           UUID NOT NULL REFERENCES receipts(id),
    line_index           INTEGER NOT NULL,
    line_kind            TEXT NOT NULL
                         CHECK (line_kind IN ('item','discount','subtotal','tax','tender','unknown')),
    raw_text             TEXT NOT NULL,         -- verbatim, immutable
    interpreted_text     TEXT,                  -- expanded, versioned with extraction
    sku_text             TEXT,
    raw_quantity         NUMERIC(12,4),
    raw_uom              TEXT,
    raw_unit_price_minor BIGINT,
    raw_line_total_minor BIGINT,
    bbox                 JSONB,                 -- [x, y, w, h] normalised, required for T2 crops
    modifies_line_id     UUID REFERENCES receipt_lines(id),   -- discount to its item
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (receipt_id, line_index)
);
```

`receipt_lines` is append-only. Corrections from review create a new extraction run, never
an update in place. (ADR-0006)

## 8. observations

```sql
CREATE TABLE price_observations (
    id                UUID PRIMARY KEY DEFAULT uuidv7(),
    source_kind       TEXT NOT NULL
                      CHECK (source_kind IN ('receipt_line','shelf_manual','shelf_barcode','scrape')),
    source_id         UUID NOT NULL,
    branch_id         UUID NOT NULL REFERENCES branches(id),
    product_id        UUID REFERENCES products(id),      -- NULL until the lexicon resolves it
    observed_at       TIMESTAMPTZ NOT NULL,
    price_minor       BIGINT NOT NULL,
    currency          CHAR(3) NOT NULL DEFAULT 'TRY',
    quantity          NUMERIC(12,4) NOT NULL DEFAULT 1,
    uom               TEXT NOT NULL DEFAULT 'piece',
    unit_price_minor  BIGINT,                             -- derived, per canonical unit
    unit_basis        TEXT CHECK (unit_basis IN ('per_l','per_kg','per_piece')),
    price_kind        TEXT NOT NULL DEFAULT 'regular'
                      CHECK (price_kind IN ('regular','promotional','member','clearance')),
    status            TEXT NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending','provisional','accepted','flagged','superseded')),
    confidence        NUMERIC(4,3),
    extraction_run_id UUID REFERENCES extraction_runs(id),   -- NULL for non-receipt sources
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_kind, source_id)
);
-- When an extraction run is superseded, its observations move to 'superseded' in the
-- same transaction as the new run's observations are written. Never deleted.
CREATE INDEX obs_run_ix ON price_observations (extraction_run_id) WHERE extraction_run_id IS NOT NULL;

CREATE INDEX obs_branch_product_time_ix
    ON price_observations (branch_id, product_id, observed_at DESC);
CREATE INDEX obs_unresolved_ix
    ON price_observations (branch_id, observed_at DESC) WHERE product_id IS NULL;
```

A nullable `product_id` is deliberate. An unresolved observation is a real fact already
collected; it simply cannot enter an index yet.

`unit_price_minor` is what makes 500g and 750g packs comparable, and comparison is the
product. It is derived, never submitted.

There is no such thing as "the price". Read surfaces expose the most recent observation
with its age and confidence, or they are lying during exactly the volatile periods that
matter most.

## 9. integrity

```sql
CREATE TABLE integrity_signals (
    id           UUID PRIMARY KEY DEFAULT uuidv7(),
    subject_kind TEXT NOT NULL CHECK (subject_kind IN ('submission','receipt','observation')),
    subject_id   UUID NOT NULL,
    signal_kind  TEXT NOT NULL
                 CHECK (signal_kind IN ('reconciliation','fingerprint_duplicate','phash_duplicate',
                                        'location_mismatch','extractor_disagreement',
                                        'conditional_anomaly','novel_string','image_quality')),
    score        NUMERIC(5,4),
    detail       JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX integrity_subject_ix ON integrity_signals (subject_kind, subject_id);

CREATE TABLE review_tasks (
    id              UUID PRIMARY KEY DEFAULT uuidv7(),
    tier            TEXT NOT NULL CHECK (tier IN ('t1_lexicon','t2_crop','t3_receipt')),
    subject_kind    TEXT NOT NULL,
    subject_id      UUID NOT NULL,
    receipt_id      UUID REFERENCES receipts(id),  -- enforces one line per reviewer per receipt
    crop_media_id   UUID REFERENCES media_objects(id),
    question        JSONB NOT NULL,                -- closed form: prompt + options
    is_honeypot     BOOLEAN NOT NULL DEFAULT FALSE,
    expected_answer JSONB,
    priority        INTEGER NOT NULL DEFAULT 0,    -- blocked observation count
    required_responses INTEGER NOT NULL,           -- quorum, from tuning.json
    agreement_threshold NUMERIC(4,3) NOT NULL,     -- weighted agreement needed, from tuning.json
    status          TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open','resolved','escalated','expired','withdrawn')),
    resolved_answer JSONB,
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT honeypot_has_expected
        CHECK (NOT is_honeypot OR expected_answer IS NOT NULL),
    CONSTRAINT crop_tier_has_media
        CHECK (tier <> 't2_crop' OR crop_media_id IS NOT NULL)
);
CREATE INDEX review_open_ix ON review_tasks (tier, priority DESC) WHERE status = 'open';

-- Leases prevent the same task being handed to more reviewers than the quorum needs.
-- Expired leases are reclaimed by a scheduled sweep.
CREATE TABLE review_leases (
    id          UUID PRIMARY KEY DEFAULT uuidv7(),
    task_id     UUID NOT NULL REFERENCES review_tasks(id),
    reviewer_id UUID NOT NULL REFERENCES users(id),
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (task_id, reviewer_id)
);
CREATE INDEX review_leases_expiry_ix ON review_leases (expires_at);

CREATE TABLE review_responses (
    id          UUID PRIMARY KEY DEFAULT uuidv7(),
    task_id     UUID NOT NULL REFERENCES review_tasks(id),
    reviewer_id UUID NOT NULL REFERENCES users(id),
    answer      JSONB NOT NULL,
    weight      NUMERIC(5,4) NOT NULL,          -- reviewer weight at time of answer
    agreed      BOOLEAN,                        -- set on adjudication
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (task_id, reviewer_id)
);
```

Questions are closed form, never free-text transcription: faster, comparable across
reviewers, and cleanly scoreable. (ADR-0060)

Task assignment enforces two rules that are not expressible as constraints and live in the
service layer: a reviewer is never assigned a task whose subject traces to their own
submission or to a submitter they share history with (ADR-0048), and never more than one
line from a given `receipt_id`, because many crops from one receipt reconstruct the basket
(ADR-0059).

## 10. economy

```sql
CREATE TABLE points_ledger (
    id                UUID PRIMARY KEY DEFAULT uuidv7(),
    user_id           UUID NOT NULL REFERENCES users(id),
    amount            INTEGER NOT NULL,        -- signed; reversals are negative
    reason_code       TEXT NOT NULL,
    subject_kind      TEXT,
    subject_id        UUID,
    reverses_entry_id UUID REFERENCES points_ledger(id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX points_user_ix ON points_ledger (user_id, created_at DESC);

CREATE TABLE bounties (
    id            UUID PRIMARY KEY DEFAULT uuidv7(),
    branch_id     UUID REFERENCES branches(id),
    product_id    UUID REFERENCES products(id),
    category_id   UUID REFERENCES categories(id),
    multiplier    NUMERIC(4,2) NOT NULL,       -- from tuning.json
    reason        TEXT NOT NULL,               -- 'stale_cell' | 'empty_cell' | 'campaign'
    expires_at    TIMESTAMPTZ NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Append-only. No mutable score column exists anywhere; balances and leaderboards are
derived. Clawback writes a negative row referencing the original so history survives and
disputes are auditable. (ADR-0019)

Bounties exist because points that scale with raw submission count instruct contributors
to farm the nearest store with the fewest items, and they will. Reward tracks marginal
information value: how stale or empty the target cell was. (ADR-0020)

## 11. indexing

```sql
CREATE TABLE baskets (
    id               UUID PRIMARY KEY DEFAULT uuidv7(),
    slug             TEXT UNIQUE NOT NULL,
    name_i18n        JSONB NOT NULL,
    taxonomy_version INTEGER NOT NULL,
    status           TEXT NOT NULL DEFAULT 'draft'
                     CHECK (status IN ('draft','active','retired')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Surrogate PK: PK columns are implicitly NOT NULL in Postgres, so a composite key
-- containing a deliberately-nullable member cannot hold the rows it was designed for.
CREATE TABLE basket_items (
    id               UUID PRIMARY KEY DEFAULT uuidv7(),
    basket_id        UUID NOT NULL REFERENCES baskets(id),
    product_id       UUID REFERENCES products(id),
    product_group_id UUID REFERENCES product_groups(id),
    weight           NUMERIC(8,4) NOT NULL,
    weight_source    TEXT NOT NULL
                     CHECK (weight_source IN ('observed_expenditure','coicop_reference','manual')),
    coicop_code      TEXT,
    CONSTRAINT exactly_one_target
        CHECK ((product_id IS NULL) <> (product_group_id IS NULL))
);
CREATE UNIQUE INDEX basket_items_product_uq
    ON basket_items (basket_id, product_id) WHERE product_id IS NOT NULL;
CREATE UNIQUE INDEX basket_items_group_uq
    ON basket_items (basket_id, product_group_id) WHERE product_group_id IS NOT NULL;

-- ADR-0046: a scraped, unverified product must never enter a published basket. A CHECK
-- constraint cannot reach another table, so this is a trigger rather than a service-layer
-- convention.
CREATE OR REPLACE FUNCTION basket_item_requires_verified_product() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.product_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM products
        WHERE id = NEW.product_id
          AND verification_state = 'verified'
          AND status = 'active'
    ) THEN
        RAISE EXCEPTION 'basket_items.product_id % is not a verified active product', NEW.product_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_basket_item_verified
    BEFORE INSERT OR UPDATE ON basket_items
    FOR EACH ROW EXECUTE FUNCTION basket_item_requires_verified_product();

CREATE TABLE index_runs (
    id                   UUID PRIMARY KEY DEFAULT uuidv7(),
    basket_id            UUID NOT NULL REFERENCES baskets(id),
    period_start         DATE NOT NULL,
    period_end           DATE NOT NULL,
    methodology_version  TEXT NOT NULL,
    taxonomy_version     INTEGER NOT NULL,
    staleness_window_days INTEGER NOT NULL,
    missing_policy       TEXT NOT NULL,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (basket_id, period_start, period_end, methodology_version)
);

-- scope_id is NULL for scope_kind = 'market', which is the headline published figure,
-- so it cannot be a PK member.
CREATE TABLE index_values (
    id                 UUID PRIMARY KEY DEFAULT uuidv7(),
    run_id             UUID NOT NULL REFERENCES index_runs(id),
    scope_kind         TEXT NOT NULL CHECK (scope_kind IN ('market','chain','branch','category')),
    scope_id           UUID,
    series_basis       TEXT NOT NULL DEFAULT 'try_nominal'
                       CHECK (series_basis IN ('try_nominal','fx_deflated')),
    index_value        NUMERIC(12,4) NOT NULL,     -- base period = 100
    basket_cost_minor  BIGINT,                     -- informational, not the series
    currency           CHAR(3) NOT NULL DEFAULT 'TRY',
    coverage_pct       NUMERIC(5,2) NOT NULL,
    imputed_pct        NUMERIC(5,2) NOT NULL DEFAULT 0,
    staleness_days_p50 NUMERIC(6,2),
    observations_count INTEGER NOT NULL
);
CREATE UNIQUE INDEX index_values_uq
    ON index_values (run_id, scope_kind, series_basis, COALESCE(scope_id, '00000000-0000-0000-0000-000000000000'::uuid));
```

Every published value carries its methodology version, taxonomy version, coverage and
staleness. A figure without those is not publishable. (ADR-0029)

## 12. fx

```sql
-- ADR-0004 applies conversion at read time with a recorded rate. Rates are facts and
-- follow the same immutability rule as observations.
CREATE TABLE fx_rates (
    id            UUID PRIMARY KEY DEFAULT uuidv7(),
    base_currency CHAR(3) NOT NULL,
    quote_currency CHAR(3) NOT NULL,
    rate          NUMERIC(18,8) NOT NULL,
    as_of         DATE NOT NULL,
    source        TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (base_currency, quote_currency, as_of, source)
);
```

A converted price is never stored. Any response that converts carries the rate and its
`as_of` date, so the conversion is reproducible and auditable.

## 13. audit

```sql
-- Integrity in this system rests on human decisions, so those decisions need a record
-- independent of the tables they mutate.
CREATE TABLE audit_log (
    id           UUID PRIMARY KEY DEFAULT uuidv7(),
    actor_id     UUID REFERENCES users(id),
    actor_role   TEXT NOT NULL,
    action       TEXT NOT NULL,          -- 'lexicon.decide', 'product.merge', 'branch.verify', ...
    subject_kind TEXT NOT NULL,
    subject_id   UUID NOT NULL,
    before       JSONB,
    after        JSONB,
    request_id   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX audit_subject_ix ON audit_log (subject_kind, subject_id, created_at DESC);
CREATE INDEX audit_actor_ix ON audit_log (actor_id, created_at DESC);
```

Append-only, and never crypto-shredded: an erased contributor's `actor_id` is tombstoned
like any other reference, but the record that a decision was made survives.

## 14. search

```sql
CREATE TABLE search_queries (
    id                UUID PRIMARY KEY DEFAULT uuidv7(),
    user_id           UUID REFERENCES users(id),
    session_id        UUID NOT NULL,
    locale            TEXT NOT NULL,
    raw_query         TEXT NOT NULL,
    fold_query        TEXT NOT NULL,
    result_count      INTEGER NOT NULL,
    clicked_product_id UUID REFERENCES products(id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX search_zero_result_ix
    ON search_queries (locale, created_at DESC) WHERE result_count = 0;
```

A zero-result query followed within a session by a successful reformulation and a click is
a labelled synonym pair. This is how the alias override layer gets filled without anyone
writing translations. (ADR-0039)

## 15. State machines

**Submission**

```
received -> extracting -> extracted -> in_review -> accepted
                |                          |
                +--> failed                +--> rejected
```

**Observation**

```
pending -> provisional -> accepted
   |            |            |
   +--> flagged +--> flagged +--> superseded
```

`provisional` exists so a contributor is not left in silence for days waiting on operator
review. Peer review grants it; final adjudication confirms it or triggers a compensating
ledger entry. (ADR-0050)

`flagged` never means deleted. A flagged observation stays in the corpus and is excluded
only from published figures. (ADR-0033)

**Product**

```
draft -> active -> merged (merged_into_id set, lexicon entries repointed)
              \
               -> retired
```

Merges are non-destructive. The losing product remains, carrying a redirect. You will
merge two products that turn out to be distinct, and that must be reversible.

## 16. Extensions required

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS ltree;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

## 17. updated_at maintenance

Seven tables carry `updated_at`. Nothing in the application maintains it, so the database
does.

```sql
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

-- Applied by migration to: users, chains, branches, products, submissions
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

A CI check asserts that every table with an `updated_at` column has a corresponding
trigger. This is exactly the class of omission that produces stale timestamps nobody
notices for months.
