# 12. Security and Compliance

Posture is to minimise at ingest rather than remediate later, and to sever identity rather than
destroy facts on erasure (ADR-0031).

## 1. What is actually sensitive

Most of the corpus is not personal data. A shelf price is a fact about a shop. The sensitivity
is concentrated in a small number of places, and treating everything as sensitive would be both
useless and expensive.

| Asset | Why it matters |
|---|---|
| Receipt originals | One person's complete basket at one place and time. Card digits, loyalty numbers, occasionally staff or customer names. Baskets support inferences about health, religion, pregnancy and alcohol use, and a sequence of them is a movement pattern |
| Crops | Fragments of the above |
| Phone numbers | Direct identifier and the auth factor |
| Receipt-level grouping | A basket even after the contributor is severed (ADR-0085) |
| Location at capture | Consumed and discarded, never stored (ADR-0056) |
| Trust scores, honeypot status, integrity signals | Not personal data, but gameable if exposed |

Everything else, meaning observations, receipt lines viewed individually, catalog, branches and
index values, is not personal data once unlinked.

## 2. Erasure

Three tiers. (ADR-0071)

| Tier | Data | Treatment |
|---|---|---|
| A | Originals, crops, raw PII fields | Envelope encryption under a per-subject KEK; erasure destroys the KEK |
| B | Observations, receipt lines, ledger entries | Severed to the shared tombstone, retained in plaintext |
| C | Phone, credentials, sessions, push tokens | Deleted outright |

**Tier B is severed, not encrypted.** A shelf price is not personal data once unlinked, and
encrypting the corpus per contributor would destroy the aggregate queryability that is the
entire product.

Erasures are counted in `erasure_counters` by month, which carries no identifier, so the platform
knows how many people have left without knowing who.

**The tombstone is shared, not per-user.** A unique random identifier per erased contributor
keeps all their submissions mutually linkable, which reconstitutes a shopping profile. That is
pseudonymisation, which remains personal data, so the work would be done and the obligation
retained. One well-known `deleted-contributor` row dissolves the linkage. Erasures are counted
in `erasure_counters`, which carries no identifier. (ADR-0084)

## 3. Why crypto shredding

ADR-0069 mandates object lock and replication so the corpus cannot be lost. Locked objects
cannot be deleted before expiry, so ordinary deletion cannot satisfy an erasure request.

Versioning plus replication would permit real deletion and need no key store. The decisive
argument against it is evidentiary rather than architectural: **a destroyed key is
demonstrable**, whereas proving that every copy across every replica and every version was
reached is not. Erasure is an obligation that may have to be shown, not merely performed.
(ADR-0086)

Honest caveat: crypto shredding is widely accepted practice, but some supervisory authorities
have questioned whether strongly encrypted data with a destroyed key is fully erased. Recorded
as defensible, not guaranteed. (ADR-0074)

## 4. Key management

Envelope encryption. A data key per media object, wrapped by a key encrypting key per subject.
KEKs live in a key store separate from both the database and object storage.

**The loophole that will be created by accident**: if key store backups outlive the erasure SLA,
nothing was shredded. Somebody will configure sensible backups on the key store a year from now
and silently un-shred every past erasure, and no alarm will fire. Key store backup retention
must be shorter than the erasure SLA, this must appear in the backup runbook rather than only in
an ADR, and it is checked in the quarterly review. (ADR-0072)

**Crops share their original's subject key.** Shredding an original while crops persist retains
fragments of exactly the sensitive content. (ADR-0073)

Erasure consequently shrinks the extraction fine-tune corpus, since the images go while the
confirmed text labels survive severed. Accepted and stated rather than discovered later.
(ADR-0062)

## 5. Access control

| Role | Reach |
|---|---|
| `contributor` | Own submissions; assigned review tasks; public reads |
| `moderator` | Review adjudication; no originals |
| `operator` | Originals via short-TTL signed URL; catalog, lexicon, branch verification |
| `admin` | Above, plus user administration and erasure execution |

Operators and admins are the only roles that see PII and therefore require a second factor and
shorter sessions. Treating them as ordinary users behind a wider role check would leave the most
sensitive path the least protected. Every action they take writes to `audit_log`. (ADR-0083)

Authorization is enforced in the service layer, never in a route decorator alone, because the
same operation is reachable from more than one route.

`/v1/ops/*` is a separate endpoint group rather than a role check on shared routes, which makes
an authorization mistake structurally harder.

## 6. Capability isolation

The `api` process holds **no credential** for the originals bucket. Crops are generated in the
worker, which already has the original open during extraction. The API cannot leak an original
because it cannot reach one. (ADR-0063, ADR-0064)

| Process | `receipts-original` | `receipts-crop` |
|---|---|---|
| `api` | none | read |
| `worker` | read/write | write |

Server-side encryption at rest is enabled and is not the protection that matters, since the
provider decrypts transparently for any valid key. What protects the corpus is credential
scoping, rotation and bucket policy. (ADR-0066)

## 7. The three invariants that live in code

Not expressible as database constraints, all three privacy-relevant, all three requiring direct
adversarial tests rather than incidental coverage through feature tests. This is the thinnest
ice in the design.

| Invariant | Failure |
|---|---|
| A reviewer never receives a task tracing to their own submission or to a submitter they share history with (ADR-0048) | Collusion; validation becomes theatre |
| No more than one line from a given receipt goes to the same reviewer (ADR-0059) | Basket reconstruction |
| Submission detail endpoints check ownership before returning receipt-level grouping (ADR-0085) | The most common authorization bug there is, exposing another person's basket |

## 8. Retention

Blocked on local legal review, which gates the storage lifecycle policy and T3 review.

What is already decided regardless of the answer: originals are re-encoded on ingest so EXIF and
embedded GPS never persist (ADR-0068); capture location is derived and discarded (ADR-0056); T1
and T2 review expose no PII by construction, so community contribution does not wait on the
legal answer (ADR-0057).

## 9. Consent

Separable and explicit at signup: account creation, contribution and publication of derived
prices, optional location use at capture, optional participation in peer review.

Declining location does not block contribution; it removes one soft integrity signal. Declining
review participation does not affect submission rewards.

Contributors are told in plain language that reward is for **accepted and novel** contributions,
never for submissions, since fingerprint and phash dedupe are what make that promise enforceable.

## 10. Application security

| Concern | Control |
|---|---|
| Upload handling | Re-encode rather than trust; validate magic bytes; size caps |
| Rate limiting | Redis-backed per user and per IP; tightest on OTP request, submission and review task issue |
| OTP abuse | Per-phone and per-IP limits; OTP has direct SMS cost |
| SQL injection | Parameterised throughout; ORM or explicit bind parameters, never string interpolation |
| Secrets | Environment-injected at deploy, never committed, rotated on staff change |
| Dependencies | Lockfiles committed; automated vulnerability scanning in CI |
| Transport | TLS only; HSTS |
| Internal signals | Trust scores, honeypot status and integrity detail are never serialised to a contributor client |

## 11. Incident response

Detection through Sentry, integrity-signal anomalies, and rate-limit spikes.

A media exposure is the worst case and drives the response plan: identify affected subjects from
`media_objects.subject_user_id`, assess through `audit_log` what was actually accessed, notify
per the applicable regime, and rotate affected KEKs.

A leaked storage credential is the realistic threat, which is why credentials are scoped per
process and rotated rather than relying on encryption at rest to save the situation.

## 12. Open

| Question | Blocks |
|---|---|
| Retention window for originals | Lifecycle policy, T3 review |
| Applicable data protection regime in detail | Consent wording, notification timelines, assessment obligations |
| Legal basis for publishing branch-attributed prices | Nothing yet; prices are not personal data, but a small market may produce complaints regardless |
