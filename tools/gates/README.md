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

Gates added as the code they guard appears:

| Gate | Arrives with |
|---|---|
| `branch-kind-predicate` | indexing and comparison queries (ADR-0045) |
| `observation-status-predicate` | observation aggregates (ADR-0082) |
| `no-handwritten-calls` | generated API clients (ADR-0042) |
| `no-literal-strings` | UI code (ADR-0026) |
| `no-server-formatting` | API responses (ADR-0004) |
| `updated-at-triggers` | the first migration carrying `updated_at` |
| `enum-parity` | the first `StrEnum` backed by a `CHECK` constraint |

## Suppression

Every gate honours a trailing `# noqa: <gate-name>` on the offending line.
Suppression is a review conversation, not a private decision: a `noqa` in a
diff should be explained in the pull request.
