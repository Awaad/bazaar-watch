# Security

## Reporting

Report suspected vulnerabilities privately. Do not open a public issue.

<!-- TODO: security contact address, before the repository becomes public. -->

Expect an acknowledgement within 72 hours.

## What this system holds

Most of the corpus is not personal data: a shelf price is a fact about a shop.
Sensitivity concentrates in a few places, and reports touching them are treated
as high severity:

- **Receipt images**, which carry one person's complete basket at one place and
  time, plus card digits and loyalty numbers.
- **Phone numbers**, which are the identifier and the authentication factor.
- **Receipt-level grouping**, which is a basket even after the contributor
  reference is severed, and is re-identifying in a small market.

Anything permitting a contributor to view another contributor's receipt image,
basket composition, or identity is high severity regardless of how it is
reached.

See `docs/12-security-compliance.md`.

## Out of scope

Reports concerning published price data, branch locations or index figures.
These are intended to be public.
