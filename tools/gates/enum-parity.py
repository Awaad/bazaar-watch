#!/usr/bin/env python3
"""Gate: every enum-backed CHECK constraint exists in the migration set.

`docs/03-data-model.md` enforces enumerations with `TEXT` plus a `CHECK` rather
than a native Postgres enum. The models render the constraint from a
`SqlStrEnum`, so the class and the metadata cannot disagree. The database can.

Adding a member to an enum changes what the models describe and changes nothing
in Postgres. Alembic autogenerate does not reliably detect an altered CHECK, so
no migration is proposed, no test fails, and the new value is rejected at insert
by a constraint nobody remembers writing. That is the failure this guards.

The check is deliberately literal: the expression the models render must appear,
character for character after whitespace normalisation, somewhere in
`versions/`. A migration that alters a constraint therefore has to write the new
expression out, which is also what makes the change visible in review.

Migrations do not import the enums. An old revision that rendered its DDL from
today's class would emit tomorrow's schema for yesterday's history, which is the
opposite of what a migration is for. The literal is written by hand and this
gate is what keeps the hand honest.

Constraint text is read as string literals via the AST, not as raw source. An
earlier version searched the text and could not find a constraint that ruff had
wrapped across implicitly concatenated fragments, because the quotes and the
join sat in the middle of the needle. Python already concatenates those into one
constant; asking the parser is simpler than telling authors how to format.
"""

from __future__ import annotations

import ast
import importlib
import re
import sys
from pathlib import Path

SRC = Path("apps/api/src")
sys.path.insert(0, str(SRC.resolve()))

from sqlalchemy import CheckConstraint  # noqa: E402

from bazaarwatch.core.models import Base  # noqa: E402

VERSIONS = SRC / "bazaarwatch" / "migrations" / "versions"
MODULES = SRC / "bazaarwatch" / "modules"

# `role IN ('contributor', 'moderator')`. Anything else is a CHECK expressing
# something other than a vocabulary and is not this gate's business.
ENUM_CHECK = re.compile(r"\A\s*(\w+)\s+IN\s+\('.*'\)\s*\Z")

_WHITESPACE = re.compile(r"\s+")


def _normalise(value: str) -> str:
    return _WHITESPACE.sub(" ", value).strip()


def _register_every_model() -> None:
    """Import every module's models so they land on `Base.metadata`.

    Discovered rather than listed. A hand-maintained import list is one a module
    can be missing from, and a module missing from it is invisible here: the
    constraints exist, the gate counts fewer than there are, and it passes. That
    is not hypothetical. This gate reported three constraints while `geo` had
    added four more, and reported success.
    """
    for models_file in sorted(MODULES.glob("*/models.py")):
        importlib.import_module(f"bazaarwatch.modules.{models_file.parent.name}.models")


def enum_checks() -> list[tuple[str, str, str]]:
    """(table, constraint name, expression) for every enum-shaped CHECK."""
    _register_every_model()
    found = []
    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            if not isinstance(constraint, CheckConstraint):
                continue
            expression = str(constraint.sqltext)
            if ENUM_CHECK.match(expression):
                found.append((table.name, str(constraint.name), _normalise(expression)))
    return sorted(found)


def _resolve(argv: list[str], default: list[Path]) -> list[Path]:
    """Explicit paths must exist.

    A gate handed a path that is not there used to filter it away and report
    that everything it checked was clean, which is true and useless: zero files
    checked is a clean run. The message then blamed the caller's assertion
    instead of the missing file.
    """
    if not argv:
        return default
    paths = [Path(arg) for arg in argv]
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise SystemExit(f"no such file: {', '.join(missing)}")
    return paths


def main(argv: list[str]) -> int:
    if argv:
        paths = [Path(arg) for arg in argv]
    elif VERSIONS.is_dir():
        paths = sorted(VERSIONS.glob("*.py"))
    else:
        print(f"No migrations at {VERSIONS}", file=sys.stderr)
        return 1

    literals = []
    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            print(f"{path}: could not be parsed: {exc}", file=sys.stderr)
            return 1
        literals += [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
    migrations = {_normalise(literal) for literal in literals}

    checks = enum_checks()
    if not checks:
        print("enum parity: no enum-backed CHECK constraints found", file=sys.stderr)
        return 1

    missing = [entry for entry in checks if entry[2] not in migrations]
    if missing:
        print("Enum-backed CHECK constraints that no migration creates:")
        for table, name, expression in missing:
            print(f"  {table}.{name}: {expression}")
        print("\nThe models and the database disagree. Write a migration that drops and")
        print("recreates the constraint with the expression above.")
        return 1

    print(f"enum parity: {len(checks)} constraint(s) checked, all present in migrations")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
