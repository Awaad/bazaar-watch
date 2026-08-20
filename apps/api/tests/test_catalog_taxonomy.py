from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from bazaarwatch.core.locales import LAUNCH_LOCALES, REQUIRED_AT_WRITE, Locale
from bazaarwatch.core.models import Base
from bazaarwatch.modules.catalog import models as _catalog  # noqa: F401
from bazaarwatch.modules.catalog.models import TaxonomyStatus

MIGRATION = Path("apps/api/src/bazaarwatch/migrations/versions/0004_taxonomy.py")

TAXONOMY_TABLES = ("taxonomy_versions", "categories", "category_structure")


def _ddl(table_name: str) -> str:
    return str(CreateTable(Base.metadata.tables[table_name]).compile(dialect=postgresql.dialect()))


def _migration() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_taxonomy_tables_are_registered() -> None:
    assert set(TAXONOMY_TABLES) <= set(Base.metadata.tables)


def test_a_version_is_a_row_rather_than_a_bare_integer() -> None:
    """`index_runs` and `index_values` both carry `taxonomy_version`. Before
    this table there was nothing for that integer to reference, so a published
    figure named a version that could not be looked up."""
    versions = Base.metadata.tables["taxonomy_versions"]
    assert [c.name for c in versions.primary_key] == ["version"]

    structure = Base.metadata.tables["category_structure"]
    targets = {fk.target_fullname for fk in structure.foreign_keys}
    assert "taxonomy_versions.version" in targets


def test_at_most_one_active_version() -> None:
    versions = Base.metadata.tables["taxonomy_versions"]
    active = next(i for i in versions.indexes if i.name == "uq_taxonomy_versions_active")
    assert active.unique
    assert active.dialect_options["postgresql"]["where"] is not None


def test_activation_time_is_present_exactly_when_it_should_be() -> None:
    """A biconditional. Without it an active version can carry no activation
    time, and the announcement date ADR-0079 rule 2 requires has nowhere to
    come from."""
    assert "(status = 'draft') = (activated_at IS NULL)" in _ddl("taxonomy_versions")


def test_categories_have_no_status_column() -> None:
    """Membership in a version's structure is what makes a node live. A status
    column beside it is a second way to say the same thing, which can disagree
    with the first."""
    assert "status" not in Base.metadata.tables["categories"].c


def test_the_slug_is_globally_unique_and_not_per_version() -> None:
    """It is a URL. Restructuring the tree must not move a category on the
    web, which is the whole reason identity is separate from shape."""
    categories = Base.metadata.tables["categories"]
    assert categories.c.slug.unique
    assert "taxonomy_version" not in categories.c


def test_turkish_is_required_at_write() -> None:
    assert f"name_i18n ? '{REQUIRED_AT_WRITE.value}'" in _ddl("categories")


def test_a_category_cannot_supersede_itself() -> None:
    assert "superseded_by_id IS NULL OR superseded_by_id <> id" in _ddl("categories")


def test_the_parent_is_scoped_to_the_same_taxonomy_version() -> None:
    """A plain reference to `categories` would let a node in version 3 claim a
    parent that only exists in version 4, and the trigger would happily build a
    path across two trees."""
    ddl = _ddl("category_structure")
    assert (
        "FOREIGN KEY(parent_id, taxonomy_version) REFERENCES "
        "category_structure (category_id, taxonomy_version)" in ddl
    )


def test_path_is_ltree_and_not_null() -> None:
    """Text would accept a malformed path and lose every subtree operator."""
    assert "path LTREE NOT NULL" in _ddl("category_structure")


def test_the_path_index_is_gist() -> None:
    """Subtree containment is the reason for ltree, and it is an index scan
    only with this."""
    structure = Base.metadata.tables["category_structure"]
    path_index = next(i for i in structure.indexes if i.name == "ix_category_structure_path")
    assert path_index.dialect_options["postgresql"]["using"] == "gist"


def test_launch_locales_exclude_arabic() -> None:
    """`ar` is layout-ready and deliberately untranslated. Requiring it for
    completeness would block every taxonomy version forever."""
    assert Locale.ARABIC not in LAUNCH_LOCALES
    assert set(LAUNCH_LOCALES) == {Locale.TURKISH, Locale.ENGLISH, Locale.RUSSIAN, Locale.GERMAN}


def test_the_migration_checks_exactly_the_launch_locales() -> None:
    """The revision writes the list out rather than importing it, so that a
    later locale does not change what an old revision enforces. This is what
    keeps the two in step."""
    rendered = re.search(r"_LAUNCH_LOCALES = \"ARRAY\[([^\]]*)\]\"", _migration())
    assert rendered is not None
    in_migration = re.findall(r"'(\w+)'", rendered.group(1))
    assert in_migration == [locale.value for locale in LAUNCH_LOCALES]


def test_the_path_trigger_refuses_a_cycle() -> None:
    """Without this the descendant cascade recurses until the stack gives out,
    and the error names a depth limit rather than the bad edge."""
    assert "would be its own ancestor" in _migration()


def test_the_activation_trigger_refuses_an_empty_version() -> None:
    """A version with no categories going active would suppress every category
    index at once, with each value reading as thin coverage rather than as a
    mistake."""
    assert "has no categories and cannot be activated" in _migration()


def test_taxonomy_status_vocabulary() -> None:
    assert TaxonomyStatus.sql_values() == "'draft', 'active', 'superseded'"


def test_superseded_is_a_status_rather_than_a_deletion() -> None:
    """ADR-0079 rule 5: sunset, do not delete. The old series stays available
    permanently and needs its version row to stay readable."""
    assert TaxonomyStatus.SUPERSEDED in list(TaxonomyStatus)
