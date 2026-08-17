# 10. Geo Registry

Branches are where prices attach. Access-scoped comparison makes every basket read a geographic
query, so a wrong pin corrupts results rather than merely misplacing a dot. (ADR-0035)

## 1. Two separate decisions

Frequently conflated, and only one is a cost question. (ADR-0044)

**Tile rendering** (MapLibre, Mapbox, Protomaps) is swappable behind an interface and chosen on
cost and appearance.

**POI data** is not swappable, because commercial places APIs restrict storage. Google Places
imposes caching and retention limits and prohibits using place data outside a Google map;
Mapbox Search carries similar storage restrictions. Building a branch registry on either means
renting your own table, which evaporates if you stop paying or if terms change.

## 2. Provider: Overture Places

Chosen for **ownership**, not coverage. Places is published under CDLA Permissive 2.0 and Apache
2.0, contains no OpenStreetMap data, and carries no share-alike obligation, so the derived branch
registry is genuinely yours. (ADR-0022)

Coverage is also better. Measured on the Kyrenia harbour bounding box:

| | OSM | Overture |
|---|---|---|
| POIs | 139 | 639 |
| Named | 67.6% | 100% |

Two constraints that must not be relaxed casually:

**Places only.** The buildings and transportation themes include OSM data and are ODbL. Pulling
them into the same derived database raises a share-alike question over a commercial price
dataset. Any OSM-derived data stays in separate files with its own attribution.

**Foursquare-sourced records** within Places carry Apache 2.0 and their own terms rather than
CDLA. Filter on the `source` property if a purely CDLA dataset is wanted. This is a one-line
decision that is much cheaper to make now than to unpick later.

## 3. Pipeline

```
bbox -> extract -> ir -> classify -> branch_candidates
```

**extract** queries the provider and caches raw response bytes under a deterministic key
(provider, endpoint, query hash) with a manifest. Re-runs are cache hits, rate limits are
respected, and the raw bytes remain auditable.

**ir** normalises to a provider-agnostic form carrying `source_id` as `provider:id`. Every
collection is sorted on normalise, so output is deterministic and diffs are meaningful.

**classify** maps provider categories to grocery retail roles from a config file, with a guard
that raises if two roles claim the same category rather than silently resolving it.

**Output is `branch_candidates`, never `branches`.** Separate table, not a boolean flag on the
live table, because mixing unverified pipeline rows into the priced table invites accidental use.

Re-runs upsert on `(source_provider, source_id)`, so the pipeline is idempotent.

## 4. Name locale

TRNC place naming in open data is politically contested and inconsistent: Girne and Kyrenia,
Lefkoşa and Nicosia and Lefkosia, with `name:tr`, `name:el` and `name:en` variants populated
unevenly.

The IR applies an explicit locale policy rather than taking whatever sits in `name`. Turkish
preferred, English fallback, others recorded but not promoted. Recorded as policy because the
default behaviour of every mapping tool is to silently pick one.

## 5. Verification

No price attaches to a branch with `verified_by_human = FALSE`. (ADR-0023)

Open data will contain closed stores, wrong pins, cross-provider duplicates, and outright
absences. Two provider fields reduce the manual burden materially:

- `operating_status`: open, temporarily closed, permanently closed. Candidates that are not open
  are deprioritised rather than promoted.
- `confidence`: a per-record score carried into `source_confidence`.

The operator promotes a candidate by confirming chain, name, geometry and address, which writes
`verified_by`, `verified_at`, and an `audit_log` row.

**Manual entry is expected and is not a fallback.** For thirty branches in one city, typing them
is faster than building and tuning a pipeline. The pipeline earns its place when expanding to a
new city or auditing for closures, not on day one.

Whether Overture knows where supermarkets are in residential Girne and Lefkoşa remains an open
question. The harbour bounding box contains zero grocery categories, which is expected for a
tourist district but tells us nothing about residential coverage.

## 6. Deduplication

Candidates arrive duplicated across providers and within one provider across updates. Matching is
by proximity plus name similarity under the Turkish fold, surfaced to an operator ranked by
confidence.

Merging is an operator action. A rejected candidate is marked `duplicate` with a reference to the
survivor, never deleted, so a re-run does not resurrect it.

## 7. Locationless branches

Online sellers are real price sources with no geometry. `branch_kind = 'online'`, `geom` null,
enforced by check constraints in both directions. (ADR-0045)

They appear in item lookup and price history. They are excluded from access-scoped basket
comparison, because reachability is meaningless for them, and from per-category chain indices,
because an online seller's pricing is not evidence about the physical market.

## 8. Access scoping

A cheap branch the user cannot reach is worth nothing. Uruluk being cheapest is irrelevant from
İskele.

Comparison is filtered to a reachable set before ranking, never ranked globally and filtered
afterwards, which would produce a recommendation the user cannot act on and then hide it.

Reachability is initially a radius via PostGIS `ST_DWithin` on the geography column with a GIST
index. Radius is a crude proxy for travel time and will eventually want an isochrone, but a
radius is correct enough at city scale and requires no routing dependency.

This is why PostGIS is core rather than decorative: geography is a filter on every basket read
path, not a map feature.

## 9. Failure modes

| Failure | Behaviour |
|---|---|
| Provider unavailable | Cached bytes serve; discovery is never on a request path |
| Category not in the role config | Candidate flagged `pending` with the raw category recorded, never silently dropped |
| Branch geometry wrong | Access-scoped comparison silently degrades. Mitigated only by verification, which is why it gates pricing |
| Branch closes | `operating_status` on re-run flags it; observations remain, comparison excludes it |
| Two branches at one address | Operator dedupe; the shopping-centre case is the common one and GPS cannot resolve it |
