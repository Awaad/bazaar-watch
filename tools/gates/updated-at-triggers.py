#!/usr/bin/env python3
"""Gate: every table with an `updated_at` column has a trigger maintaining it.

An application-maintained timestamp is wrong the moment anything writes outside
the ORM, which migrations and operational fixes both do. A missing trigger
produces no error and no test failure: the column simply stops changing, and
nobody notices for months.

Scans the migration set, collects tables that create an `updated_at` column, and
requires a matching `CREATE TRIGGER ... ON <table>` somewhere in the same set.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

VERSIONS = Path("apps/api/src/bazaarwatch/migrations/versions")

CREATE_TABLE = re.compile(r'op\.create_table\(\s*"(?P<table>\w+)"(?P<body>.*?)\n    \)', re.S)
UPDATED_AT = re.compile(r'sa\.Column\(\s*"updated_at"')
TRIGGER_ON = re.compile(r"CREATE TRIGGER\s+\S+\s+BEFORE UPDATE ON\s+\{?(?P<table>\w+)\}?", re.I)
TRIGGER_LOOP = re.compile(r"for table in \(([^)]*)\)")


def _upgrade_body(source: str) -> str:
    """Only `upgrade()` creates triggers. `downgrade()` drops them, and counting
    those would let a missing CREATE pass because the matching DROP is present."""
    start = source.find("def upgrade()")
    if start < 0:
        return ""
    end = source.find("def downgrade()", start)
    return source[start:end] if end > 0 else source[start:]


def main() -> int:
    if not VERSIONS.is_dir():
        return 0

    files = sorted(VERSIONS.glob("*.py"))
    source = "\n".join(p.read_text(encoding="utf-8") for p in files)
    upgrades = "\n".join(_upgrade_body(p.read_text(encoding="utf-8")) for p in files)

    needs: set[str] = {
        m.group("table")
        for m in CREATE_TABLE.finditer(source)
        if UPDATED_AT.search(m.group("body"))
    }

    has: set[str] = {
        m.group("table")
        for m in TRIGGER_ON.finditer(upgrades)
        if m.group("table") != "table"  # f-string placeholder, resolved below
    }
    # Triggers created in a loop over a tuple of table names.
    if "CREATE TRIGGER" in upgrades:
        for m in TRIGGER_LOOP.finditer(upgrades):
            has.update(re.findall(r'"(\w+)"', m.group(1)))

    missing = sorted(needs - has)
    if missing:
        print("Tables with updated_at and no trigger maintaining it:")
        for table in missing:
            print(f"  {table}")
        print("\nAdd: CREATE TRIGGER trg_<table>_updated_at BEFORE UPDATE ON <table>")
        print("     FOR EACH ROW EXECUTE FUNCTION set_updated_at();")
        return 1

    print(f"updated_at triggers: {len(needs)} table(s) checked, all covered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
