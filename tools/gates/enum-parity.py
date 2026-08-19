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

Keep a rendered constraint on one source line. This reads the migration text, so
a constraint split across implicitly concatenated string fragments will not be
found even though it is correct.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path("apps/api/src").resolve()))

from sqlalchemy import CheckConstraint

from bazaarwatch.core.models import Base

# Importing the models registers them on Base.metadata. Every module owning
# tables belongs here; a module missing from this list is invisible to the gate.
from bazaarwatch.modules.identity import models as _identity  # noqa: F401

VERSIONS = Path("apps/api/src/bazaarwatch/migrations/versions")

# `role IN ('contributor', 'moderator')`. Anything else is a CHECK expressing
# something other than a vocabulary and is not this gate's business.
ENUM_CHECK = re.compile(r"\A\s*(\w+)\s+IN\s+\('.*'\)\s*\Z")

_WHITESPACE = re.compile(r"\s+")


def _normalise(value: str) -> str:
    return _WHITESPACE.sub(" ", value).strip()


def enum_checks() -> list[tuple[str, str, str]]:
    """(table, constraint name, expression) for every enum-shaped CHECK."""
    found = []
    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            if not isinstance(constraint, CheckConstraint):
                continue
            expression = str(constraint.sqltext)
            if ENUM_CHECK.match(expression):
                found.append((table.name, str(constraint.name), _normalise(expression)))
    return sorted(found)


def main(argv: list[str]) -> int:
    if argv:
        paths = [Path(arg) for arg in argv]
    elif VERSIONS.is_dir():
        paths = sorted(VERSIONS.glob("*.py"))
    else:
        print(f"No migrations at {VERSIONS}", file=sys.stderr)
        return 1

    migrations = _normalise("\n".join(p.read_text(encoding="utf-8") for p in paths))

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
