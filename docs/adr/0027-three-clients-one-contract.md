# ADR-0027: One Expo app, one operator console, one public web surface

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Three distinct audiences with genuinely different needs: contributors capturing in shops,
operators curating the catalog, and the public reading prices.

Workstreams run in parallel, frequently by different agents, which makes the boundary between
clients a coordination surface as much as a product one.

The operator console is where normalization throughput is won, and normalization is the bottleneck
of the entire system.

## Decision

Three clients over one versioned API: Expo contributor app, Next.js operator console,
Next.js public web.

Console and public web are separate applications rather than one with role-gated routes. Different
audiences, different auth, different deploy cadence, and the separation makes an operator surface
leaking to the public structurally harder rather than a matter of correct routing.

All three consume generated clients. Hand-written API calls fail CI (ADR-0042).

## Consequences

Backend capability is built once and consumed three times, so client work can proceed
in parallel against a generated mock server.

Three deploy targets and three sets of dependencies to maintain.

Shared UI between console and web must live in a package or be duplicated deliberately; duplication
is usually the better answer given how differently they read.

The console is the surface whose throughput determines whether the corpus grows, which makes it a
first-class product rather than an admin afterthought.

## Alternatives considered

**One Next.js app with role-gated console routes.** Rejected. The most sensitive
surface would share a bundle and a route table with the most public one.

**Console as a desktop or CLI tool.** Rejected. Review queues want a browser, and operators are not
necessarily engineers.

**No public web initially.** Reasonable and deferred by phase rather than by architecture. The
public surface lands in P4.

## Revisit trigger

Console and public web converge enough in audience and auth that separation costs more
than it protects, which is unlikely.
