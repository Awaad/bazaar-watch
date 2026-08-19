# CI gates

Each script exits non-zero on a violation and takes an optional list of files;
with no arguments it scans everything tracked by git.

They exist because the corresponding mistake produces **no error and no test
failure**, only quietly wrong data discovered weeks later. See
`docs/15-repo-structure-standards.md`.

| Gate | Guards | ADR |
|---|---|---|
| `no-naive-casing.sh` | Turkish dotted and dotless i corrupting lexicon keys | 0025 |
| `no-float-money.sh` | Float arithmetic on prices | 0004 |
| `no-naive-datetime.sh` | Naive datetimes written to `TIMESTAMPTZ` | 0002 |
| `updated-at-triggers.py` | A mutable table whose `updated_at` silently stops changing | 0002 |
| `workflow-jobs.py` | A CI job dedented out of `jobs`, so it never runs | |
| `enum-parity.py` | An enum gaining a member that no migration adds to its `CHECK` | 0042 |

Gates added as the code they guard appears:

| Gate | Arrives with |
|---|---|
| `branch-kind-predicate` | indexing and comparison queries (ADR-0045) |
| `observation-status-predicate` | observation aggregates (ADR-0082) |
| `no-handwritten-calls` | generated API clients (ADR-0042) |
| `no-literal-strings` | UI code (ADR-0026) |
| `no-server-formatting` | API responses (ADR-0004) |
| `i18n-parity` | locale files (ADR-0026) |

## Fixtures

`fixtures/` holds inputs a gate is run against to prove it fires. A gate that
has never failed has never been tested, and the tests in
`apps/api/tests/test_gates.py` run each gate over its fixtures and assert the
exit status.

Where the guarded mistake can be reintroduced directly, that is better evidence
than a fixture, and the slice README records it. `enum-parity` was proven by
adding a member to `UserRole` and watching it fail.

## Suppression

Every gate honours a trailing `# gate-ignore: <gate-name>` on the offending
line, and the line above it should say why.

The marker is deliberately **not** `# noqa`. Ruff owns that directive and warns
when it sees a value that is not a ruff rule code, so a custom gate sharing the
syntax produces a warning on every suppression.

Suppression is a review conversation, not a private decision: a `gate-ignore` in
a diff should be explained in the pull request.
