# ADR-0022: POI source is the Overture Places theme specifically

**Status:** Accepted
**Accepted:** 2026-08-17
**Open parameter:** Overture recall in residential districts, pending a coverage run. The provider choice and licence separation are settled.
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Branches are where prices attach, and access-scoped comparison makes every basket read a
geographic query, so the branch registry is infrastructure rather than decoration.

Commercial places APIs restrict storage. Google Places imposes caching and retention limits and
prohibits using place data outside a Google map. Mapbox Search carries comparable storage
restrictions. Building a branch registry on either means renting your own table, which evaporates
if terms change or payment stops.

Overture is a mixed-licence dataset. The Places theme differs materially from the buildings and
transportation themes.

Measured on the Kyrenia harbour bounding box, Overture returned 639 POIs at 100% naming against
OpenStreetMap's 139 at 67.6%.

## Decision

POI data comes from the Overture **Places theme**, chosen for ownership rather than
coverage. Places carries no OpenStreetMap data and no share-alike obligation, so the derived branch
registry is genuinely ours.

Buildings and transportation are ODbL and must never enter the same derived database. Any
OpenStreetMap-derived data stays in separate files with its own attribution.

Foursquare-sourced records within Places carry Apache 2.0 and their own terms rather than CDLA;
filter on the `source` property if a purely CDLA dataset is wanted.

`operating_status` and per-record `confidence` are carried through to branch verification.

## Consequences

The branch registry is an owned asset rather than a licensed view, which matters
because it is the substrate for a commercial price dataset.

Licence separation must be structural, since joining CDLA data to ODbL data can make the result
subject to share-alike.

Coverage in residential districts is unmeasured. A sample record confirms `supermarket` exists in
the taxonomy and that independents such as `H.Gül Market` are present in Girne, but presence is not
recall.

Records lack chain attribution and often address, so promotion remains a genuine operator step
(ADR-0023).

## Alternatives considered

**Google Places.** Rejected on storage restrictions, not on coverage or price.

**Mapbox Search.** Rejected on the same grounds.

**OpenStreetMap directly.** Rejected. Lower coverage here, and ODbL share-alike over a commercial
derived database is a risk not worth taking.

**Manual survey only.** Not rejected. It is the correct approach for the first city and the pipeline
earns its place on expansion (ADR-0023).

## Revisit trigger

Residential bounding box coverage measurement. If recall is poor, the pipeline becomes an
audit tool for closures rather than a discovery mechanism.
