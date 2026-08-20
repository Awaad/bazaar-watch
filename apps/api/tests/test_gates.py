"""A gate that has never failed has never been tested.

Each gate is run as a subprocess over its fixtures, because that is the entry
point CI and pre-commit use. Importing the module instead would test a code path
nothing else takes.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

GATES = Path("tools/gates")
FIXTURES = GATES / "fixtures"


def _run(gate: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GATES / gate), *args],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "fixture",
    ["dedented-job.yml", "no-jobs.yml"],
)
def test_workflow_gate_fires(fixture: str) -> None:
    result = _run("workflow-jobs.py", str(FIXTURES / "workflow-jobs" / fixture))
    assert result.returncode == 1, result.stdout


def test_workflow_gate_passes_a_well_formed_workflow() -> None:
    result = _run("workflow-jobs.py", str(FIXTURES / "workflow-jobs" / "valid.yml"))
    assert result.returncode == 0, result.stdout


def test_workflow_gate_names_the_dedented_job() -> None:
    """The message has to say which key, or the reader has to diff the file
    against the docs to find it."""
    result = _run("workflow-jobs.py", str(FIXTURES / "workflow-jobs" / "dedented-job.yml"))
    assert "'test'" in result.stdout


def test_the_real_workflow_declares_its_jobs_under_jobs() -> None:
    """This failed for ten slices: `api` sat at the top level, so mypy,
    import-linter and pytest ran nowhere but a laptop."""
    result = _run("workflow-jobs.py")
    assert result.returncode == 0, result.stdout


def test_enum_parity_gate_fires_when_a_migration_lacks_the_constraint() -> None:
    result = _run("enum-parity.py", str(FIXTURES / "enum-parity" / "stale.py"))
    assert result.returncode == 1, result.stdout
    assert "role IN ('contributor', 'moderator', 'operator', 'admin')" in result.stdout


def test_enum_parity_gate_passes_against_the_real_migrations() -> None:
    result = _run("enum-parity.py")
    assert result.returncode == 0, result.stdout + result.stderr


def _gate_scripts(text: str) -> set[str]:
    return set(re.findall(r"tools/gates/([\w.-]+\.(?:sh|py))", text))


def test_make_gates_and_pre_commit_run_the_same_set() -> None:
    """Two lists of gates, maintained separately. A gate added to one and not
    the other simply does not run there, and nothing says so."""
    makefile = Path("Makefile").read_text(encoding="utf-8")
    target = makefile[makefile.index("\ngates:") :]
    target = target[: target.index('@echo "gates passed"')]

    config = yaml.safe_load(Path(".pre-commit-config.yaml").read_text(encoding="utf-8"))
    hook_entries = "\n".join(
        str(hook.get("entry", "")) for repo in config["repos"] for hook in repo.get("hooks", [])
    )

    assert _gate_scripts(target) == _gate_scripts(hook_entries)


def test_every_gate_script_is_registered() -> None:
    """A gate in the directory that neither list runs is decoration."""
    on_disk = {p.name for p in GATES.iterdir() if p.suffix in {".sh", ".py"}}
    makefile = Path("Makefile").read_text(encoding="utf-8")
    assert on_disk <= _gate_scripts(makefile)


BRANCH_SCOPE = FIXTURES / "branch-scope" / "modules"
UPDATED_AT = FIXTURES / "updated-at-triggers"


@pytest.mark.parametrize(
    "fixture",
    ["indexing/violation_orm.py", "search/violation_sql.py", "economy/violation_sql.py"],
)
def test_branch_scope_gate_fires(fixture: str) -> None:
    result = _run("branch-scope.py", str(BRANCH_SCOPE / fixture))
    assert result.returncode == 1, result.stdout


@pytest.mark.parametrize(
    "fixture",
    [
        "indexing/clean.py",
        # Prose and a local variable are not access. The first version of this
        # gate matched a regex over raw lines and rejected both, which is the
        # false-positive failure ADR-0088 argues against.
        "indexing/clean_local_name.py",
        "geo/clean_sql.py",
    ],
)
def test_branch_scope_gate_allows_correct_code(fixture: str) -> None:
    result = _run("branch-scope.py", str(BRANCH_SCOPE / fixture))
    assert result.returncode == 0, result.stdout


def test_branch_scope_gate_points_at_the_selectables() -> None:
    """A gate that says no without saying what to do instead gets suppressed."""
    result = _run("branch-scope.py", str(BRANCH_SCOPE / "indexing/violation_orm.py"))
    assert "index_eligible_branches()" in result.stdout
    assert "ADR-0088" in result.stdout


def test_branch_scope_gate_passes_against_the_real_tree() -> None:
    result = _run("branch-scope.py")
    assert result.returncode == 0, result.stdout


def _found(*fixtures: str) -> set[str]:
    result = _run("updated-at-triggers.py", "--found", *[str(UPDATED_AT / f) for f in fixtures])
    return set(result.stdout.split())


def test_updated_at_gate_sees_a_trigger_loop_over_a_module_constant() -> None:
    """The f-string in the loop never spells the trigger name out. Requiring it
    to would mean shaping migrations to suit a parser."""
    assert _found("loop-over-constant.py") == {"widgets"}


def test_updated_at_gate_resolves_each_revisions_own_constant() -> None:
    """Two revisions can both call their tuple `_UPDATED_AT_TABLES`. Resolving
    it against the concatenated source finds the first and misses the rest."""
    assert _found("loop-over-constant.py", "second-revision-same-constant.py") == {
        "widgets",
        "gadgets",
    }


def test_updated_at_gate_does_not_care_about_formatting() -> None:
    """An earlier version matched where `op.create_table(...)` put its closing
    parenthesis, and called a correct migration broken."""
    assert _found("awkward-formatting.py") == {"widgets", "sprockets"}


def test_updated_at_gate_finds_nothing_when_no_trigger_is_created() -> None:
    assert _found("missing-trigger.py") == set()


def test_updated_at_gate_passes_against_the_real_migrations() -> None:
    """Which tables need a trigger comes from the ORM metadata now. Parsing it
    out of the migrations made the gate blind to a column written by a helper,
    and it passed while missing two tables in migration 0005."""
    result = _run("updated-at-triggers.py")
    assert result.returncode == 0, result.stdout
