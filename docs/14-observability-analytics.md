# 14. Observability and Analytics

Two distinct concerns. **System health** is whether the software works. **Data health** is
whether the corpus is any good. The second is the one that determines whether this project
succeeds, and it is the one conventional monitoring does not cover.

## 1. Logging

`structlog`, JSON, one event per line.

Every log line carries `request_id`, `actor_id` where an actor exists, and the module emitting
it. Worker jobs carry `submission_id` and `extraction_run_id`, which is what makes an extraction
failure traceable back to a specific image and forward to specific observations.

**Never logged**: phone numbers, OTP codes, tokens, signed URLs, raw capture coordinates, KEK
references, honeypot status, trust scores. Signed URLs matter particularly, because a log
aggregator turns a short-TTL credential into a durable one.

Log level is not the mechanism for hiding sensitive fields. Redaction happens at the structlog
processor, so a field cannot leak by someone raising verbosity during an incident.

## 2. Tracing

OpenTelemetry. The span that matters is the ingestion path, because it crosses three processes
and an external provider:

```
POST /v1/submissions
  -> enqueue extract
    -> worker: extraction provider call
    -> worker: reconciliation
    -> worker: crop generation
    -> worker: resolution
  -> observations written
```

Provider latency and cost per receipt are span attributes. They are the numbers that decide
whether the extraction choice is affordable, and guessing at them later is worse than recording
them from the start.

## 3. Errors

Sentry, with `request_id` correlation to logs. Release-tagged so a regression is attributable to
a deploy.

Client errors from Expo and both Next.js apps report to separate projects, since a crash in the
contributor app and a failure in the operator console need different responses.

## 4. System metrics

| Metric | Alert on |
|---|---|
| API latency p50, p95, p99 | p95 breach sustained |
| Error rate by endpoint | Any sustained increase |
| Queue depth by task type | Depth growing without drain |
| Extraction job duration and failure rate | Failure rate above threshold |
| Extraction cost per receipt | Drift above budget |
| Postgres connections, slow queries, replication lag | Standard thresholds |
| Redis memory and eviction | Eviction above zero, since it means rate limits and idempotency keys are being dropped |
| Storage bucket size and object count | Growth anomaly |
| OTP send volume and cost | Spike, which is both an abuse and a billing signal |

## 5. Data health

The part that matters most and the part that is easy to omit because nothing breaks when it
degrades.

| Metric | Why |
|---|---|
| Observations accepted per day | The headline throughput number |
| **Lexicon resolution rate** | Share of item lines resolving on first pass. The single best measure of whether normalization is scaling |
| Unresolved key backlog, and its age | If this grows faster than it drains, the bottleneck is winning |
| T1 queue depth and median time to resolution | Whether community review is actually working |
| Reconciliation balanced rate | A sudden drop means an extraction regression or a new POS layout, not fraud |
| Coverage by basket cell | Share of `(branch, product)` cells with an observation inside the staleness window |
| Staleness distribution p50, p90 | Freshness, which is half of coverage |
| Contributor concentration | Share of accepted observations from the top contributor. A high number is a sample-validity problem (ADR-0080) and a bus factor |
| Branch verification backlog | Unverified branches are excluded from every index |
| Zero-result search rate by locale | Drives the alias backlog (ADR-0039) |
| Review agreement rate | A falling rate means either the tasks or the reviewers are degrading |
| Honeypot pass rate | Direct measure of reviewer quality |
| Imputation share per index run | A figure resting largely on imputation is disclosed, and a rising trend is a coverage warning |

## 6. Data-health SLOs

Targets are placeholders until the corpus establishes a baseline. What matters is that each has
a defined response, not that the initial number is right.

| SLO | Response on breach |
|---|---|
| Lexicon resolution rate above target | Investigate new chain or POS layout; check for an extraction regression |
| Unresolved backlog draining faster than it fills | Raise T1 bounty multipliers; operator time to the queue |
| Reconciliation balanced rate above target | Suspect extraction regression before suspecting contributors |
| Basket coverage above the publication floor | Generate `empty_cell` bounties; suppress affected index values rather than publishing thin (ADR-0080) |
| Contributor concentration below threshold | Recruitment problem, not an engineering one. Escalate to a human decision |

The last one is deliberately not automatable. Concentration is the validity threat named in the
methodology, and no code change fixes it.

## 7. Analytics events

Product analytics, distinct from system telemetry, and subject to the same redaction rules.

| Event | Purpose |
|---|---|
| `capture.started`, `capture.completed`, `capture.abandoned` | Where the capture flow loses people |
| `queue.drained` with duration | Whether offline sync actually works in the field |
| `review.task_shown`, `review.answered`, `review.skipped` | Review UX, and which tiers people tolerate |
| `search.performed` with locale and result count | Feeds the alias backlog |
| `search.clicked` | Closes the loop for synonym mining |
| `basket.computed` | Whether the split basket is used |

Never events on receipt contents. Basket composition is exactly the sensitive inference surface
described in `12-security-compliance.md`, and it must not leak into an analytics pipeline by a
side door.

## 8. Audit as observability

`audit_log` is not a metrics store, but it answers questions nothing else can: who verified this
branch, who resolved this key, what did an operator see before an incident.

Retention outlives ordinary logs. An erased contributor's `actor_id` is tombstoned like any other
reference, but the record that a decision was made survives, because integrity in this system
rests on human decisions and those need a durable record.

## 9. Dashboards

Three, deliberately separate, because they are read by different people at different times.

**System.** Latency, errors, queue depth, resource use. Read during incidents.

**Data health.** Everything in section 5. Read weekly. This is the one that tells you whether
the project is working.

**Index quality.** Coverage, staleness, imputation share, per-category rank stability. Read
before publishing anything, and it is the evidence behind every published figure.
