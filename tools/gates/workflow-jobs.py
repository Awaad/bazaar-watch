#!/usr/bin/env python3
"""Gate: every job in a GitHub Actions workflow is declared under `jobs`.

A job dedented to column zero is still valid YAML. `check-yaml` passes, nothing
local fails, and GitHub rejects the workflow. The only place that shows is the
Actions tab, so the failure is silent to anyone working from a terminal.

This repository ran ten slices with `mypy`, `import-linter` and `pytest` not
running in CI for exactly that reason: `api:` sat at the top level instead of
under `jobs:`, which made it an unrecognised workflow key.

Two checks per file, deliberately narrow:

  1. Every top-level key is one GitHub Actions recognises.
  2. `jobs` exists and is a non-empty mapping.

This is not a workflow linter. `actionlint` is, and it checks expressions,
action inputs, shell syntax and much else. It is a Go binary, which is a
toolchain this repository does not otherwise need; adopting it is a separate
decision. These two checks need nothing but the YAML parser and catch the
mistake that actually happened.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

WORKFLOW_DIR = Path(".github/workflows")

# https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions
# `on` is absent because YAML 1.1 resolves the bare word to the boolean True,
# which is what the parser hands back and what is checked for below.
TOP_LEVEL_KEYS = frozenset(
    {
        "name",
        "run-name",
        "permissions",
        "env",
        "defaults",
        "concurrency",
        "jobs",
    }
)


def _describe(key: object) -> str:
    # `on:` arrives as True. Reporting it as `True` would send a reader looking
    # for a key they never wrote.
    return "on" if key is True else repr(key)


def _check(path: Path) -> list[str]:
    try:
        document: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"{path}: not parseable as YAML: {exc}"]

    if not isinstance(document, dict):
        return [f"{path}: top level is {type(document).__name__}, expected a mapping"]

    problems = []
    for key in document:
        if key is not True and key not in TOP_LEVEL_KEYS:
            problems.append(
                f"{path}: unrecognised top-level key {_describe(key)}. "
                "A job belongs under `jobs:`, indented two spaces."
            )

    jobs = document.get("jobs")
    if jobs is None:
        problems.append(f"{path}: no `jobs` key, so this workflow runs nothing")
    elif not isinstance(jobs, dict) or not jobs:
        problems.append(f"{path}: `jobs` is empty")

    return problems


def main(argv: list[str]) -> int:
    if argv:
        paths = [Path(arg) for arg in argv]
    elif WORKFLOW_DIR.is_dir():
        paths = sorted(p for p in WORKFLOW_DIR.iterdir() if p.suffix in {".yml", ".yaml"})
    else:
        # No workflows is not a failure. A repository without CI is a choice.
        return 0

    problems = [problem for path in paths for problem in _check(path)]
    if problems:
        print("Workflow structure:")
        for problem in problems:
            print(f"  {problem}")
        return 1

    print(f"workflow jobs: {len(paths)} workflow(s) checked, all well formed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
