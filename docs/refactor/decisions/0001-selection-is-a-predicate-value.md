# ADR-0001: Selection is a composable predicate value, not a held selection

**Status:** Accepted

## Context

Two selection outcomes are needed: select and materialise a new dataset, and build a
selection up in stages by adding to, removing from and subsetting it. arcpy expresses the
second with a mutable selection set on a feature layer, mutated by successive
`SelectLayerBy*` calls with `NEW_SELECTION` / `ADD_TO_SELECTION` / `REMOVE_FROM_SELECTION` /
`SUBSET_SELECTION`. The make-layer/select triple is 616 call sites.

## Decision

`GeometryOps` exposes `select(input, where: Predicate, output)` and
`count(input, where) -> int`. `Predicate` is an immutable algebra — `Attr`, `Spatial`, `And`,
`Or`, `Not` — with `&`, `|` and `~` as constructors. No mutable selection crosses the port.

`any()` is not shipped. It pays only where a backend can short-circuit (SQL `EXISTS`,
`LIMIT 1`); arcpy's `GetCount` cannot, and `count(...) > 0` covers the case until a backend
benefits.

## Consequences

A held selection is arcpy's implementation, not the concept: in SQL and dataframe engines
"add to" is `Or`, "remove from" is `And Not`, "subset" is `And`. Exposing the handle would
make every future adapter emulate arcpy's statefulness.

The tree maps almost directly onto OGC CQL2, and to a `WHERE` clause in a SQL adapter.

The predicate is lazier than a held selection: nothing materialises until `select`.

The arcpy adapter carries the awkwardness. arcpy inverts only at a leaf
(`invert_where_clause`, `invert_spatial_relationship`), so `Not(And(...))` has no direct
representation and the adapter must push negation to the leaves by De Morgan. This produces
an adapter-internal `Negated` node that never crosses the port boundary.

`CopyFeatures` (282 sites) is materialisation, not selection, and survives as the output
write inside `select`.
