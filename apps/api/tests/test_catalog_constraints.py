"""Catalog constraint behaviour. Needs a database.

Every constraint added in this slice is here. The point of building the harness
first was that these are checked rather than asserted about rendered DDL.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DatabaseError

pytestmark = pytest.mark.integration

COMPLETE = '{"tr": "Ad", "en": "Name", "ru": "Imya", "de": "Name"}'


def _category(db: Connection) -> uuid.UUID:
    return db.execute(
        text("INSERT INTO categories (slug, name_i18n) VALUES ('food', :n) RETURNING id"),
        {"n": COMPLETE},
    ).scalar_one()


def _chain(db: Connection) -> uuid.UUID:
    return db.execute(
        text("INSERT INTO chains (slug, name) VALUES ('lemar', 'Lemar') RETURNING id")
    ).scalar_one()


def _brand(db: Connection, slug: str = "ulker", **kwargs: object) -> uuid.UUID:
    private = bool(kwargs.get("private", False))
    owner = kwargs.get("owner")
    return db.execute(
        text(
            "INSERT INTO brands (slug, name, is_private_label, owner_chain_id) "
            "VALUES (:s, 'B', :p, :o) RETURNING id"
        ),
        {"s": slug, "p": private, "o": owner},
    ).scalar_one()


def _product(db: Connection, category: uuid.UUID, slug: str = "p1", **kwargs: object) -> uuid.UUID:
    columns = ", ".join(kwargs)
    values = ", ".join(f":{k}" for k in kwargs)
    extra_columns = f", {columns}" if columns else ""
    extra_values = f", {values}" if values else ""
    sql = (
        f"INSERT INTO products (slug, canonical_name, category_id{extra_columns}) "
        f"VALUES (:slug, 'N', :cat{extra_values}) RETURNING id"
    )
    return db.execute(text(sql), {"slug": slug, "cat": category, **kwargs}).scalar_one()


def test_a_brand_owner_without_private_label_is_refused(db: Connection) -> None:
    """The converse of the documented rule. An owner on a brand that is not
    private label claims a chain relationship the private-label rules will
    never apply."""
    chain = _chain(db)
    with pytest.raises(DatabaseError, match="owner_implies_private_label"):
        _brand(db, private=False, owner=chain)


def test_private_label_without_an_owner_is_refused(db: Connection) -> None:
    with pytest.raises(DatabaseError, match="private_label_has_owner"):
        _brand(db, private=True, owner=None)


def test_products_do_not_carry_an_owner_chain(db: Connection) -> None:
    """Private label is a property of the brand and was recorded twice. Two
    places for one fact is two places that can disagree."""
    columns = db.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name = 'products'")
    ).scalars()
    assert "owner_chain_id" not in set(columns)


def test_a_weight_basis_without_net_content_is_refused(db: Connection) -> None:
    """A per-kilogram basis with no net content is a unit price that cannot be
    computed, and unit price is what comparison ranks on."""
    category = _category(db)
    with pytest.raises(DatabaseError, match="unit_basis_needs_net_content"):
        _product(db, category, unit_basis="per_kg")


def test_a_weight_basis_with_net_content_is_accepted(db: Connection) -> None:
    category = _category(db)
    _product(db, category, unit_basis="per_kg", net_content_value=1.5, net_content_uom="kg")


def test_a_piece_basis_needs_no_net_content(db: Connection) -> None:
    """The default, and the common case for a countable item."""
    category = _category(db)
    _product(db, category, unit_basis="per_piece")


def test_a_zero_or_negative_net_content_is_refused(db: Connection) -> None:
    category = _category(db)
    with pytest.raises(DatabaseError, match="net_content_is_positive"):
        _product(db, category, unit_basis="per_kg", net_content_value=0, net_content_uom="kg")


def test_an_unknown_unit_of_measure_is_refused(db: Connection) -> None:
    category = _category(db)
    with pytest.raises(DatabaseError, match="uom_known_if_present"):
        _product(db, category, unit_basis="per_kg", net_content_value=1, net_content_uom="oz")


def test_a_live_product_carrying_a_merge_target_is_refused(db: Connection) -> None:
    """The biconditional. Without the second direction a product can be active
    and point at its own replacement, and lookups follow it."""
    category = _category(db)
    target = _product(db, category, "p1")
    with pytest.raises(DatabaseError, match="merged_iff_target"):
        _product(db, category, "p2", status="active", merged_into_id=target)


def test_a_merged_product_without_a_target_is_refused(db: Connection) -> None:
    category = _category(db)
    with pytest.raises(DatabaseError, match="merged_iff_target"):
        _product(db, category, "p2", status="merged")


def test_a_product_cannot_be_merged_into_itself(db: Connection) -> None:
    """Following the merge chain has to terminate."""
    category = _category(db)
    product = _product(db, category, "p1")
    with pytest.raises(DatabaseError, match="not_merged_into_itself"):
        db.execute(
            text("UPDATE products SET status = 'merged', merged_into_id = id WHERE id = :p"),
            {"p": product},
        )


def test_only_one_primary_code_per_product(db: Connection) -> None:
    """Without this, the barcode to print is a question with several answers
    and no way to choose."""
    category = _category(db)
    product = _product(db, category)
    db.execute(
        text(
            "INSERT INTO product_gtins (product_id, gtin, gtin_kind, is_primary) "
            "VALUES (:p, '111', 'ean13', true)"
        ),
        {"p": product},
    )
    with pytest.raises(DatabaseError, match="uq_product_gtins_primary"):
        db.execute(
            text(
                "INSERT INTO product_gtins (product_id, gtin, gtin_kind, is_primary) "
                "VALUES (:p, '222', 'ean13', true)"
            ),
            {"p": product},
        )


def test_several_non_primary_codes_are_allowed(db: Connection) -> None:
    """The index is partial. A product legitimately carries many codes."""
    category = _category(db)
    product = _product(db, category)
    for code in ("111", "222", "333"):
        db.execute(
            text(
                "INSERT INTO product_gtins (product_id, gtin, gtin_kind) VALUES (:p, :g, 'ean13')"
            ),
            {"p": product, "g": code},
        )
    count = db.execute(text("SELECT count(*) FROM product_gtins")).scalar_one()
    assert count == 3


def test_a_global_code_belongs_to_one_product(db: Connection) -> None:
    category = _category(db)
    first = _product(db, category, "p1")
    second = _product(db, category, "p2")
    db.execute(
        text("INSERT INTO product_gtins (product_id, gtin, gtin_kind) VALUES (:p, '111', 'ean13')"),
        {"p": first},
    )
    with pytest.raises(DatabaseError, match="uq_product_gtins_global"):
        db.execute(
            text(
                "INSERT INTO product_gtins (product_id, gtin, gtin_kind) "
                "VALUES (:p, '111', 'ean13')"
            ),
            {"p": second},
        )


def test_chain_internal_codes_collide_across_chains_without_complaint(db: Connection) -> None:
    """They are not a global namespace, which is the whole reason they are
    scoped to a chain."""
    category = _category(db)
    product = _product(db, category)
    first = _chain(db)
    second = db.execute(
        text("INSERT INTO chains (slug, name) VALUES ('bim', 'BIM') RETURNING id")
    ).scalar_one()
    for chain in (first, second):
        db.execute(
            text(
                "INSERT INTO product_gtins (product_id, gtin, gtin_kind, chain_id) "
                "VALUES (:p, '5001', 'chain_internal', :c)"
            ),
            {"p": product, "c": chain},
        )
    count = db.execute(text("SELECT count(*) FROM product_gtins")).scalar_one()
    assert count == 2


def test_a_chain_internal_code_without_a_chain_is_refused(db: Connection) -> None:
    category = _category(db)
    product = _product(db, category)
    with pytest.raises(DatabaseError, match="internal_gtin_is_chain_scoped"):
        db.execute(
            text(
                "INSERT INTO product_gtins (product_id, gtin, gtin_kind) "
                "VALUES (:p, '5001', 'chain_internal')"
            ),
            {"p": product},
        )


def test_an_unknown_alias_locale_is_refused(db: Connection) -> None:
    """An unconstrained column accumulates `TR`, `tr-CY` and `turkish`, and
    lexicon resolution matches on it."""
    category = _category(db)
    product = _product(db, category)
    with pytest.raises(DatabaseError, match="locale_known"):
        db.execute(
            text(
                "INSERT INTO product_aliases (product_id, locale, alias_text, source) "
                "VALUES (:p, 'tr-CY', 'sut', 'operator')"
            ),
            {"p": product},
        )


def test_an_over_long_alias_is_refused_by_length_not_by_the_index(db: Connection) -> None:
    """Unbounded text inside a unique index fails at insert with an index size
    error, which says nothing about what the caller did wrong."""
    category = _category(db)
    product = _product(db, category)
    with pytest.raises(DatabaseError, match=r"too long|value too long"):
        db.execute(
            text(
                "INSERT INTO product_aliases (product_id, locale, alias_text, source) "
                "VALUES (:p, 'tr', :a, 'operator')"
            ),
            {"p": product, "a": "x" * 300},
        )


def test_an_embedding_cannot_be_written_yet(db: Connection) -> None:
    """ADR-0024 leaves the dimension unpinned, and an unpinned `vector` accepts
    768 beside 1024 with no error. The pinning migration drops this constraint
    in the same change that sets the dimension."""
    category = _category(db)
    product = _product(db, category)
    with pytest.raises(DatabaseError, match="embedding_is_unset"):
        db.execute(
            text(
                "INSERT INTO product_search_docs "
                "(product_id, lexical_text, semantic_text, embedding, model_version) "
                "VALUES (:p, 'a', 'b', '[1,2,3]', 'test')"
            ),
            {"p": product},
        )


def test_a_model_version_without_an_embedding_is_refused(db: Connection) -> None:
    """A placeholder in a NOT NULL column is a lie the schema tells, which is
    why this is nullable and paired instead."""
    category = _category(db)
    product = _product(db, category)
    with pytest.raises(DatabaseError, match="model_version_iff_embedding"):
        db.execute(
            text(
                "INSERT INTO product_search_docs "
                "(product_id, lexical_text, semantic_text, model_version) "
                "VALUES (:p, 'a', 'b', 'test')"
            ),
            {"p": product},
        )


def test_a_search_doc_with_no_embedding_is_accepted(db: Connection) -> None:
    """The lexical half is usable now. Retrieval does not have to wait for a
    model to be chosen."""
    category = _category(db)
    product = _product(db, category)
    db.execute(
        text(
            "INSERT INTO product_search_docs (product_id, lexical_text, semantic_text) "
            "VALUES (:p, 'sut urunleri', 'Süt Ürünleri')"
        ),
        {"p": product},
    )


def test_facets_are_an_open_set(db: Connection) -> None:
    """No CHECK, deliberately. Adding a facet should not be a migration."""
    category = _category(db)
    product = _product(db, category)
    for facet in ("halal", "organic", "something_new"):
        db.execute(
            text("INSERT INTO product_facets (product_id, facet) VALUES (:p, :f)"),
            {"p": product, "f": facet},
        )
    count = db.execute(text("SELECT count(*) FROM product_facets")).scalar_one()
    assert count == 3


def test_a_collection_without_a_turkish_name_is_refused(db: Connection) -> None:
    with pytest.raises(DatabaseError, match="has_turkish_name"):
        db.execute(
            text(
                "INSERT INTO collections (slug, name_i18n) VALUES ('vegan', '{\"en\": \"Vegan\"}')"
            )
        )
