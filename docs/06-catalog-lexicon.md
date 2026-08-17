# 06. Catalog and Lexicon

The catalog defines what a product is. The lexicon maps what sources call it to what we
call it. Every downstream feature (price history, basket index, split basket, search)
resolves through these two layers, so errors here propagate everywhere and are the most
expensive class of mistake in the system.

## 1. Product identity

A canonical product is defined by a human. Barcodes, receipt strings and scraped names are
evidence and attributes, never identity. (ADR-0007)

**Separate products:**

- Different net content. 1L and 1.5L Coca-Cola are two products. `product_groups` handles
  substitution where a feature needs it.
- Different formulation. Full fat and semi-skimmed milk from the same producer.
- Private label from different chains. Never comparable across chains, and marked with
  `owner_chain_id` so the basket cannot accidentally compare them.

**Same product:**

- Packaging revisions carrying different barcodes. `product_gtins` is one-to-many.
- Regional name variants of an identical SKU. These become aliases.

**Never merged automatically.** A merge is an operator action, writes `merged_into_id`,
repoints lexicon entries, and leaves the losing row in place. You will merge two products
that turn out to be distinct, and reversibility is the only defence. (ADR-0007)

## 2. Taxonomy

Closed, curated, versioned, hierarchical. Operators alone may create nodes. If contributors
or a model could create categories, the tree degenerates within weeks and every basket
weight built on it becomes meaningless. (ADR-0009)

The tree carries a second job beyond classification. Because the catalog is Turkish and no
supply side exists to localise it, a fully translated tree is what makes an untranslated
catalog reachable in four languages: a German browsing `Käse` lands on the cheese node and
sees products whose names are only ever Turkish. That raises the design bar. Nodes must be
retrieval-shaped, not merely taxonomically correct, and every node needs complete
`name_i18n` coverage before launch. Roughly 150 nodes across four locales is bounded work.

Facets are a separate, open set: `halal`, `organic`, `imported`, `refrigerated`,
`private_label`. Open because they cost nothing and carry no structural weight.

Category restructuring bumps `taxonomy_version`. Any published index value names the
taxonomy version that produced it, because a restructured tree silently changes what a
category index means.

## 3. Barcodes and SKUs

Four distinct identifier namespaces that are not interchangeable.

**GTIN / EAN** is an attribute. One product may carry several across packaging revisions
and import routes, and a discontinued code can be reused later by a different product.

**Variable-weight barcodes.** EAN-13 codes beginning with `2` are reserved for in-store
restricted circulation and commonly encode weight or price rather than product identity.
Two packs of the same cheese scan as two different barcodes. Detected by prefix at ingest
and routed to the weight-item path; treating them as product identifiers would generate
thousands of phantom products. (ADR-0010)

**PLU codes** for loose produce, where they exist at all.

**Chain SKU** is chain-internal and lives in a different namespace per chain, so the same
code legitimately maps to different products at different chains. `product_gtins` scopes
`chain_internal` codes by `chain_id` and enforces global uniqueness only for real GTINs.
Where a receipt prints a code, it is the superior lexicon key: stable, unambiguous within
the chain, and immune to description changes.

Loose produce frequently carries no identifier of any kind. It is also the category with
the highest price variance, so it is a first-class path and not an afterthought.

## 4. The lexicon

```
(chain_id, key_kind, key_value) -> product_id
```

Exact match on a hash lookup, not fuzzy matching. `key_kind` is `sku` where the receipt
prints a code, otherwise `raw_text` holding the Turkish-folded description.

The economics are what make this viable. `CC KOLA 1LT PET` means the same thing on every
receipt from that chain, forever. Resolving it once applies **retroactively** to every
observation already ingested carrying that key, and **automatically** to every future one.
The first receipt from a new chain is fully manual. The fiftieth is almost entirely
automatic, with only genuinely new items needing attention.

This changes what the operator console is for. Its job is not "process a receipt", it is
"resolve unknown keys", and the queue is ordered by how many pending observations each
unknown key is blocking.

Every resolved entry is simultaneously three things: a mapping, a search alias, and a
labelled training example. That is why `decided_by` is never null.

### Resolution at ingest

```
for each receipt_line where line_kind = 'item':
    key = sku_text if present else turkish_fold(raw_text)
    entry = lookup(chain_id, key)
    if entry:
        create observation with product_id = entry.product_id
    else:
        create observation with product_id = NULL
        enqueue T1 review task, priority = count of observations blocked by this key
```

Unresolved observations are stored, not discarded. They are real facts that simply cannot
enter an index yet.

### Suggestion

The suggestion layer ranks candidates for an unresolved key. It never writes a mapping.
(ADR-0011)

Hybrid retrieval over the same index that serves user search: trigram over
`lexical_text` for brand and near-literal matches, dense vectors over `semantic_text` for
everything else, fused by reciprocal rank fusion.

The embedding input is `interpreted_text`, not `raw_text`. `CC KOLA 1LT PET` is not a
sentence, and feeding uppercase truncated abbreviations to a model trained on natural
language performs badly. The extraction pass emits both in one call: `raw_text` verbatim
and immutable, `interpreted_text` expanded and versioned alongside `extraction_version`.
(ADR-0013)

## 5. Retrieval

Cross-lingual grocery search fails on lexical matching because the hard cases have zero
character overlap: `Käse` to `peynir`, `гречка` to `karabuğday`, `tvorog` to `lor
peyniri`. Trigram handles `Emmentaler` to `Emmental` and nothing harder.

Dense multilingual embeddings handle meaning across languages. Sparse and trigram matching
handle brands, barcodes, SKUs and rare entities that embeddings blur. Both live in one
Postgres through `pgvector` and `pg_trgm`, so no second datastore is required. (ADR-0024)

`product_search_docs` carries the two inputs deliberately separately:

| Column | Content | Consumer |
|---|---|---|
| `lexical_text` | Turkish-folded canonical name, brand, aliases | trigram |
| `semantic_text` | Unfolded natural language | embedding |

The Turkish fold (`ı İ ş ğ ç ö ü`) is lossy by design and correct for exact keys and
trigram. Applying it to embedding input strips the diacritics the model was trained on and
degrades retrieval. One fold function, applied identically on index and query side for
lexical matching only. Locale-naive `upper()` and `toUpperCase()` are banned by CI, because
the dotted and dotless i corrupts lexicon keys silently. (ADR-0025)

### Aliases

Aliases are an override layer, not the mechanism. Dense retrieval covers cross-lingual
matching at scale; aliases exist for what a web-trained model cannot know, which is
TRNC-only brands, private label, and regional names. Dozens of corrections, not thousands
of translations. (ADR-0037)

Four sources, in ascending cost:

1. **Lexicon entries.** Free. Every resolved receipt string is an alias by definition.
2. **Query mining.** A zero-result query followed within a session by a reformulation and
   a click is a labelled synonym pair. This is how large retailers build synonym
   dictionaries without anyone writing them. (ADR-0039)
3. **Contributor proposals.** A user who searched and failed is the cheapest source of the
   alias in their own language. Moderated through the same queue.
4. **Operator curation.** Ranked by logged zero-result volume per locale, so the backlog
   is demand-ordered rather than guessed.

## 6. Seeding

Scraped online catalogs seed product names, brands, pack sizes, categories, barcodes and
images, which removes the cold-start burden of typing a catalog by hand.

Seeded rows carry `source = 'scrape'` and `verification_state = 'unverified'`. A scraper's
spelling mistakes and category errors must be visibly distinct from operator-confirmed
ground truth, or you inherit them as fact. (ADR-0046)

Online sellers are also price sources, recorded as branches with `branch_kind = 'online'`
and no geometry. They appear in item lookup and price history but are excluded from
access-scoped basket comparison and from per-category chain indices, because an online
seller's pricing is not evidence about the physical market. (ADR-0045)

## 7. Collections

Dietary and national product sets (German staples, Russian staples, halal) exist as a join
table and nothing else. Different demographics want disjoint product sets, so the schema
needs to support it, but curating collections now would be guessing at demand for which no
signal exists. Query logs decide which are worth building. (ADR-0038)

## 8. Failure modes

| Failure | Consequence | Mitigation |
|---|---|---|
| Two canonical products for one real product | Split price history, both look sparse | Suggestion surfaces near-duplicates at creation; reversible merge |
| One canonical product for two real products | Comparison silently wrong | Net content and brand are required fields on `active` |
| Variable-weight barcode treated as identity | Thousands of phantom products | Prefix detection at ingest (ADR-0010) |
| Wrong lexicon entry | Every past and future observation for that key is misattributed | Entries are revisable; correction reprocesses rather than edits (ADR-0006) |
| Taxonomy restructure | Published category indices change meaning | `taxonomy_version` recorded on every index run |
| Fold applied to embedding input | Cross-lingual recall degrades quietly | Separate columns, separate code paths |
| Private label compared across chains | Basket index meaningless | `owner_chain_id` excluded from cross-chain comparison |
