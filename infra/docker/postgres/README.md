# Postgres image

Postgres 18 with PostGIS, pgvector, pg_trgm, ltree and pgcrypto.

Built rather than pulled. A prebuilt image would leave extension versions to
chance, and both the HNSW index (ADR-0024) and PostGIS behave differently across
versions in ways that produce wrong results rather than errors.

## Why 18

Native `uuidv7()`, so database-side defaults produce the same insert locality as
application-generated identifiers. See ADR-0003.

## Extension bootstrap

`initdb/00-extensions.sql` runs once, against an empty data directory, as
superuser.

Extensions are **not** created by Alembic. `CREATE EXTENSION` needs superuser,
and granting that to the application role in production is not acceptable.
Migration 0001 asserts the extensions are present and fails with a clear message
if they are not, which keeps Alembic authoritative over schema while leaving the
privileged step privileged.

Changing this file does nothing to an existing volume. Run `make db-reset`.

## Resolved versions

The build records what apt actually installed:

```bash
docker compose exec postgres cat /etc/bazaarwatch-extension-versions
make db-versions     # same, plus what the server reports
```

Worth checking after any rebuild. The Dockerfile pins package names, not package
versions, so a rebuild months later can pick up a newer PostGIS or pgvector.
Pinning apt versions exactly would break the build the moment PGDG rotates them,
which is a worse failure than a visible drift.
