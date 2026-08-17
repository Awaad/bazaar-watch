## What

<!-- One paragraph. What changes and why. -->

## Checklist

Delete rows that do not apply; do not delete rows that do.

- [ ] Changes a decision recorded in an ADR, and includes the **superseding ADR**.
      Accepted records are never edited in place.
- [ ] Touches `docs/03-data-model.md`, and includes the **Alembic migration**.
- [ ] Adds or changes an endpoint, and includes the **regenerated spec and clients**
      in the same commit, so the diff shows what clients will see. (ADR-0042)
- [ ] Adds a `# noqa: <gate>` suppression, explained below.
- [ ] Touches a service-layer privacy invariant (reviewer independence, one line per
      receipt per reviewer, submission ownership) and the **adversarial tests** still pass
      and are not skipped. (ADR-0048, ADR-0059, ADR-0085)
- [ ] Adds a tuning constant, and it is in `config/tuning.json`, not in code or a DDL
      default. (ADR-0021)

## Suppressions

<!-- Any noqa added, and why. A suppression is a review conversation. -->
