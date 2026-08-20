"""Constraints and the SQL fold. Needs a database.

A CHECK that spans columns, a partial unique index, and the parity between
`turkish_fold` in Python and its SQL mirror are all invisible to a unit test.
The fold in particular is the one this project has called the highest-value
outstanding check since slice 5: if the two implementations ever diverge,
lexicon resolution silently misses and nothing raises.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DatabaseError

from bazaarwatch.core.text import turkish_fold

pytestmark = pytest.mark.integration

POINT = "ST_SetSRID(ST_MakePoint(33.36, 35.17), 4326)"

# Chosen for the cases Turkish casing gets wrong, not for coverage of the
# alphabet. The dotless i is the one that breaks under a locale-naive fold, and
# the rest are the letters an ASCII fold drops.
FOLD_CASES = (
    "İstanbul",
    "IĞDIR",
    "ıIiİ",
    "Şok Market",
    "Güneş Gıda",
    "ÇAĞRI",
    "Öz Ürünler",
    "ĞğÜüŞşÖöÇç",
    "CC KOLA 1LT PET",
    "Ülker Çikolata",
    "MİGROS",
    "Peynir  Beyaz",
    "A101",
)


@pytest.mark.parametrize("value", FOLD_CASES)
def test_the_sql_fold_agrees_with_the_python_fold(db: Connection, value: str) -> None:
    """Two implementations of one function, and nothing but this notices when
    they drift. ADR-0025 centralises the fold for exactly this reason."""
    in_sql = db.execute(text("SELECT turkish_fold(:v)"), {"v": value}).scalar_one()
    assert in_sql == turkish_fold(value)


def _chain(db: Connection) -> uuid.UUID:
    return db.execute(
        text("INSERT INTO chains (slug, name) VALUES ('lemar', 'Lemar') RETURNING id")
    ).scalar_one()


def _branch(
    db: Connection, chain: uuid.UUID, slug: str, columns: str = "", values: str = ""
) -> None:
    db.execute(
        text(
            f"INSERT INTO branches (chain_id, slug, name {columns}) "
            f"VALUES (:chain, :slug, 'B' {values})"
        ),
        {"chain": chain, "slug": slug},
    )


def test_a_physical_branch_without_geometry_is_refused(db: Connection) -> None:
    """It would be invisible to reachability, and ADR-0035 filters to a
    reachable set before ranking rather than after."""
    chain = _chain(db)
    with pytest.raises(DatabaseError, match="physical_has_geom"):
        _branch(db, chain, "a", ", branch_kind", ", 'physical'")


def test_an_online_branch_carrying_a_coordinate_is_refused(db: Connection) -> None:
    """The other direction, and the one that matters more: a fabricated
    coordinate would put an online seller inside a reachable set silently."""
    chain = _chain(db)
    with pytest.raises(DatabaseError, match="online_has_no_geom"):
        _branch(db, chain, "b", ", branch_kind, geom", f", 'online', {POINT}")


def test_verification_without_an_operator_is_refused(db: Connection) -> None:
    """`verified_by_human` gates every published figure under ADR-0023. A true
    flag with no actor and no time is a claim nobody made."""
    chain = _chain(db)
    with pytest.raises(DatabaseError, match="verification_has_an_actor"):
        _branch(db, chain, "c", ", geom, verified_by_human", f", {POINT}, true")


def test_source_confidence_outside_zero_to_one_is_refused(db: Connection) -> None:
    chain = _chain(db)
    with pytest.raises(DatabaseError, match="confidence_in_range"):
        _branch(db, chain, "d", ", geom, source_confidence", f", {POINT}, 1.5")


def test_two_branches_with_no_source_key_are_both_allowed(db: Connection) -> None:
    """Manual entry is a first-class path under ADR-0023 and carries no source
    key. A total unique index would permit exactly one such branch."""
    chain = _chain(db)
    _branch(db, chain, "e", ", geom", f", {POINT}")
    _branch(db, chain, "f", ", geom", f", {POINT}")
    count = db.execute(text("SELECT count(*) FROM branches")).scalar_one()
    assert count == 2


def test_the_same_source_key_twice_is_refused(db: Connection) -> None:
    chain = _chain(db)
    _branch(db, chain, "g", ", geom, source_provider, source_id", f", {POINT}, 'overture', 'x1'")
    with pytest.raises(DatabaseError, match="uq_branches_source"):
        _branch(
            db, chain, "h", ", geom, source_provider, source_id", f", {POINT}, 'overture', 'x1'"
        )


def test_a_promoted_candidate_without_a_branch_is_refused(db: Connection) -> None:
    with pytest.raises(DatabaseError, match="promoted_iff_branch"):
        db.execute(
            text(
                "INSERT INTO branch_candidates (source_provider, source_id, raw, status) "
                "VALUES ('overture', 'y1', '{}', 'promoted')"
            )
        )


def test_a_candidate_cannot_be_its_own_duplicate(db: Connection) -> None:
    """Following the survivor chain has to terminate."""
    candidate = uuid.UUID("00000000-0000-7000-8000-0000000000d1")
    with pytest.raises(DatabaseError, match=r"not_its_own_duplicate|duplicate_iff_survivor"):
        db.execute(
            text(
                "INSERT INTO branch_candidates "
                "(id, source_provider, source_id, raw, status, duplicate_of_id) "
                "VALUES (:id, 'overture', 'y2', '{}', 'duplicate', :id)"
            ),
            {"id": candidate},
        )


def test_a_rating_outside_one_to_five_is_refused(db: Connection) -> None:
    chain = _chain(db)
    _branch(db, chain, "i", ", geom", f", {POINT}")
    branch = db.execute(text("SELECT id FROM branches WHERE slug = 'i'")).scalar_one()
    tombstone = db.execute(
        text("SELECT id FROM users WHERE slug = 'deleted-contributor'")
    ).scalar_one()

    with pytest.raises(DatabaseError, match="score_in_range"):
        db.execute(
            text(
                "INSERT INTO branch_attribute_ratings "
                "(branch_id, contributor_id, dimension, score, observed_at) "
                "VALUES (:b, :u, 'queue_length', 9, now())"
            ),
            {"b": branch, "u": tombstone},
        )


def test_deleting_a_referenced_row_is_refused(db: Connection) -> None:
    """RESTRICT everywhere. Erasure repoints to the tombstone rather than
    cascading, and a cascade here would take observations with it."""
    chain = _chain(db)
    _branch(db, chain, "j", ", geom", f", {POINT}")
    with pytest.raises(DatabaseError, match="fk_branches_chain_id_chains"):
        db.execute(text("DELETE FROM chains WHERE id = :id"), {"id": chain})
