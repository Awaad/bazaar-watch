# Postgres 18 with every extension the schema requires.
#
# Built rather than pulled, because "which pgvector is in this image" is not a
# question worth answering while a migration is failing. The HNSW index in
# ADR-0024 is version-sensitive, and PostGIS behaviour varies across minor
# versions in ways that surface as wrong results rather than errors.
#
# The official postgres image already configures the PGDG apt repository, so
# these packages come from the same source PostgreSQL itself does.

FROM postgres:18-bookworm

# pg_trgm, ltree and pgcrypto ship in postgresql-contrib, which the base image
# already carries. Only PostGIS and pgvector need adding.
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        postgresql-18-postgis-3 \
        postgresql-18-postgis-3-scripts \
        postgresql-18-pgvector \
    ; \
    rm -rf /var/lib/apt/lists/*

# Record what actually landed, so `docker image inspect` answers the version
# question without starting a container.
RUN set -eux; \
    postgis_ver="$(dpkg-query -W -f='${Version}' postgresql-18-postgis-3)"; \
    vector_ver="$(dpkg-query -W -f='${Version}' postgresql-18-pgvector)"; \
    printf 'postgis=%s\npgvector=%s\n' "$postgis_ver" "$vector_ver" \
        > /etc/bazaarwatch-extension-versions

LABEL org.opencontainers.image.title="bazaar-watch postgres" \
      org.opencontainers.image.description="Postgres 18 with postgis, pgvector, pg_trgm, ltree, pgcrypto"
