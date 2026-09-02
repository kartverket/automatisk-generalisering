# ADR-0002: Three geoprocessing ports rather than one or many

**Status:** Accepted

## Context

The system must be able to replace arcpy on need. The replacement cannot be a single cutover: some
calls have near-1:1 equivalents elsewhere (`buffer`, `dissolve`, `clip`), while the
cartography toolbox has none and each member needs hundreds to thousands of lines to
reproduce. Measured in this repository, cartography is 78 of 2801 tool call sites (2.8%)
across 16 distinct tools.

## Decision

Split the geoprocessing seam into `GeometryOps` (primitive dataset operations, 25–35
methods), `TableOps` (schema, attributes, bulk row IO, 10–15) and `CartographicOps` (named
ICA generalization operators, 8–12).

## Consequences

Migration becomes incremental and its progress measurable: `TableOps` first, then
`GeometryOps`, then cartographic operators one at a time — each written against the other two
ports rather than a new library directly, so the arcpy `CartographicOps` adapter shrinks
method by method.

With a single port, no non-arcpy adapter could ship until every cartographic algorithm was
reimplemented. All-or-nothing cutovers are what kill migrations.

`CartographicOps` will eventually hold thick implementations that adapt nothing. Those move
to `cartography/`, which is why the port must not name arcpy concepts.

An operation may need two or three ports injected rather than one. See ADR-0008.

Whether `CartographicOps` should split further per operator is Q-B, deferred until at least
one operator is reimplemented.
