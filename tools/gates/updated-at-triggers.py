#!/usr/bin/env python3
"""Gate: every table with an `updated_at` column has a trigger maintaining it.

`updated_at` is maintained by the database, not the application, because an
application-maintained timestamp is wrong the moment anything writes outside the
ORM, which migrations and operational fixes both do.

A table created with the column and no trigger takes `DEFAULT now()` on insert
and then never changes again. Nothing errors, no test fails, and the staleness
of every row derived from it is quietly wrong.

This reads the AST rather than matching text. Three earlier versions matched
regexes against the source and misfired three times: on a trigger loop over a
module constant, on two revisions sharing a constant name, and on the exact
layout of a `op.create_table(...)` call. Each false positive was harmless and
each cost time, and formatting is not something a gate should have opinions
about.

Resolution is per file. Two revisions may both name their tuple
`_UPDATED_AT_TABLES`, and looking it up in the concatenated source finds
whichever came first.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

VERSIONS = Path("apps/api/src/bazaarwatch/migrations/versions")

TRIGGER_MARKERS = ("CREATE TRIGGER", "BEFORE UPDATE ON")


def _is_call(node: ast.AST, *, attr: str) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == attr
    )


def _first_string_arg(call: ast.Call) -> str | None:
    if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
        return call.args[0].value
    return None


def _upgrade(tree: ast.Module) -> ast.FunctionDef | None:
    """Only `upgrade()` creates triggers. `downgrade()` drops them, and counting
    those would let a missing CREATE pass because the matching DROP is present."""
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "upgrade":
            return node
    return None


def _module_constants(tree: ast.Module) -> dict[str, list[str]]:
    """Module-level sequences of strings, for `for table in NAME` to resolve."""
    constants: dict[str, list[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            value = ast.literal_eval(node.value)
        except ValueError:
            continue
        if isinstance(value, tuple | list) and all(isinstance(v, str) for v in value):
            constants[target.id] = list(value)
    return constants


def _string_parts(node: ast.AST) -> str:
    """Flatten a literal or an f-string to the text a reader would see.

    An f-string in a loop never spells the trigger name out. Only the literal
    parts are needed here, because the markers being looked for are literal.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            part.value
            for part in node.values
            if isinstance(part, ast.Constant) and isinstance(part.value, str)
        )
    return ""


def _creates_a_trigger(node: ast.AST) -> bool:
    return any(
        all(marker in _string_parts(child) for marker in TRIGGER_MARKERS)
        for child in ast.walk(node)
    )


def tables_needing_a_trigger(tree: ast.Module) -> set[str]:
    tables = set()
    for node in ast.walk(tree):
        if not _is_call(node, attr="create_table"):
            continue
        assert isinstance(node, ast.Call)
        name = _first_string_arg(node)
        if name is None:
            continue
        for argument in node.args[1:]:
            if _is_call(argument, attr="Column"):
                assert isinstance(argument, ast.Call)
                if _first_string_arg(argument) == "updated_at":
                    tables.add(name)
    return tables


def tables_with_a_trigger(tree: ast.Module) -> set[str]:
    upgrade = _upgrade(tree)
    if upgrade is None:
        return set()

    constants = _module_constants(tree)
    tables: set[str] = set()

    for node in ast.walk(upgrade):
        # A loop over a sequence of table names, inline or by constant.
        if isinstance(node, ast.For) and _creates_a_trigger(node):
            iterable = node.iter
            # `reversed(...)` and friends: look at what they wrap.
            if isinstance(iterable, ast.Call) and iterable.args:
                iterable = iterable.args[0]
            if isinstance(iterable, ast.Name):
                tables.update(constants.get(iterable.id, []))
            else:
                try:
                    value = ast.literal_eval(iterable)
                except ValueError:
                    continue
                if isinstance(value, tuple | list):
                    tables.update(str(v) for v in value)

        # A trigger written out for one named table.
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = node.value
            if all(marker in text for marker in TRIGGER_MARKERS):
                after = text.split("BEFORE UPDATE ON", 1)[1].strip().split()
                if after and after[0].isidentifier():
                    tables.add(after[0])

    return tables


def check(paths: list[Path]) -> list[str]:
    needs: set[str] = set()
    has: set[str] = set()
    problems: list[str] = []

    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            problems.append(f"{path}: could not be parsed: {exc}")
            continue
        needs |= tables_needing_a_trigger(tree)
        has |= tables_with_a_trigger(tree)

    problems += [
        f"{table}: has updated_at, no trigger maintains it" for table in sorted(needs - has)
    ]
    return problems


def main(argv: list[str]) -> int:
    if argv:
        paths = [Path(arg) for arg in argv]
    elif VERSIONS.is_dir():
        paths = sorted(VERSIONS.glob("*.py"))
    else:
        return 0

    problems = check(paths)
    if problems:
        print("Tables with updated_at and no trigger maintaining it:")
        for problem in problems:
            print(f"  {problem}")
        print("\nAdd: CREATE TRIGGER trg_<table>_updated_at BEFORE UPDATE ON <table>")
        print("     FOR EACH ROW EXECUTE FUNCTION set_updated_at();")
        return 1

    covered = len(
        {
            t
            for p in paths
            for t in tables_needing_a_trigger(ast.parse(p.read_text(encoding="utf-8")))
        }
    )
    print(f"updated_at triggers: {covered} table(s) checked, all covered")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
