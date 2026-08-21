#!/usr/bin/env python3
"""Gate: aggregates reach branches and observations only through selectables.

ADR-0045 keeps online branches out of indices and access-scoped comparison.
ADR-0023 keeps unverified branches out of the same. Two predicates, from two
records, for two unrelated reasons, and omitting either produces a plausible
number rather than an error. The number then gets published, and ADR-0079
forbids restating a published figure: the remedy is an erratum.

ADR-0088 moves the exclusions into `geo.service.index_eligible_branches()` and
`geo.service.public_branches()`. ADR-0090 does the same for observations, where
the trap is worse: `price_observations` keeps superseded rows by design, so the
count grows every time the extraction model improves. This gate enforces both.

Two rules:

  1. The restricted modules do not import the owning module's `models` and do
     not use the guarded class names. They ask the service for a scope.
     `modules/economy` is restricted for observations and not for branches,
     because bounty payout aggregates over observations and paying twice for a
     reprocessed receipt is the same defect wearing different clothes.

  2. No string anywhere outside the owning module and the migrations contains
     SQL naming a guarded table. Rule 1 cannot see inside a string.

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

# (guarded class, owning module, table, modules that must go through a scope,
#  the advice to print). One entry per protected table.
GUARDS = (
    (
        "Branch",
        "geo",
        "branches",
        ("modules/indexing", "modules/search"),
        "geo.service.index_eligible_branches() or public_branches(), which carry "
        "the ADR-0045 and ADR-0023 exclusions (ADR-0088)",
    ),
    (
        "PriceObservation",
        "observations",
        "price_observations",
        ("modules/indexing", "modules/search", "modules/economy"),
        "observations.service.countable_observations() or unresolved_observations(), "
        "which carry the status and resolution exclusions (ADR-0090)",
    ),
)

RAW_SQL_TEMPLATE = r"\b(?:FROM|JOIN|UPDATE|INTO)\s+{table}\b"

IGNORE = re.compile(r"#\s*gate-ignore:\s*branch-scope")


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


def _check_guard(
    tree: ast.Module, guard: tuple[str, str, str, tuple[str, ...], str], path: Path
) -> list[tuple[int, str]]:
    name, module, table, restricted, advice = guard
    owning_import = f"bazaarwatch.modules.{module}.models"
    problems: list[tuple[int, str]] = []

    if _under(path, restricted):
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(owning_import):
                problems.append((node.lineno, f"imports {owning_import}. Use {advice}."))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(owning_import):
                        problems.append((node.lineno, f"imports {alias.name}. Use {advice}."))
            elif (isinstance(node, ast.Name) and node.id == name) or (
                isinstance(node, ast.Attribute) and node.attr == name
            ):
                problems.append((node.lineno, f"uses the name `{name}`. Use {advice}."))

    if not _under(path, (f"modules/{module}", "migrations")):
        pattern = re.compile(RAW_SQL_TEMPLATE.format(table=table), re.IGNORECASE)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and pattern.search(node.value)
            ):
                problems.append(
                    (
                        node.lineno,
                        f"raw SQL against the {table} table outside {module}. "
                        f"The exclusions cannot be applied to it. Use {advice}.",
                    )
                )

    return problems


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
        for guard in GUARDS:
            found += _check_guard(tree, guard, path)

        suppressed = _suppressed(source)
        problems += [
            f"{path}:{line}: {message}"
            for line, message in sorted(set(found))
            if line not in suppressed
        ]
    return problems


def main(argv: list[str]) -> int:
    paths = _resolve(argv, sorted(SRC.rglob("*.py")))

    problems = check(paths)
    if problems:
        print("Scope (ADR-0088, ADR-0090):")
        for problem in problems:
            print(f"  {problem}")
        return 1

    print(f"branch scope: {len(paths)} file(s) checked, all clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
