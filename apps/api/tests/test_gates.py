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
