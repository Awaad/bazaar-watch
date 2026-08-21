#!/usr/bin/env python3
"""Development seed. Local only, and idempotent.

The last Checkpoint A criterion, and more usefully the first thing that
exercises all 42 tables together. A constraint test checks one rule in
isolation; a seed has to satisfy every one of them at once and in order, which
is a different kind of check.

Everything here is **fixture data**. The coordinate was read off a map by a
developer, the barcodes are plausible rather than verified, and the Russian and
German category names want a second pair of eyes. None of it should be mistaken
for the output of `tools/geo-gen`, which is where real branch geometry comes
from with a licence attached. The environment guard below is what keeps this
distinction from mattering.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path("apps/api/src").resolve()))

from sqlalchemy import Connection, create_engine, text

from bazaarwatch.core.settings import Environment, get_settings
from bazaarwatch.core.text import slugify, turkish_fold

TAXONOMY_VERSION = 1

# tr and en are mine. ru and de are a best effort and are flagged in the README:
# a taxonomy version cannot be activated until all four are present, so they
# have to exist, but they should be reviewed by someone who speaks them.
CATEGORIES: tuple[tuple[str, str | None, dict[str, str]], ...] = (
    (
        "icecekler",
        None,
        {"tr": "İçecekler", "en": "Drinks", "ru": "Напитки", "de": "Getränke"},
    ),
    (
        "gazli-icecekler",
        "icecekler",
        {
            "tr": "Gazlı İçecekler",
            "en": "Carbonated drinks",
            "ru": "Газированные напитки",
            "de": "Kohlensäurehaltige Getränke",
        },
    ),
    (
        "atistirmalik",
        None,
        {"tr": "Atıştırmalık", "en": "Snacks", "ru": "Закуски", "de": "Snacks"},
    ),
    (
        "cikolata",
        "atistirmalik",
        {"tr": "Çikolata", "en": "Chocolate", "ru": "Шоколад", "de": "Schokolade"},
    ),
)


def _one(connection: Connection, sql: str, **params: Any) -> Any:
    return connection.execute(text(sql), params).scalar_one_or_none()


def _ensure(
    connection: Connection, table: str, key: str, value: str, insert: str, **params: Any
) -> uuid.UUID:
    """Fetch by natural key, or insert. This is what makes re-running safe."""
    existing = _one(connection, f"SELECT id FROM {table} WHERE {key} = :v", v=value)
    if existing is not None:
        return uuid.UUID(str(existing))
    return uuid.UUID(str(connection.execute(text(insert), params).scalar_one()))


def seed_identity(connection: Connection) -> uuid.UUID:
    """An operator, because verification is an act by a person.

    `verified_by_human` requires `verified_by` and `verified_at`, and the only
    user in a fresh database is the tombstone. The constraint forces the seed to
    name someone, which is the right way round.
    """
    return _ensure(
        connection,
        "users",
        "slug",
        "seed-operator",
        "INSERT INTO users (slug, display_name, role, locale) "
        "VALUES ('seed-operator', 'Seed Operator', 'operator', 'tr') RETURNING id",
    )


def seed_taxonomy(connection: Connection) -> dict[str, uuid.UUID]:
    connection.execute(
        text(
            "INSERT INTO taxonomy_versions (version, status, notes) "
            "VALUES (:v, 'draft', 'Development seed') ON CONFLICT (version) DO NOTHING"
        ),
        {"v": TAXONOMY_VERSION},
    )

    ids: dict[str, uuid.UUID] = {}
    for slug, _parent, names in CATEGORIES:
        ids[slug] = _ensure(
            connection,
            "categories",
            "slug",
            slug,
            # Serialised here rather than passed as a dict: psycopg will not
            # adapt one without a JSONB type hint, and the error names the
            # placeholder rather than the column.
            "INSERT INTO categories (slug, name_i18n) VALUES (:s, CAST(:n AS JSONB)) RETURNING id",
            s=slug,
            n=json.dumps(names, ensure_ascii=False),
        )

    # Parents before children, so the path trigger has something to build on.
    for slug, parent, _names in CATEGORIES:
        connection.execute(
            text(
                "INSERT INTO category_structure (category_id, taxonomy_version, parent_id) "
                "VALUES (:c, :v, :p) ON CONFLICT (category_id, taxonomy_version) DO NOTHING"
            ),
            {
                "c": ids[slug],
                "v": TAXONOMY_VERSION,
                "p": ids[parent] if parent else None,
            },
        )

    # Refused if any name is incomplete, or if the version is empty.
    status = _one(
        connection, "SELECT status FROM taxonomy_versions WHERE version = :v", v=TAXONOMY_VERSION
    )
    if status != "active":
        connection.execute(
            text(
                "UPDATE taxonomy_versions SET status = 'active', activated_at = now() "
                "WHERE version = :v"
            ),
            {"v": TAXONOMY_VERSION},
        )
    return ids


def seed_geo(connection: Connection, operator: uuid.UUID) -> dict[str, uuid.UUID]:
    """Two chains, three branches, chosen so the two scopes actually differ.

    Lemar split into Molto and Micro. Long-time residents still say Lemar and
    younger residents have never heard it, which is a live search problem this
    schema has nowhere to record: there is no chain alias table. See the README.
    """
    chains = {
        slug: _ensure(
            connection,
            "chains",
            "slug",
            slug,
            "INSERT INTO chains (slug, name) VALUES (:s, :n) RETURNING id",
            s=slug,
            n=name,
        )
        for slug, name in (("molto", "Molto"), ("micro", "Micro"))
    }

    branches: dict[str, uuid.UUID] = {}

    # Physical and verified: the only kind that reaches an index.
    branches["molto-dogankoy"] = _ensure(
        connection,
        "branches",
        "slug",
        "molto-dogankoy",
        "INSERT INTO branches "
        "(chain_id, slug, name, branch_kind, geom, address, city, source_provider, "
        " verified_by_human, verified_by, verified_at) "
        "VALUES (:c, :s, :n, 'physical', ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), "
        " :addr, 'Girne', 'manual', true, :op, now()) RETURNING id",
        c=chains["molto"],
        s="molto-dogankoy",
        n="Molto Doğanköy",
        lon=33.333695,
        lat=35.332378,
        addr="88JM+XF4, Doğanköy 99300",
        op=operator,
    )

    # Physical and unverified: present, and excluded from both scopes by
    # ADR-0023 until an operator looks at it.
    branches["micro-girne"] = _ensure(
        connection,
        "branches",
        "slug",
        "micro-girne",
        "INSERT INTO branches (chain_id, slug, name, branch_kind, geom, city, source_provider) "
        "VALUES (:c, :s, :n, 'physical', ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), "
        " 'Girne', 'manual') RETURNING id",
        c=chains["micro"],
        s="micro-girne",
        n="Micro Girne",
        lon=33.3190,
        lat=35.3410,
    )

    # Online and verified: in price history and item lookup, out of indices and
    # comparison. This is the row that makes the two selectables differ.
    branches["molto-online"] = _ensure(
        connection,
        "branches",
        "slug",
        "molto-online",
        "INSERT INTO branches "
        "(chain_id, slug, name, branch_kind, source_provider, verified_by_human, "
        " verified_by, verified_at) "
        "VALUES (:c, :s, :n, 'online', 'manual', true, :op, now()) RETURNING id",
        c=chains["molto"],
        s="molto-online",
        n="Molto Online",
        op=operator,
    )
    return {**chains, **branches}


def seed_catalog(
    connection: Connection, categories: dict[str, uuid.UUID], molto: uuid.UUID
) -> None:
    brands = {
        "coca-cola": _ensure(
            connection,
            "brands",
            "slug",
            "coca-cola",
            "INSERT INTO brands (slug, name) VALUES ('coca-cola', 'Coca-Cola') RETURNING id",
        ),
        "ferrero": _ensure(
            connection,
            "brands",
            "slug",
            "ferrero",
            "INSERT INTO brands (slug, name) VALUES ('ferrero', 'Ferrero') RETURNING id",
        ),
        # Private label, so ownership sits on the brand and nowhere else.
        "molto-secim": _ensure(
            connection,
            "brands",
            "slug",
            "molto-secim",
            "INSERT INTO brands (slug, name, is_private_label, owner_chain_id) "
            "VALUES ('molto-secim', 'Molto Seçim', true, :c) RETURNING id",
            c=molto,
        ),
    }

    products: dict[str, uuid.UUID] = {}
    # Each row is name, brand, category, net content, unit, basis and barcode.
    catalogue = (
        ("Coca-Cola 1 L", "coca-cola", "gazli-icecekler", 1, "l", "per_l", "8690572000011"),
        ("Coca-Cola 1.5 L", "coca-cola", "gazli-icecekler", 1.5, "l", "per_l", "8690572000028"),
        ("Kinder Bueno 43 g", "ferrero", "cikolata", 43, "g", "per_kg", "8000500037560"),
        ("Molto Seçim Su 5 L", "molto-secim", "icecekler", 5, "l", "per_l", None),
    )
    for name, brand, category, value, uom, basis, gtin in catalogue:
        slug = slugify(name)
        products[slug] = _ensure(
            connection,
            "products",
            "slug",
            slug,
            "INSERT INTO products "
            "(slug, canonical_name, brand_id, category_id, net_content_value, "
            " net_content_uom, unit_basis, source, verification_state) "
            "VALUES (:s, :n, :b, :c, :v, :u, :ub, 'operator', 'verified') RETURNING id",
            s=slug,
            n=name,
            b=brands[brand],
            c=categories[category],
            v=value,
            u=uom,
            ub=basis,
        )
        if gtin:
            connection.execute(
                text(
                    "INSERT INTO product_gtins (product_id, gtin, gtin_kind, is_primary) "
                    "VALUES (:p, :g, 'ean13', true) "
                    "ON CONFLICT (gtin, gtin_kind) WHERE gtin_kind <> 'chain_internal' "
                    "DO NOTHING"
                ),
                {"p": products[slug], "g": gtin},
            )

    # Substitution grouping: two sizes of one thing. Also the mechanism a
    # shopper comparison uses to include private label across chains.
    group = _ensure(
        connection,
        "product_groups",
        "slug",
        "kola",
        "INSERT INTO product_groups (slug, name) VALUES ('kola', 'Kola') RETURNING id",
    )
    for slug in ("coca-cola-1-l", "coca-cola-1-5-l"):
        connection.execute(
            text(
                "INSERT INTO product_group_members (group_id, product_id) VALUES (:g, :p) "
                "ON CONFLICT (group_id, product_id) DO NOTHING"
            ),
            {"g": group, "p": products[slug]},
        )

    for slug, facet in (
        ("molto-secim-su-5-l", "private_label"),
        ("kinder-bueno-43-g", "imported"),
    ):
        connection.execute(
            text(
                "INSERT INTO product_facets (product_id, facet) VALUES (:p, :f) "
                "ON CONFLICT (product_id, facet) DO NOTHING"
            ),
            {"p": products[slug], "f": facet},
        )

    connection.execute(
        text(
            "INSERT INTO product_aliases (product_id, locale, alias_text, source) "
            "VALUES (:p, 'tr', 'kola', 'operator') "
            "ON CONFLICT (product_id, locale, alias_text) DO NOTHING"
        ),
        {"p": products["coca-cola-1-l"]},
    )

    # Lexical is folded, semantic is not. The fold is right for trigram and
    # wrong for a model trained on natural diacritics (ADR-0025). No embedding:
    # the column is held empty until ADR-0024 pins a dimension.
    for slug, product_id in products.items():
        name = _one(connection, "SELECT canonical_name FROM products WHERE id = :p", p=product_id)
        connection.execute(
            text(
                "INSERT INTO product_search_docs (product_id, lexical_text, semantic_text) "
                "VALUES (:p, :lex, :sem) ON CONFLICT (product_id) DO NOTHING"
            ),
            {"p": product_id, "lex": turkish_fold(str(name)), "sem": str(name)},
        )
        del slug


def main() -> int:
    settings = get_settings()
    if settings.environment is not Environment.LOCAL:
        # A seed pointed at production is an accident worth making impossible
        # rather than unlikely.
        print(f"refusing to seed a {settings.environment.value} environment", file=sys.stderr)
        return 1

    engine = create_engine(str(settings.database_url))
    with engine.begin() as connection:
        operator = seed_identity(connection)
        categories = seed_taxonomy(connection)
        geo = seed_geo(connection, operator)
        seed_catalog(connection, categories, geo["molto"])
    engine.dispose()

    print("seeded: 1 operator, 1 taxonomy version, 4 categories, 2 chains, 3 branches, 4 products")
    return 0


if __name__ == "__main__":
    sys.exit(main())
