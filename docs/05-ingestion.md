# 05. Ingestion

Capture to observation. Every fact in the system enters here, so the guarantees in this
document are the ones everything downstream inherits.

## 1. Capture paths

| Path | Yield | Notes |
|---|---|---|
| Receipt photo | 20 to 40 attributed, timestamped, arithmetically checkable observations | Primary. Covers produce and bakery carrying no barcode |
| Barcode scan | 1 | Same `price_observation` with a different `source_kind`. Supported day one, not retrofitted (ADR-0012) |
| Manual shelf entry | 1 | For items with no scannable code |
| Scrape | Many | Online sellers, recorded against `branch_kind = 'online'` |

All four converge on `price_observations`. Nothing downstream branches on how a price was
captured except where provenance is explicitly relevant.

## 2. Offline queue

Supermarket interiors have poor signal. The app treats every capture as durable local state
first and a network operation second. (ADR-0015)

`expo-sqlite`, not AsyncStorage. A queue needs transactions, ordering and survival across
force-quit.

Each queued item carries a `client_idempotency_key` generated at capture time. It is a v4
token and never a primary key, because a device with a skewed clock would generate a
UUIDv7 whose embedded timestamp destroys the insert locality that justified choosing v7.
(ADR-0003)

Sync is at-least-once. Retry with exponential backoff and jitter. A partially uploaded
media object is resumed or restarted; a confirmed one is never re-uploaded, because the
content hash makes the duplicate detectable server-side.

The queue drains on connectivity, on foreground, and on user request. It never blocks
capture.

## 3. Upload

Two-phase, direct to object storage. Multi-megabyte uploads through the API tie up request
workers and interact badly with retries. (ADR-0070)

```
POST /v1/media/upload-slot   -> media_id, presigned PUT url, expires_at
PUT  <presigned url>         -> direct to receipts-original
POST /v1/media/{id}/confirm  -> content_hash
```

On confirm the server:

1. Verifies the object exists and matches the declared size.
2. Verifies the content hash.
3. **Re-encodes the image.** Never stores the upload verbatim. This strips EXIF, normalises
   format, and neutralises malformed-image parser exploits in one step. EXIF matters
   specifically because it can carry GPS, and storing it would retain the precise
   coordinate that ADR-0054 exists to discard. (ADR-0068)
4. Wraps a fresh data key under the contributor's subject KEK and stores `wrapped_dek`.
   (ADR-0071)
5. If the content hash already exists with `role = 'original'`, **links to the existing
   object rather than erroring.** Identical bytes are an identical image, and an offline
   retry or an honestly duplicated photo must not fail the submission.

## 4. Submission

```
POST /v1/submissions
  Idempotency-Key: <client_idempotency_key>
  { kind, claimed_branch_id, captured_at, media_ids, capture_location? }
```

`capture_location` is a single foreground fix at the moment of capture. There is no background
tracking and no location history; peer review targeting uses prior contributions at that branch,
already recorded in `submissions`, which is strictly less invasive for the same result (ADR-0053).

It is consumed and discarded. The server computes whether the position was
within the threshold distance of the claimed branch, stores `location_matched` and
`location_confidence`, and never persists the coordinate. Every consuming feature needs only
the derived signal, so this costs nothing functionally and collapses breach exposure,
retention obligation and assessment burden. (ADR-0056)

Location is a soft signal (ADR-0055). Indoor GPS commonly degrades to 50 to 100 metres and cannot
separate adjacent units in a shopping centre, and mock location is a developer-settings
toggle. It contributes to the integrity score and never blocks a submission. (ADR-0057)

The submission returns as soon as it is durably recorded. Extraction is asynchronous.

## 5. Extraction

Runs in the Celery worker, never in the API process. Model dependencies are multi-gigabyte
and the workload is CPU-bound and batch-friendly. (ADR-0043)

Every extraction opens an `extraction_runs` row. A second extraction of the same submission
marks the previous run superseded and moves its observations to `superseded` in the same
transaction. Without this, reprocessing double-counts and the entire
improve-the-model-and-reprocess strategy is unimplementable. (ADR-0082)

The provider emits, per line:

| Field | Purpose |
|---|---|
| `raw_text` | Verbatim. Immutable. Feeds the lexicon key and trigram. |
| `interpreted_text` | Expanded to natural language. Feeds the embedding, because `CC KOLA 1LT PET` is not a sentence. |
| `bbox` | Required for T2 cropped review. A hard provider selection criterion. |
| `sku_text` | Where the POS prints a code. The superior lexicon key. |
| quantity, uom, unit price, line total | |
| `line_kind` | item, discount, subtotal, tax, tender, unknown |

Discount lines carry `modifies_line_id` linking them to the item they adjust. Tender lines
are payment and are never products, but they must be captured or the document cannot be
audited.

## 6. Reconciliation

**TRNC receipts are KDV-inclusive.** Printed line prices already contain the tax, and the
KDV line is an informational breakdown. Treating it as an addend makes every healthy receipt
fail, disabling the strongest integrity signal in the system. (ADR-0081)

```
residual = printed_total - ( sum(item lines) - sum(discount lines) )
```

| Residual | `reconciliation_status` | Consequence |
|---|---|---|
| Zero | `balanced` | Strong positive signal |
| Non-zero | `residual` | Flagged, targeted T2 tasks created |
| Cannot parse a total | `unparseable` | Operator queue |

A residual is a **pointer, not a rejection**. Lines are still stored. Where the residual is
a round figure such as exactly 1.00, candidate lines are ranked by which single digit flip
would close the gap, which is the most precise review-routing signal available and it costs
nothing. (ADR-0058)

## 7. Crop generation

Crops are generated in the worker, which already has the original open, and written to
`receipts-crop`. The API therefore holds no credential for the originals bucket at all.
Isolation by capability rather than by check. (ADR-0064)

Crops share the subject KEK of their original, because shredding an original while its crops
persist would retain fragments of exactly the sensitive content. (ADR-0073)

Crops are generated for lines routed to review, not for every line. Routing is decided within the
extraction job itself, using the reconciliation residual and the other signals in ADR-0058, so crop
generation remains a single pass during extraction and is never an on-demand read of the original
(ADR-0064).

## 8. Resolution

```
for each line where line_kind = 'item':
    key_kind, key = ('sku', sku_text) if sku_text else ('raw_text', turkish_fold(raw_text))
    entry = chain_lexicon.lookup(chain_id, key_kind, key)   # exact match, active only
    if entry:
        observation.product_id = entry.product_id
    else:
        observation.product_id = NULL
        upsert T1 review task, priority = count of observations blocked by this key
```

Unresolved observations are stored, not discarded. They are real facts that cannot yet enter
an index.

When a lexicon entry is created, a job repoints every existing observation carrying that key.
Resolution is retroactive by design: the first receipt from a chain is fully manual, the
fiftieth is nearly automatic. (ADR-0008)

`unit_price_minor` is derived at this point from quantity, unit of measure and the product's
`unit_basis`. It is what makes 500g and 750g packs comparable, and comparison is the product.
It is derived, never submitted.

## 9. Branch resolution

An observation requires a branch. Three cases:

- **Claimed branch verified**: proceed.
- **Claimed branch unverified**: observations are created and excluded from indices and from
  access-scoped comparison until verification. A mis-pinned branch corrupts comparisons
  rather than merely showing a wrong dot. (ADR-0023)
- **No branch determinable**: submission holds at `extracted` in the operator queue.
  Observations are not created, since `price_observations.branch_id` is `NOT NULL`.

## 10. Acceptance

```
pending -> provisional -> accepted
   |            |            |
   +--> flagged +--> flagged +--> superseded
```

`provisional` is granted by peer review so a contributor is not left in silence for days.
Final adjudication confirms it or triggers a compensating ledger entry. (ADR-0050)

`flagged` never means deleted. A flagged observation stays in the corpus and is excluded only
from published figures. (ADR-0033)

## 11. Failure handling

| Failure | Behaviour |
|---|---|
| Extraction provider down | Submission holds at `received`, job retries with backoff. The original is durable; nothing is lost |
| Provider returns no bounding boxes | Lines stored, T2 unavailable for that receipt, T1 unaffected. Review degrades rather than fails |
| Duplicate fingerprint or perceptual hash | Receipt marked `duplicate`, no observations, no points. Nothing deleted; the submission remains as evidence |
| Reconciliation residual | Flagged, lines stored, targeted T2 tasks created |
| Storage unreachable | Upload slot fails fast with `503`; the client queue retries |
| Extraction produces zero item lines | Operator queue. Usually a photo of something that is not a receipt |

Every job is idempotent and keyed on `(submission_id, extraction_method, extraction_version)`,
so a retried extraction either produces the same run or a new one, never a partial duplicate.

## 12. Reprocessing

The reason originals are retained, replicated and object-locked. (ADR-0069)

When a provider or version improves, a backfill opens new `extraction_runs` against stored
originals. Previous runs are superseded, their observations moved to `superseded`, and the
new run's observations written in the same transaction.

Erased contributors' media cannot be reprocessed, since the subject key is destroyed. Their
existing observations remain, severed to the shared tombstone. (ADR-0084)
