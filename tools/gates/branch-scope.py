#!/usr/bin/env python3
"""Gate: index and comparison code reaches branches only through the selectables.

ADR-0045 keeps online branches out of indices and access-scoped comparison.
ADR-0023 keeps unverified branches out of the same. Two predicates, from two
records, for two unrelated reasons, and omitting either produces a plausible
number rather than an error. The number then gets published, and ADR-0079
forbids restating a published figure: the remedy is an erratum.

ADR-0088 moves the exclusions into `geo.service.index_eligible_branches()` and
`geo.service.public_branches()`. This gate is the enforcement.

Two rules:

  1. `modules/indexing` and `modules/search` do not import `geo.models` and do
     not use the name `Branch`. They ask `geo.service` for a scope. `search`
     may not import `geo` at all under the module map, so for it this is mostly
     about rule 2, which is the right answer: search reaches branches through
     `catalog`.

  2. No string anywhere outside `modules/geo` and the migrations contains SQL
     naming the `branches` table. Rule 1 cannot see inside a string.

This reads the AST, not the lines. A first version matched a regex over raw
text and immediately fired on the word `branches` in a docstring and on a local
variable holding a scope, which is the false-positive failure ADR-0088 uses to
argue against the gate `docs/15` originally described. Comments and prose are
not code and are never examined; a local named `branches` is allowed, because
holding a scope in a well named variable is the pattern, not the violation.

What this deliberately does not do is inspect a query for the predicate. See
ADR-0088 for why that cannot be written honestly.

This gate is aimed at forgetting, not at circumvention. Anyone determined to
query `branches` from `indexing` can alias the import and do it, and will have
to write a `gate-ignore` and explain it in review, which is the point.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

SRC = Path("apps/api/src/bazaarwatch")

# Modules that compute or serve figures and must go through a scope.
RESTRICTED = ("modules/indexing", "modules/search")

# Where naming the table is the job.
SQL_ALLOWED = ("modules/geo", "migrations")

FORBIDDEN_NAME = "Branch"
FORBIDDEN_IMPORT = "bazaarwatch.modules.geo.models"

# `FROM branches`, `JOIN branches b`, `UPDATE branches SET`, `INTO branches`.
RAW_SQL = re.compile(r"\b(?:FROM|JOIN|UPDATE|INTO)\s+branches\b", re.IGNORECASE)

IGNORE = re.compile(r"#\s*gate-ignore:\s*branch-scope")

SCOPE_ADVICE = (
    "Use geo.service.index_eligible_branches() or public_branches(), which carry "
    "the ADR-0045 and ADR-0023 exclusions (ADR-0088)."
)


def _under(path: Path, prefixes: tuple[str, ...]) -> bool:
    # Matched on path segments rather than relative to SRC, so the fixture tree
    # under tools/gates/fixtures mirrors the module layout and exercises the
    # same code path CI takes.
    posix = path.as_posix()
    return any(f"/{prefix}/" in posix or posix.startswith(f"{prefix}/") for prefix in prefixes)


def _suppressed(source: str) -> set[int]:
    return {
        number for number, line in enumerate(source.splitlines(), start=1) if IGNORE.search(line)
    }


def _check_restricted(tree: ast.Module) -> list[tuple[int, str]]:
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(FORBIDDEN_IMPORT):
            problems.append((node.lineno, f"imports {FORBIDDEN_IMPORT}. {SCOPE_ADVICE}"))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(FORBIDDEN_IMPORT):
                    problems.append((node.lineno, f"imports {alias.name}. {SCOPE_ADVICE}"))
        elif (isinstance(node, ast.Name) and node.id == FORBIDDEN_NAME) or (
            isinstance(node, ast.Attribute) and node.attr == FORBIDDEN_NAME
        ):
            problems.append((node.lineno, f"uses the name `{FORBIDDEN_NAME}`. {SCOPE_ADVICE}"))
    return problems


def _check_raw_sql(tree: ast.Module) -> list[tuple[int, str]]:
    problems = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and RAW_SQL.search(node.value)
        ):
            problems.append(
                (
                    node.lineno,
                    "raw SQL against the branches table outside geo. The ADR-0045 "
                    "and ADR-0023 exclusions cannot be applied to it (ADR-0088).",
                )
            )
    return problems


def check(paths: list[Path]) -> list[str]:
    problems = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            problems.append(f"{path}: could not be parsed: {exc}")
            continue

        found: list[tuple[int, str]] = []
        if _under(path, RESTRICTED):
            found += _check_restricted(tree)
        if not _under(path, SQL_ALLOWED):
            found += _check_raw_sql(tree)

        suppressed = _suppressed(source)
        problems += [
            f"{path}:{line}: {message}"
            for line, message in sorted(set(found))
            if line not in suppressed
        ]
    return problems


def main(argv: list[str]) -> int:
    paths = [Path(arg) for arg in argv] if argv else sorted(SRC.rglob("*.py"))
    paths = [p for p in paths if p.suffix == ".py" and p.is_file()]

    problems = check(paths)
    if problems:
        print("Branch scope (ADR-0088):")
        for problem in problems:
            print(f"  {problem}")
        return 1

    print(f"branch scope: {len(paths)} file(s) checked, all clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
