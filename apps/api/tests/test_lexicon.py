"""Lexicon resolution and its constraints. Needs a database."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DatabaseError

from bazaarwatch.modules.lexicon.service import resolution_query

pytestmark = pytest.mark.integration

COMPLETE = '{"tr": "Ad", "en": "Name", "ru": "Imya", "de": "Name"}'


def _fixtures(db: Connection) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """A chain, a product and an operator: the three things an entry needs."""
    chain = db.execute(
        text("INSERT INTO chains (slug, name) VALUES ('molto', 'Molto') RETURNING id")
    ).scalar_one()
    category = db.execute(
        text("INSERT INTO categories (slug, name_i18n) VALUES ('food', :n) RETURNING id"),
        {"n": COMPLETE},
    ).scalar_one()
    product = db.execute(
        text(
            "INSERT INTO products (slug, canonical_name, category_id) "
            "VALUES ('sut-1l', 'Süt 1 L', :c) RETURNING id"
        ),
        {"c": category},
    ).scalar_one()
    operator = db.execute(
        text("INSERT INTO users (slug, role) VALUES ('op', 'operator') RETURNING id")
    ).scalar_one()
    return chain, product, operator


def _entry(
    db: Connection,
    chain: uuid.UUID,
    product: uuid.UUID,
    operator: uuid.UUID,
    *,
    kind: str,
    value: str,
    **kwargs: object,
) -> uuid.UUID:
    return db.execute(
        text(
            "INSERT INTO chain_lexicon "
            "(chain_id, key_kind, key_value, product_id, decided_by, decided_via, status) "
            "VALUES (:c, :k, :v, :p, :o, :via, :st) RETURNING id"
        ),
        {
            "c": chain,
            "k": kind,
            "v": value,
            "p": product,
            "o": operator,
            "via": kwargs.get("via", "operator"),
            "st": kwargs.get("status", "active"),
        },
    ).scalar_one()


def test_a_folded_description_resolves(db: Connection) -> None:
    chain, product, operator = _fixtures(db)
    _entry(db, chain, product, operator, kind="raw_text", value="sut tam yagli 1lt")
    # The caller passes what the receipt printed. Folding happens inside.
    found = db.execute(resolution_query(chain, raw_text="SÜT TAM YAĞLI 1LT")).scalar_one()
    assert found == product


def test_an_sku_resolves(db: Connection) -> None:
    chain, product, operator = _fixtures(db)
    _entry(db, chain, product, operator, kind="sku", value="100234")
    assert db.execute(resolution_query(chain, sku="100234")).scalar_one() == product


def test_the_sku_wins_when_a_line_carries_both(db: Connection) -> None:
    """ADR-0008 makes raw text the fallback. Ordering is what makes it one
    rather than a race between two equally valid rows."""
    chain, product, operator = _fixtures(db)
    other = db.execute(
        text(
            "INSERT INTO products (slug, canonical_name, category_id) "
            "SELECT 'sut-2l', 'Süt 2 L', category_id FROM products LIMIT 1 RETURNING id"
        )
    ).scalar_one()
    _entry(db, chain, product, operator, kind="sku", value="100234")
    _entry(db, chain, other, operator, kind="raw_text", value="sut tam yagli 1lt")

    found = db.execute(
        resolution_query(chain, sku="100234", raw_text="SÜT TAM YAĞLI 1LT")
    ).scalar_one()
    assert found == product


def test_an_unmapped_line_resolves_to_nothing(db: Connection) -> None:
    """Zero rows is the normal unresolved case. It creates a review task, not
    an exception."""
    chain, _product, _operator = _fixtures(db)
    assert db.execute(resolution_query(chain, raw_text="bilinmeyen")).scalar_one_or_none() is None


def test_resolution_does_not_cross_chains(db: Connection) -> None:
    """The same printed string means different things in different shops, which
    is the entire reason the lexicon is chain-scoped (ADR-0008)."""
    chain, product, operator = _fixtures(db)
    other_chain = db.execute(
        text("INSERT INTO chains (slug, name) VALUES ('micro', 'Micro') RETURNING id")
    ).scalar_one()
    _entry(db, chain, product, operator, kind="raw_text", value="sut tam yagli 1lt")

    found = db.execute(
        resolution_query(other_chain, raw_text="SÜT TAM YAĞLI 1LT")
    ).scalar_one_or_none()
    assert found is None


def test_a_superseded_entry_does_not_resolve(db: Connection) -> None:
    chain, product, operator = _fixtures(db)
    _entry(
        db,
        chain,
        product,
        operator,
        kind="raw_text",
        value="sut tam yagli 1lt",
        status="superseded",
    )
    assert (
        db.execute(resolution_query(chain, raw_text="sut tam yagli 1lt")).scalar_one_or_none()
        is None
    )


def test_resolution_needs_something_to_resolve() -> None:
    """Calling it with neither key would select every active entry for the
    chain and return whichever came first."""
    with pytest.raises(ValueError, match="needs a sku"):
        resolution_query(uuid.uuid4())


def test_only_one_active_entry_per_key(db: Connection) -> None:
    chain, product, operator = _fixtures(db)
    _entry(db, chain, product, operator, kind="raw_text", value="sut tam yagli 1lt")
    with pytest.raises(DatabaseError, match="uq_chain_lexicon_active"):
        _entry(db, chain, product, operator, kind="raw_text", value="sut tam yagli 1lt")


def test_superseded_entries_accumulate_under_one_key(db: Connection) -> None:
    """History without limit, which is the point: a mapping decision is
    evidence, and the partial index is what allows the pile."""
    chain, product, operator = _fixtures(db)
    for _ in range(3):
        _entry(
            db,
            chain,
            product,
            operator,
            kind="raw_text",
            value="sut tam yagli 1lt",
            status="superseded",
        )
    _entry(db, chain, product, operator, kind="raw_text", value="sut tam yagli 1lt")
    count = db.execute(text("SELECT count(*) FROM chain_lexicon")).scalar_one()
    assert count == 4


def test_an_unfolded_raw_text_key_is_refused(db: Connection) -> None:
    """The data model says this column holds folded text and nothing enforced
    it. An unfolded entry never matches, so the operator who wrote it sees
    their mapping silently ignored forever."""
    chain, product, operator = _fixtures(db)
    with pytest.raises(DatabaseError, match="raw_text_key_is_folded"):
        _entry(db, chain, product, operator, kind="raw_text", value="SÜT TAM YAĞLI 1LT")


def test_an_sku_key_is_not_folded(db: Connection) -> None:
    """Codes are verbatim. Folding one would change it."""
    chain, product, operator = _fixtures(db)
    _entry(db, chain, product, operator, kind="sku", value="ABC-100")
    assert db.execute(resolution_query(chain, sku="ABC-100")).scalar_one() == product


def test_an_empty_key_is_refused(db: Connection) -> None:
    """It would match every line that printed nothing, which is the failure a
    lexicon exists to prevent."""
    chain, product, operator = _fixtures(db)
    with pytest.raises(DatabaseError, match="key_value_is_not_empty"):
        _entry(db, chain, product, operator, kind="raw_text", value="")


def test_an_active_entry_cannot_name_a_successor(db: Connection) -> None:
    chain, product, operator = _fixtures(db)
    replacement = _entry(db, chain, product, operator, kind="sku", value="1")
    still_active = _entry(db, chain, product, operator, kind="sku", value="2")
    with pytest.raises(DatabaseError, match="successor_implies_superseded"):
        db.execute(
            text("UPDATE chain_lexicon SET superseded_by = :s WHERE id = :i"),
            {"s": replacement, "i": still_active},
        )


def test_an_entry_cannot_supersede_itself(db: Connection) -> None:
    chain, product, operator = _fixtures(db)
    entry = _entry(db, chain, product, operator, kind="sku", value="1")
    with pytest.raises(DatabaseError, match="not_its_own_successor"):
        db.execute(
            text(
                "UPDATE chain_lexicon SET status = 'superseded', superseded_by = :s WHERE id = :i"
            ),
            {"s": entry, "i": entry},
        )


def test_a_withdrawal_needs_no_successor(db: Connection) -> None:
    """An operator retracting a wrong mapping with nothing to put in its place
    is a real thing to want, so the biconditional is deliberately one-way."""
    chain, product, operator = _fixtures(db)
    entry = _entry(db, chain, product, operator, kind="sku", value="1")
    db.execute(text("UPDATE chain_lexicon SET status = 'superseded' WHERE id = :i"), {"i": entry})
    assert db.execute(resolution_query(chain, sku="1")).scalar_one_or_none() is None


def test_no_automated_process_can_write_an_entry(db: Connection) -> None:
    """ADR-0011 made structural: a NOT NULL column cannot be filled by a
    suggestion that has no one to attribute."""
    chain, product, _operator = _fixtures(db)
    with pytest.raises(DatabaseError, match="decided_by"):
        db.execute(
            text(
                "INSERT INTO chain_lexicon "
                "(chain_id, key_kind, key_value, product_id, decided_via) "
                "VALUES (:c, 'sku', '1', :p, 'operator')"
            ),
            {"c": chain, "p": product},
        )
