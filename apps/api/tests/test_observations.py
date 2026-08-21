"""Ingest and observation constraints, and the ADR-0090 scopes. Needs a database."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Connection, select, text
from sqlalchemy.exc import DatabaseError

from bazaarwatch.modules.observations.service import (
    countable_observations,
    unresolved_observations,
)

pytestmark = pytest.mark.integration

COMPLETE = '{"tr": "Ad", "en": "Name", "ru": "Imya", "de": "Name"}'
POINT = "ST_SetSRID(ST_MakePoint(33.33, 35.33), 4326)"


def _world(db: Connection) -> dict[str, uuid.UUID]:
    user = db.execute(
        text("INSERT INTO users (slug, role) VALUES ('op', 'operator') RETURNING id")
    ).scalar_one()
    chain = db.execute(
        text("INSERT INTO chains (slug, name) VALUES ('molto', 'Molto') RETURNING id")
    ).scalar_one()
    branch = db.execute(
        text(
            "INSERT INTO branches (chain_id, slug, name, geom, verified_by_human, "
            f"verified_by, verified_at) VALUES (:c, 'b', 'B', {POINT}, true, :u, now()) "
            "RETURNING id"
        ),
        {"c": chain, "u": user},
    ).scalar_one()
    category = db.execute(
        text("INSERT INTO categories (slug, name_i18n) VALUES ('food', :n) RETURNING id"),
        {"n": COMPLETE},
    ).scalar_one()
    product = db.execute(
        text(
            "INSERT INTO products (slug, canonical_name, category_id) "
            "VALUES ('sut', 'Süt', :c) RETURNING id"
        ),
        {"c": category},
    ).scalar_one()
    submission = db.execute(
        text(
            "INSERT INTO submissions (contributor_id, client_idempotency_key, channel, kind, "
            "captured_at) VALUES (:u, gen_random_uuid(), 'app', 'receipt', now()) RETURNING id"
        ),
        {"u": user},
    ).scalar_one()
    run = db.execute(
        text(
            "INSERT INTO extraction_runs (submission_id, extraction_method, extraction_version) "
            "VALUES (:s, 'fake', 'v1') RETURNING id"
        ),
        {"s": submission},
    ).scalar_one()
    return {
        "user": user,
        "chain": chain,
        "branch": branch,
        "product": product,
        "submission": submission,
        "run": run,
    }


def _observation(db: Connection, w: dict[str, uuid.UUID], **kwargs: object) -> uuid.UUID:
    return db.execute(
        text(
            "INSERT INTO price_observations (source_kind, source_id, branch_id, product_id, "
            "observed_at, price_minor, status, extraction_run_id) "
            "VALUES ('receipt_line', gen_random_uuid(), :b, :p, now(), :price, :st, :run) "
            "RETURNING id"
        ),
        {
            "b": w["branch"],
            "p": kwargs.get("product", w["product"]),
            "price": kwargs.get("price", 1000),
            "st": kwargs.get("status", "accepted"),
            "run": w["run"],
        },
    ).scalar_one()


def test_only_one_current_extraction_run_per_submission(db: Connection) -> None:
    """This is what makes reprocessing supersede rather than double count."""
    w = _world(db)
    with pytest.raises(DatabaseError, match="uq_extraction_runs_current"):
        db.execute(
            text(
                "INSERT INTO extraction_runs (submission_id, extraction_method, "
                "extraction_version) VALUES (:s, 'fake', 'v2')"
            ),
            {"s": w["submission"]},
        )


def test_a_superseded_run_cannot_still_be_current(db: Connection) -> None:
    w = _world(db)
    with pytest.raises(DatabaseError, match="superseded_is_not_current"):
        db.execute(
            text("UPDATE extraction_runs SET status = 'superseded' WHERE id = :r"),
            {"r": w["run"]},
        )


def test_a_receipt_sourced_observation_names_its_run(db: Connection) -> None:
    """Without the run there is no way to find an observation when the run that
    produced it is superseded."""
    w = _world(db)
    with pytest.raises(DatabaseError, match="run_iff_receipt_sourced"):
        db.execute(
            text(
                "INSERT INTO price_observations (source_kind, source_id, branch_id, "
                "observed_at, price_minor) "
                "VALUES ('receipt_line', gen_random_uuid(), :b, now(), 100)"
            ),
            {"b": w["branch"]},
        )


def test_a_scrape_has_no_run_to_name(db: Connection) -> None:
    w = _world(db)
    with pytest.raises(DatabaseError, match="run_iff_receipt_sourced"):
        db.execute(
            text(
                "INSERT INTO price_observations (source_kind, source_id, branch_id, "
                "observed_at, price_minor, extraction_run_id) "
                "VALUES ('scrape', gen_random_uuid(), :b, now(), 100, :r)"
            ),
            {"b": w["branch"], "r": w["run"]},
        )


def test_one_source_produces_one_observation(db: Connection) -> None:
    w = _world(db)
    source = uuid.uuid4()
    for _ in range(2):
        statement = text(
            "INSERT INTO price_observations (source_kind, source_id, branch_id, observed_at, "
            "price_minor, extraction_run_id) VALUES ('receipt_line', :s, :b, now(), 100, :r)"
        )
        if _ == 0:
            db.execute(statement, {"s": source, "b": w["branch"], "r": w["run"]})
        else:
            with pytest.raises(DatabaseError, match="uq_price_observations_source"):
                db.execute(statement, {"s": source, "b": w["branch"], "r": w["run"]})


def test_a_unit_price_needs_a_basis(db: Connection) -> None:
    """A unit price with no basis is a number with no meaning, and comparison
    ranks on it."""
    w = _world(db)
    with pytest.raises(DatabaseError, match="unit_price_has_a_basis"):
        db.execute(
            text(
                "INSERT INTO price_observations (source_kind, source_id, branch_id, observed_at, "
                "price_minor, unit_price_minor, extraction_run_id) "
                "VALUES ('receipt_line', gen_random_uuid(), :b, now(), 100, 50, :r)"
            ),
            {"b": w["branch"], "r": w["run"]},
        )


def test_a_zero_quantity_is_refused(db: Connection) -> None:
    w = _world(db)
    with pytest.raises(DatabaseError, match="quantity_is_positive"):
        db.execute(
            text(
                "INSERT INTO price_observations (source_kind, source_id, branch_id, observed_at, "
                "price_minor, quantity, extraction_run_id) "
                "VALUES ('receipt_line', gen_random_uuid(), :b, now(), 100, 0, :r)"
            ),
            {"b": w["branch"], "r": w["run"]},
        )


def test_a_three_element_bbox_is_refused(db: Connection) -> None:
    """A wrong box crops the wrong region, and a reviewer sees an arbitrary
    strip of somebody's receipt."""
    w = _world(db)
    receipt = db.execute(
        text(
            "INSERT INTO receipts (submission_id, extraction_run_id) VALUES (:s, :r) RETURNING id"
        ),
        {"s": w["submission"], "r": w["run"]},
    ).scalar_one()
    with pytest.raises(DatabaseError, match="bbox_has_four_values"):
        db.execute(
            text(
                "INSERT INTO receipt_lines (receipt_id, line_index, line_kind, raw_text, bbox) "
                "VALUES (:r, 0, 'item', 'SUT', '[1,2,3]')"
            ),
            {"r": receipt},
        )


def test_a_residual_verdict_must_be_quantified(db: Connection) -> None:
    w = _world(db)
    with pytest.raises(DatabaseError, match="residual_is_quantified"):
        db.execute(
            text(
                "INSERT INTO receipts (submission_id, extraction_run_id, reconciliation_status) "
                "VALUES (:s, :r, 'residual')"
            ),
            {"s": w["submission"], "r": w["run"]},
        )


def test_a_location_verdict_comes_with_its_confidence(db: Connection) -> None:
    w = _world(db)
    with pytest.raises(DatabaseError, match="location_verdict_is_complete"):
        db.execute(
            text(
                "INSERT INTO submissions (contributor_id, client_idempotency_key, channel, kind, "
                "captured_at, location_matched) "
                "VALUES (:u, gen_random_uuid(), 'app', 'receipt', now(), true)"
            ),
            {"u": w["user"]},
        )


def test_a_media_object_needs_a_wrapped_key(db: Connection) -> None:
    """Erasure destroys the subject KEK, which makes every object wrapped by it
    unreadable. An object with no wrapped key is not covered by that."""
    w = _world(db)
    with pytest.raises(DatabaseError, match="dek_is_present"):
        db.execute(
            text(
                "INSERT INTO media_objects (submission_id, role, bucket, object_key, "
                "content_hash, mime_type, byte_size, subject_user_id, wrapped_dek) "
                "VALUES (:s, 'original', 'b', 'k', 'h', 'image/jpeg', 10, :u, '')"
            ),
            {"s": w["submission"], "u": w["user"]},
        )


def test_the_countable_scope_excludes_superseded_rows(db: Connection) -> None:
    """The reason ADR-0090 exists. Reprocessing writes new observations and
    moves the old ones aside; counting both inflates the figure by exactly the
    amount the model improved."""
    w = _world(db)
    _observation(db, w, status="accepted")
    _observation(db, w, status="superseded")
    _observation(db, w, status="pending")

    total = db.execute(text("SELECT count(*) FROM price_observations")).scalar_one()
    countable = db.execute(select(countable_observations().c.id)).scalars().all()

    assert total == 3
    assert len(countable) == 1


def test_the_countable_scope_excludes_unresolved_rows(db: Connection) -> None:
    """A null product_id groups unrelated goods into one bucket."""
    w = _world(db)
    _observation(db, w, status="accepted")
    _observation(db, w, status="accepted", product=None)

    countable = db.execute(select(countable_observations().c.id)).scalars().all()
    assert len(countable) == 1


def test_the_unresolved_scope_ignores_status(db: Connection) -> None:
    """A pending unresolved row is exactly what a T1 task is for. Requiring
    acceptance first would deadlock the queue that does the accepting."""
    w = _world(db)
    _observation(db, w, status="pending", product=None)
    _observation(db, w, status="accepted", product=None)
    _observation(db, w, status="accepted")

    unresolved = db.execute(select(unresolved_observations().c.id)).scalars().all()
    assert len(unresolved) == 2


def test_each_call_returns_a_fresh_scope() -> None:
    assert countable_observations() is not countable_observations()


def _receipt_with_line(db: Connection, w: dict[str, uuid.UUID], rate: int | None) -> None:
    receipt = db.execute(
        text(
            "INSERT INTO receipts (submission_id, extraction_run_id) VALUES (:s, :r) RETURNING id"
        ),
        {"s": w["submission"], "r": w["run"]},
    ).scalar_one()
    db.execute(
        text(
            "INSERT INTO receipt_lines (receipt_id, line_index, line_kind, raw_text, tax_rate_bp) "
            "VALUES (:r, 0, 'item', 'MUZ', :bp)"
        ),
        {"r": receipt, "bp": rate},
    )


def test_a_printed_tax_rate_is_stored_as_basis_points(db: Connection) -> None:
    """Whole percents on the receipt, integers here. A fraction would invite a
    float into the one place this schema refuses them."""
    w = _world(db)
    _receipt_with_line(db, w, 1600)
    stored = db.execute(text("SELECT tax_rate_bp FROM receipt_lines")).scalar_one()
    assert stored == 1600


def test_a_line_without_a_printed_rate_is_allowed(db: Connection) -> None:
    """Not every POS prints one, and its absence is a fact about the chain."""
    w = _world(db)
    _receipt_with_line(db, w, None)
    assert db.execute(text("SELECT tax_rate_bp FROM receipt_lines")).scalar_one() is None


def test_a_rate_above_one_hundred_percent_is_refused(db: Connection) -> None:
    w = _world(db)
    with pytest.raises(DatabaseError, match="tax_rate_in_range"):
        _receipt_with_line(db, w, 10001)


def test_the_bektas_receipt_reconciles_per_rate_bucket(db: Connection) -> None:
    """The reason the column exists, on real numbers.

    ADR-0081 compares one sum to one total, and compensating errors survive
    that: swap two line totals between buckets and the receipt still balances.
    Per-line rates give one equation per bucket instead. These are the five
    lines and four buckets from a Bektaş Gıda Pazarı receipt, and the KDV is
    inclusive, so each bucket's tax is total * rate / (10000 + rate).
    """
    lines = [
        ("MUZ", 7300, 0),
        ("ULKER MARIFET TOR", 13750, 500),
        ("RUFFLES MEGA-- ORI", 9000, 1000),
        ("NIVEA SPREY 150ML", 20990, 1600),
        ("BEKTAS MARKET POS", 400, 500),
    ]
    printed_buckets = {0: (7300, 0), 500: (14150, 674), 1000: (9000, 818), 1600: (20990, 2895)}

    w = _world(db)
    receipt = db.execute(
        text(
            "INSERT INTO receipts (submission_id, extraction_run_id, printed_total_minor, "
            "tax_total_minor) VALUES (:s, :r, 51440, 4387) RETURNING id"
        ),
        {"s": w["submission"], "r": w["run"]},
    ).scalar_one()
    for index, (raw, total, rate) in enumerate(lines):
        db.execute(
            text(
                "INSERT INTO receipt_lines (receipt_id, line_index, line_kind, raw_text, "
                "raw_line_total_minor, tax_rate_bp) VALUES (:r, :i, 'item', :t, :total, :bp)"
            ),
            {"r": receipt, "i": index, "t": raw, "total": total, "bp": rate},
        )

    buckets = db.execute(
        text(
            "SELECT tax_rate_bp, sum(raw_line_total_minor) "
            "FROM receipt_lines WHERE receipt_id = :r GROUP BY tax_rate_bp"
        ),
        {"r": receipt},
    ).all()

    for rate, subtotal in buckets:
        expected_total, expected_tax = printed_buckets[rate]
        assert subtotal == expected_total
        # Inclusive: the tax is inside the printed amount, never added to it.
        assert round(subtotal * rate / (10000 + rate)) == expected_tax

    printed_total, tax_total = db.execute(
        text("SELECT printed_total_minor, tax_total_minor FROM receipts WHERE id = :r"),
        {"r": receipt},
    ).one()
    assert sum(total for _, total, _ in lines) == printed_total
    assert sum(tax for _, tax in printed_buckets.values()) == tax_total
