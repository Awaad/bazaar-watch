# ADR-0044: Tile rendering and POI data are separate decisions

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

These are routinely treated as one map decision, and only one of them is a cost question.

Tile rendering is interchangeable. MapLibre, Mapbox and Protomaps produce comparable results and
differ on price and appearance.

POI data is not interchangeable, because commercial places APIs restrict **storage**. Building a
branch registry on one means the registry is licensed rather than owned.

## Decision

Two independent decisions.

**Tiles**: behind an interface, chosen on cost and appearance, swappable. MapLibre GL as the client.

**POI data**: Overture Places, chosen for ownership rather than coverage (ADR-0022). Not swappable
for a commercial places API, because storage restrictions would make the branch registry a rented
view.

## Consequences

Tile provider can change without touching the branch registry.

The POI decision is evaluated on licensing first and coverage second, which inverts the usual
comparison and is correct here.

If Overture coverage proves inadequate in residential districts, the fallback is manual survey rather
than a commercial API, because the licensing constraint does not relax.

Attribution requirements differ per decision and must be tracked separately.

## Alternatives considered

**One map provider for both.** Rejected. Couples a cheap reversible decision to an
expensive irreversible one.

**Google Places for both.** Rejected. Storage restrictions, and place data may not be used outside a
Google map.

**Self-hosted tiles from OpenStreetMap.** Available and reasonable; a cost decision within the tile
interface, not an architectural one.

## Revisit trigger

Tile costs change materially, which affects only the tile decision, or Overture coverage
proves inadequate, which affects only the POI decision.
