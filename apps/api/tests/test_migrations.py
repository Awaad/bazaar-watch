from __future__ import annotations

import re
from pathlib import Path

from bazaarwatch.core.models import Base
from bazaarwatch.modules.identity import models as _identity_models  # noqa: F401

VERSIONS = Path("apps/api/src/bazaarwatch/migrations/versions")


def _sources() -> list[tuple[Path, str]]:
    return [(p, p.read_text(encoding="utf-8")) for p in sorted(VERSIONS.glob("*.py"))]


def test_revisions_form_a_single_chain() -> None:
    """A branched history cannot be applied deterministically."""
    revisions = {}
    for path, source in _sources():
        rev = re.search(r'^revision: str = "(.+)"', source, re.M)
        down = re.search(r"^down_revision: str \| None = (.+)$", source, re.M)
        assert rev is not None, f"{path}: no revision identifier"
        assert down is not None, f"{path}: no down_revision"
        revisions[rev.group(1)] = down.group(1).strip().strip('"')

    assert list(revisions.values()).count("None") == 1, "exactly one root revision"
    assert len(set(revisions.values())) == len(revisions), "no branch points"


def test_every_migration_has_a_downgrade() -> None:
    """Either a tested downgrade or an explicit statement that it is
    irreversible. A silent `pass` is neither."""
    for path, source in _sources():
        body = source[source.index("def downgrade()") :]
        does_something = "op." in body
        declares_irreversible = "irreversible" in body
        assert does_something or declares_irreversible, f"{path}: empty downgrade"


def test_first_migration_asserts_extensions_rather_than_creating_them() -> None:
    """CREATE EXTENSION needs superuser. Granting that to the application role
    in production is not acceptable, so the privileged bootstrap creates them and
    the migration asserts. See infra/docker/postgres/README.md."""
    source = dict(_sources())[VERSIONS / "0001_foundation_and_identity.py"]
    # Check executed SQL, not any occurrence: the docstring explains why
    # CREATE EXTENSION is deliberately absent, and naming it there is correct.
    executed = "\n".join(re.findall(r"op\.execute\((.*?)\)\n", source, re.S))
    assert "CREATE EXTENSION" not in executed
    assert "SELECT extname FROM pg_extension" in source
    for extension in ("postgis", "vector", "pg_trgm", "ltree", "pgcrypto"):
        assert extension in source


def test_turkish_fold_is_read_from_core_not_duplicated() -> None:
    """Two copies of the fold is the drift this design exists to prevent."""
    source = dict(_sources())[VERSIONS / "0001_foundation_and_identity.py"]
    assert "turkish_fold.sql" in source
    assert "CREATE OR REPLACE FUNCTION turkish_fold" not in source


def test_downgrade_does_not_drop_extensions() -> None:
    """They were not created here, and dropping postgis would take unrelated
    objects with it."""
    source = dict(_sources())[VERSIONS / "0001_foundation_and_identity.py"]
    downgrade = source[source.index("def downgrade()") :]
    executed = "\n".join(re.findall(r"op\.execute\((.*?)\)\n", downgrade, re.S))
    assert "DROP EXTENSION" not in executed


def test_check_constraint_names_are_bare() -> None:
    """The ck_ naming convention is `ck_%(table_name)s_%(constraint_name)s`, so
    passing an already-prefixed name produces `ck_users_ck_users_role_known` and,
    worse, a name the models do not agree on. Autogenerate would then propose
    renaming constraints forever."""
    for path, source in _sources():
        # `[^)]` would stop at the closing paren inside the SQL expression
        # itself, e.g. "role IN ('a', 'b')", before reaching name=.
        pattern = r'CheckConstraint\((?:.|\n){0,400}?name="([^"]+)"'
        for name in re.findall(pattern, source):
            assert not name.startswith("ck_"), (
                f"{path}: CheckConstraint name {name!r} is already prefixed; "
                "the naming convention prefixes it again"
            )


def test_model_and_migration_agree_on_constraint_names() -> None:
    """The models are the source of truth for names. If the migration invents
    different ones, the schema and the metadata drift silently."""
    source = dict(_sources())[VERSIONS / "0001_foundation_and_identity.py"]

    for table_name in ("users", "subject_keys", "push_tokens"):
        table = Base.metadata.tables[table_name]
        for constraint in table.constraints:
            if constraint.name and str(constraint.name).startswith("ck_"):
                assert str(constraint.name) in source or any(
                    str(constraint.name).endswith(bare)
                    for bare in re.findall(r'name="([^"]+)"', source)
                ), f"{table_name}: {constraint.name} not represented in the migration"
