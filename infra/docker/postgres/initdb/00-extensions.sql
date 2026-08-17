-- Extension bootstrap.
--
-- CREATE EXTENSION requires superuser. Making the application's database role a
-- superuser in production would be a bad trade, and managed Postgres commonly
-- forbids it outright. So extensions are created here, by the privileged
-- bootstrap, and Alembic migration 0001 asserts they exist rather than creating
-- them. Alembic remains the authority on schema; a missing extension surfaces at
-- migrate time with a clear message instead of at first query.
--
-- Runs once, on an empty data directory, against POSTGRES_DB.
-- See docs/03-data-model.md section 16 and docs/13-infra-devops.md.

CREATE EXTENSION IF NOT EXISTS postgis;    -- access-scoped comparison (ADR-0035)
CREATE EXTENSION IF NOT EXISTS vector;     -- hybrid retrieval (ADR-0024)
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- brands, SKUs, near-literal matches
CREATE EXTENSION IF NOT EXISTS ltree;      -- category tree (ADR-0009)
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- envelope encryption (ADR-0071)
