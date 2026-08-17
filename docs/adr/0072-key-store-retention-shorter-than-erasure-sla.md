# ADR-0072: Key store backup retention must be shorter than the erasure SLA

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Crypto shredding works by making a key irrecoverable. If any copy of the key survives,
nothing was shredded.

Key stores are databases, and databases get backed up. Somebody applying sensible backup practice to
a key store a year from now would silently restore the ability to decrypt every past erasure.

This failure is invisible. No error is raised, no alarm fires, and the system appears to be working
correctly. It would surface only during an audit or an incident.

## Decision

Key store backup retention is **shorter** than the erasure service level agreement.

This appears in the backup runbook (`13-infra-devops.md`), not only in this record, because the
person who breaks it will be reading a runbook rather than an ADR.

It is verified quarterly as a scheduled operational check.

Backups of the key store are treated as a distinct asset class from database and object storage
backups, with their own rule, precisely because the intuition to make backups longer-lived is
correct everywhere else.

## Consequences

The erasure guarantee actually holds rather than appearing to.

Key store recovery from backup has a shorter window than other systems, which is an availability
trade accepted deliberately.

A quarterly check exists whose only purpose is to catch a configuration change nobody thought was
dangerous.

Documentation must state the reason, not just the rule, or the rule will be "corrected" by someone
optimising backup coverage.

## Alternatives considered

**Standard backup retention on the key store.** Rejected. Silently defeats every
erasure.

**No key store backups at all.** Rejected. A key store loss would render the entire media corpus
unreadable, which is a worse outcome than a short recovery window.

**Rely on documentation alone.** Rejected. The quarterly check exists because documentation is not a
control.

## Revisit trigger

The erasure SLA changes, which changes the retention ceiling.
