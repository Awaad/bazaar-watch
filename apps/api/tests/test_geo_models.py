from __future__ import annotations

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from bazaarwatch.core.models import Base
from bazaarwatch.modules.geo import service
from bazaarwatch.modules.geo.models import (
    AttributeDimension,
    BranchKind,
    CandidateStatus,
    OperatingStatus,
)
from bazaarwatch.modules.identity import models as _identity  # noqa: F401

GEO_TABLES = ("chains", "branches", "branch_candidates", "branch_attribute_ratings")

# Postgres truncates a longer identifier silently, which would leave an upgrade
# and a downgrade disagreeing about a constraint name.
POSTGRES_IDENTIFIER_LIMIT = 63


def _ddl(table_name: str) -> str:
    table = Base.metadata.tables[table_name]
    return str(CreateTable(table).compile(dialect=postgresql.dialect()))


def test_geo_tables_are_registered_on_the_shared_metadata() -> None:
    assert set(GEO_TABLES) <= set(Base.metadata.tables)


def test_every_generated_identifier_fits_postgres() -> None:
    """`fk_branch_candidates_duplicate_of_candidate_id_branch_candidates` was
    64 characters, which is how the self-referencing column ended up named
    `duplicate_of_id`. SQLAlchemy raises on this, but only when DDL is
    compiled, which nothing else in the unit suite does."""
    too_long = []
    for table in Base.metadata.tables.values():
        names = [c.name for c in table.constraints] + [i.name for i in table.indexes]
        too_long += [
            str(name) for name in names if name and len(str(name)) > POSTGRES_IDENTIFIER_LIMIT
        ]
    assert not too_long, f"identifiers over {POSTGRES_IDENTIFIER_LIMIT} characters: {too_long}"


def test_no_column_is_left_without_a_type() -> None:
    """A `ForeignKey` with no explicit type resolves from the referenced column,
    and a cross-module reference resolves only if the other module happens to
    have been imported first. `branches.verified_by` came out as `NullType` when
    `geo` was imported without `identity`, which is an import-order accident
    deciding a column type. Every foreign key now declares its type."""
    untyped = [
        f"{table.name}.{column.name}"
        for table in Base.metadata.tables.values()
        for column in table.c
        if repr(column.type) == "NullType()"
    ]
    assert not untyped, f"columns with no type: {untyped}"


def test_all_ddl_compiles_for_postgres() -> None:
    """Catches the identifier limit, an unrenderable type, and anything else
    that only appears at compile time."""
    for name in Base.metadata.tables:
        assert _ddl(name)


def test_geometry_columns_are_geography_4326() -> None:
    """`geography`, not `geometry`: every distance this system asks for is a
    real distance in metres, and ST_DWithin on geography answers that without
    a projection choice nobody would remember to make. See ADR-0035."""
    for name in ("branches", "branch_candidates"):
        assert "geography(POINT,4326)" in _ddl(name)


def test_no_automatic_spatial_index_leaks_in() -> None:
    """GeoAlchemy2 attaches `idx_<table>_<column>` at construction unless
    `spatial_index=False`, which bypasses NAMING_CONVENTION and leaves a second
    GIST index the downgrade does not know about."""
    for table in Base.metadata.tables.values():
        for index in table.indexes:
            assert not str(index.name).startswith("idx_"), index.name


def test_the_geometry_index_is_gist() -> None:
    """A btree on a geography column is accepted and useless: ST_DWithin
    cannot use it, so every reachability query becomes a sequential scan."""
    branches = Base.metadata.tables["branches"]
    geom_index = next(i for i in branches.indexes if i.name == "ix_branches_geom")
    assert geom_index.dialect_options["postgresql"]["using"] == "gist"


def test_physical_and_online_geometry_rules_are_both_enforced() -> None:
    """One direction is not enough. Without the second, an online branch could
    carry a fabricated coordinate and enter reachability silently, which is the
    alternative ADR-0045 rejected."""
    ddl = _ddl("branches")
    assert "branch_kind <> 'physical' OR geom IS NOT NULL" in ddl
    assert "branch_kind <> 'online' OR geom IS NULL" in ddl


def test_verification_requires_an_actor_and_a_time() -> None:
    """`verified_by_human` gates every published figure under ADR-0023. A true
    flag with no operator and no timestamp is a claim nobody made."""
    assert "NOT verified_by_human OR (verified_by IS NOT NULL AND verified_at IS NOT NULL)" in _ddl(
        "branches"
    )


def test_candidate_status_and_its_references_agree_in_both_directions() -> None:
    """A biconditional, not an implication: a rejected candidate must not carry
    a branch reference, and a promoted one must not lack it."""
    ddl = _ddl("branch_candidates")
    assert "(status = 'promoted') = (promoted_branch_id IS NOT NULL)" in ddl
    assert "(status = 'duplicate') = (duplicate_of_id IS NOT NULL)" in ddl


def test_a_candidate_cannot_be_its_own_duplicate() -> None:
    """Following the survivor chain has to terminate."""
    assert "duplicate_of_id IS NULL OR duplicate_of_id <> id" in _ddl("branch_candidates")


def test_source_confidence_is_bounded() -> None:
    for name in ("branches", "branch_candidates"):
        assert "source_confidence IS NULL OR source_confidence BETWEEN 0 AND 1" in _ddl(name)


def test_candidate_operating_status_allows_null_but_not_a_provider_spelling() -> None:
    """A provider may say nothing, and when it does say something the ingest
    stage normalises to our vocabulary rather than storing its spelling."""
    ddl = _ddl("branch_candidates")
    assert "operating_status IS NULL OR operating_status IN" in ddl


def test_the_source_key_is_unique_only_where_it_exists() -> None:
    """Manual entry is a first-class path under ADR-0023, and manually entered
    branches carry no source key. A total unique index would let exactly one of
    them exist."""
    branches = Base.metadata.tables["branches"]
    source_index = next(i for i in branches.indexes if i.name == "uq_branches_source")
    assert source_index.unique
    assert source_index.dialect_options["postgresql"]["where"] is not None

    candidates = Base.metadata.tables["branch_candidates"]
    candidate_index = next(i for i in candidates.indexes if i.name == "uq_branch_candidates_source")
    assert candidate_index.unique
    assert candidate_index.dialect_options["postgresql"]["where"] is None


def test_ratings_have_no_updated_at() -> None:
    """A rating is an observation at a moment, not a mutable record. Editing
    one would silently rewrite an aggregate that has already been read."""
    assert "updated_at" not in Base.metadata.tables["branch_attribute_ratings"].c


def test_enum_vocabularies_match_the_documented_ones() -> None:
    assert BranchKind.sql_values() == "'physical', 'online'"
    assert OperatingStatus.sql_values() == "'open', 'temporarily_closed', 'permanently_closed'"
    assert CandidateStatus.sql_values() == "'pending', 'promoted', 'rejected', 'duplicate'"
    assert AttributeDimension.sql_values() == "'produce_freshness', 'stock_breadth', 'queue_length'"


def _compiled(subquery: object) -> str:
    return str(subquery.original.compile(dialect=postgresql.dialect()))  # type: ignore[attr-defined]


def test_index_scope_carries_both_exclusions() -> None:
    """ADR-0045 excludes online, ADR-0023 excludes unverified. Two records, two
    reasons, and this is the single place either is written down in a query."""
    sql = _compiled(service.index_eligible_branches())
    assert "branch_kind = " in sql
    assert "verified_by_human IS true" in sql


def test_public_scope_keeps_online_sellers() -> None:
    """They are real price sources and belong in item lookup and price history.
    Excluding them here would collapse the distinction ADR-0045 exists for."""
    sql = _compiled(service.public_branches())
    assert "verified_by_human IS true" in sql
    assert "branch_kind = " not in sql


def test_neither_scope_filters_operating_status() -> None:
    """A permanently closed branch has real history, and an index recomputed
    over a past period must still see the prices observed then. Filtering here
    would silently rewrite history, which ADR-0079 forbids."""
    for scope in (service.index_eligible_branches(), service.public_branches()):
        where = _compiled(scope).split("WHERE", 1)[1]
        assert "operating_status" not in where


def test_each_call_returns_a_fresh_selectable() -> None:
    """Two calls in one query must not collide on an alias."""
    assert service.index_eligible_branches() is not service.index_eligible_branches()
