"""Trigger behaviour. Needs a database.

None of this is visible in DDL. The path trigger, its two cascades and the
activation check are the only code in the schema with control flow in it, and
until this file existed none of it had ever run.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DatabaseError

pytestmark = pytest.mark.integration

COMPLETE = '{"tr": "Ad", "en": "Name", "ru": "Imya", "de": "Name"}'


def _category(db: Connection, slug: str, names: str = COMPLETE) -> uuid.UUID:
    return db.execute(
        text("INSERT INTO categories (slug, name_i18n) VALUES (:slug, :names) RETURNING id"),
        {"slug": slug, "names": names},
    ).scalar_one()


def _version(db: Connection, version: int) -> int:
    db.execute(
        text("INSERT INTO taxonomy_versions (version, status) VALUES (:v, 'draft')"),
        {"v": version},
    )
    return version


def _place(db: Connection, category: uuid.UUID, version: int, parent: uuid.UUID | None) -> None:
    db.execute(
        text(
            "INSERT INTO category_structure (category_id, taxonomy_version, parent_id) "
            "VALUES (:c, :v, :p)"
        ),
        {"c": category, "v": version, "p": parent},
    )


def _path(db: Connection, category: uuid.UUID, version: int) -> str:
    return db.execute(
        text(
            "SELECT path::text FROM category_structure "
            "WHERE category_id = :c AND taxonomy_version = :v"
        ),
        {"c": category, "v": version},
    ).scalar_one()


def _tree(db: Connection) -> tuple[int, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    """food > dairy > cheese-aged, and drinks alongside food."""
    version = _version(db, 1)
    food = _category(db, "food")
    drinks = _category(db, "drinks")
    dairy = _category(db, "dairy")
    cheese = _category(db, "cheese-aged")
    _place(db, food, version, None)
    _place(db, drinks, version, None)
    _place(db, dairy, version, food)
    _place(db, cheese, version, dairy)
    return version, food, drinks, dairy, cheese


def test_path_is_built_from_the_parent_chain(db: Connection) -> None:
    version, food, _drinks, dairy, cheese = _tree(db)
    assert _path(db, food, version) == "food"
    assert _path(db, dairy, version) == "food.dairy"
    assert _path(db, cheese, version) == "food.dairy.cheese_aged"


def test_hyphens_become_underscores_in_labels(db: Connection) -> None:
    """ltree labels allow only `[A-Za-z0-9_]` and slugs are hyphenated. The
    mapping cannot collide because `slugify` never emits an underscore."""
    version, _food, _drinks, _dairy, cheese = _tree(db)
    assert "cheese_aged" in _path(db, cheese, version)


def test_moving_a_node_rewrites_every_descendant(db: Connection) -> None:
    """The cascade touches direct children only and recurses through their own
    triggers. A grandchild is the shallowest case that proves it recurses."""
    version, _food, drinks, dairy, cheese = _tree(db)
    db.execute(
        text(
            "UPDATE category_structure SET parent_id = :new "
            "WHERE category_id = :c AND taxonomy_version = :v"
        ),
        {"new": drinks, "c": dairy, "v": version},
    )
    assert _path(db, dairy, version) == "drinks.dairy"
    assert _path(db, cheese, version) == "drinks.dairy.cheese_aged"


def test_renaming_a_category_rewrites_the_paths_below_it(db: Connection) -> None:
    """A slug is part of every descendant's path, which is why the rename needs
    its own trigger on `categories` rather than riding on the structure one."""
    version, _food, _drinks, dairy, cheese = _tree(db)
    db.execute(text("UPDATE categories SET slug = 'milk' WHERE id = :c"), {"c": dairy})
    assert _path(db, dairy, version) == "food.milk"
    assert _path(db, cheese, version) == "food.milk.cheese_aged"


def test_a_rename_rewrites_every_version_the_node_appears_in(db: Connection) -> None:
    version_one, food, _drinks, _dairy, _cheese = _tree(db)
    version_two = _version(db, 2)
    _place(db, food, version_two, None)

    db.execute(text("UPDATE categories SET slug = 'groceries' WHERE id = :c"), {"c": food})
    assert _path(db, food, version_one) == "groceries"
    assert _path(db, food, version_two) == "groceries"


def test_a_cycle_is_refused_by_name(db: Connection) -> None:
    """Without this the cascade recurses until the stack gives out, and the
    error names a depth limit rather than the bad edge."""
    version, food, _drinks, _dairy, cheese = _tree(db)
    with pytest.raises(DatabaseError, match="would be its own ancestor"):
        db.execute(
            text(
                "UPDATE category_structure SET parent_id = :new "
                "WHERE category_id = :c AND taxonomy_version = :v"
            ),
            {"new": cheese, "c": food, "v": version},
        )


def test_a_parent_from_another_version_is_refused(db: Connection) -> None:
    """The composite key is what makes this impossible. A plain reference to
    `categories` would let a path be built across two trees."""
    _version_one, food, _drinks, dairy, _cheese = _tree(db)
    version_two = _version(db, 2)
    with pytest.raises(DatabaseError):
        _place(db, dairy, version_two, food)


def test_activation_is_refused_while_a_name_is_incomplete(db: Connection) -> None:
    version, _food, _drinks, _dairy, _cheese = _tree(db)
    partial = _category(db, "tea", '{"tr": "Cay"}')
    _place(db, partial, version, None)

    with pytest.raises(DatabaseError, match="incomplete name_i18n"):
        db.execute(
            text(
                "UPDATE taxonomy_versions SET status = 'active', activated_at = now() "
                "WHERE version = :v"
            ),
            {"v": version},
        )


def test_activation_succeeds_once_every_name_is_complete(db: Connection) -> None:
    version, _food, _drinks, _dairy, _cheese = _tree(db)
    db.execute(
        text(
            "UPDATE taxonomy_versions SET status = 'active', activated_at = now() "
            "WHERE version = :v"
        ),
        {"v": version},
    )
    status = db.execute(
        text("SELECT status FROM taxonomy_versions WHERE version = :v"), {"v": version}
    ).scalar_one()
    assert status == "active"


def test_an_empty_version_cannot_be_activated(db: Connection) -> None:
    """An empty tree would suppress every category index at once, and each
    suppressed value would read as thin coverage rather than as a mistake."""
    version = _version(db, 7)
    with pytest.raises(DatabaseError, match="no categories"):
        db.execute(
            text(
                "UPDATE taxonomy_versions SET status = 'active', activated_at = now() "
                "WHERE version = :v"
            ),
            {"v": version},
        )


def test_only_one_version_can_be_active(db: Connection) -> None:
    version, food, _drinks, _dairy, _cheese = _tree(db)
    db.execute(
        text(
            "UPDATE taxonomy_versions SET status = 'active', activated_at = now() "
            "WHERE version = :v"
        ),
        {"v": version},
    )
    second = _version(db, 2)
    _place(db, food, second, None)

    with pytest.raises(DatabaseError, match="uq_taxonomy_versions_active"):
        db.execute(
            text(
                "UPDATE taxonomy_versions SET status = 'active', activated_at = now() "
                "WHERE version = :v"
            ),
            {"v": second},
        )


def test_updated_at_is_reset_by_the_trigger(db: Connection) -> None:
    """The column is maintained by the database, not the application.

    Observing this inside one transaction takes some care. `set_updated_at` uses
    `now()`, which is transaction time and constant for the whole transaction,
    so an insert followed by an update leaves the value unchanged and proves
    nothing. Backdating with an UPDATE does not work either, because that UPDATE
    fires the trigger and is overwritten. The trigger is `BEFORE UPDATE` only,
    so an explicit value at insert survives, and the next update is what moves
    it.
    """
    version = _version(db, 1)
    food = _category(db, "food")
    db.execute(
        text(
            "INSERT INTO category_structure "
            "(category_id, taxonomy_version, parent_id, updated_at) "
            "VALUES (:c, :v, NULL, '2000-01-01T00:00:00Z')"
        ),
        {"c": food, "v": version},
    )

    db.execute(
        text(
            "UPDATE category_structure SET sort_order = 5 "
            "WHERE category_id = :c AND taxonomy_version = :v"
        ),
        {"c": food, "v": version},
    )
    after = db.execute(
        text("SELECT updated_at FROM category_structure WHERE category_id = :c"), {"c": food}
    ).scalar_one()
    assert after.year > 2000
