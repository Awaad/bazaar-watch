"""The seed, run end to end. Needs a database.

A constraint test checks one rule in isolation. The seed has to satisfy all of
them at once and in the right order, which is a different kind of check: it is
the first thing that touches identity, taxonomy, geo and catalog in one
transaction.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest
from sqlalchemy import Connection, Engine, func, select, text

from bazaarwatch.modules.geo.service import index_eligible_branches, public_branches

pytestmark = pytest.mark.integration

SEED = "tools/seed/seed.py"


def _run_seed(engine: Engine) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, SEED],
        env={
            **os.environ,
            "DATABASE_URL": engine.url.render_as_string(hide_password=False),
            "REDIS_URL": os.environ.get("REDIS_URL", "redis://127.0.0.1:1/0"),
            "ENVIRONMENT": "local",
        },
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def seeded(seed_engine: Engine) -> Connection:
    result = _run_seed(seed_engine)
    assert result.returncode == 0, result.stdout + result.stderr
    return seed_engine.connect()


def test_the_seed_runs_against_a_freshly_migrated_database(seeded: Connection) -> None:
    counts = seeded.execute(
        text(
            "SELECT (SELECT count(*) FROM chains), (SELECT count(*) FROM branches), "
            "(SELECT count(*) FROM products), (SELECT count(*) FROM categories)"
        )
    ).one()
    assert counts == (2, 3, 4, 4)
    seeded.close()


def test_running_it_twice_changes_nothing(seed_engine: Engine) -> None:
    """A seed that cannot be re-run is a seed nobody re-runs, and then the
    fixture data drifts from the migrations it was written against."""
    assert _run_seed(seed_engine).returncode == 0
    with seed_engine.connect() as connection:
        first = connection.execute(text("SELECT count(*) FROM products")).scalar_one()
    assert _run_seed(seed_engine).returncode == 0
    with seed_engine.connect() as connection:
        second = connection.execute(text("SELECT count(*) FROM products")).scalar_one()
    assert first == second


def test_the_taxonomy_version_ends_up_active(seeded: Connection) -> None:
    """Which means the activation trigger accepted it: four complete names in
    four launch locales, and a non-empty tree."""
    status = seeded.execute(
        text("SELECT status FROM taxonomy_versions WHERE version = 1")
    ).scalar_one()
    assert status == "active"
    seeded.close()


def test_the_path_trigger_ran_through_the_seed(seeded: Connection) -> None:
    path = seeded.execute(
        text(
            "SELECT s.path::text FROM category_structure s JOIN categories c "
            "ON c.id = s.category_id WHERE c.slug = 'gazli-icecekler'"
        )
    ).scalar_one()
    assert path == "icecekler.gazli_icecekler"
    seeded.close()


def test_the_two_scopes_differ_on_real_rows(seeded: Connection) -> None:
    """Three branches: one physical and verified, one physical and unverified,
    one online and verified. ADR-0088 says the first is the only one an index
    may see, and the online one belongs in price history but not in a
    comparison. This is that difference, on data rather than in a docstring.
    """
    total = seeded.execute(select(func.count()).select_from(text("branches"))).scalar_one()
    index_scope = index_eligible_branches()
    public_scope = public_branches()

    indexable = seeded.execute(select(index_scope.c.slug)).scalars().all()
    public = seeded.execute(select(public_scope.c.slug).order_by(public_scope.c.slug))

    assert total == 3
    assert list(indexable) == ["molto-dogankoy"]
    assert list(public.scalars()) == ["molto-dogankoy", "molto-online"]
    seeded.close()


def test_private_label_ownership_is_reachable_through_the_brand(seeded: Connection) -> None:
    """`products.owner_chain_id` is gone, so this is the join the substitution
    rule will need. Two hops rather than one, which is the trade recorded when
    the column was dropped."""
    owner = seeded.execute(
        text(
            "SELECT ch.slug FROM products p "
            "JOIN brands b ON b.id = p.brand_id "
            "JOIN chains ch ON ch.id = b.owner_chain_id "
            "WHERE b.is_private_label"
        )
    ).scalar_one()
    assert owner == "molto"
    seeded.close()
