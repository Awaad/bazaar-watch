# ADR-0002: PostgreSQL 18 as the single datastore

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

The system needs relational integrity, geospatial filtering, vector similarity and
fuzzy text matching. Each of these has a specialised datastore that does it better in isolation.

Every additional stateful service is an additional thing to run, back up, monitor, restore and
keep synchronised, and synchronisation between stores is a recurring source of correctness bugs.

Scale is small: a few thousand products, tens of branches, thousands of receipts per month at
maturity.

## Decision

One PostgreSQL 18 database with PostGIS, pgvector, pg_trgm, ltree and pgcrypto.

Postgres 18 specifically for native `uuidv7()`, so database-side defaults produce the same
insert locality as application-generated identifiers (ADR-0003).

Alembic owns all DDL without exception. No table is created by application code and no column is
added by hand.

PostGIS is core rather than decorative, because access-scoped comparison makes geography a filter
on every basket read path (ADR-0035).

## Consequences

One thing to operate, back up and restore. One transaction boundary, so a
cross-domain write is atomic without distributed transaction machinery.

Postgres unavailability is a full outage. Accepted as a deliberate trade at this scale.

Testing must run against real Postgres via testcontainers. SQLite would silently misrepresent
PostGIS, pgvector, ltree, partial indexes, `CHECK` constraints and `NUMERIC` semantics, each of
which carries a correctness invariant here.

Vector index performance and geospatial query performance now share one resource envelope.

## Alternatives considered

**Elasticsearch for search.** Rejected in ADR-0024.

**A dedicated vector database.** Rejected. pgvector with HNSW is comfortable at a few thousand
products, and colocation removes a synchronisation problem.

**Postgres 16 or 17.** Rejected. Native `uuidv7()` in 18 removes the discrepancy between
application-generated and database-generated identifiers.

## Revisit trigger

Vector index build time exceeds the maintenance window, or geospatial and retrieval
workloads begin to contend measurably.
