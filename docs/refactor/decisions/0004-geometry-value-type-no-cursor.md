# ADR-0004: Geometry as a value type; no cursor in the port

**Status:** Accepted

## Context

`SearchCursor`, `UpdateCursor` and `InsertCursor` are 483 call sites and the least portable
arcpy API: streaming row iterators with a vendor field-token language (`SHAPE@`, `OID@`,
`SHAPE@XY`). Separately, some logic manipulates geometry values in Python rather than whole
datasets — `line_topology.py` builds `arcpy.Polyline(arcpy.Array([...]))` and reads
`.firstPoint` / `.lastPoint`.

## Decision

`TableOps` has no cursor. Three shapes replace it: `calculate_field(input, field, expression)`
declaratively, `read_rows(input, fields) -> Iterable[Row]` in bulk, and
`write_rows(output, schema, rows)` in bulk.

`ports/geometry.py` defines an immutable `Geometry` value type — geometry kind, coordinate
sequence, CRS — which `read_rows` yields and `write_rows` accepts.

## Consequences

Target engines are vectorized, where a row loop is idiomatically wrong and orders of magnitude
slower. A faithful cursor port would make the slowest arcpy-shaped pattern part of the
contract and guarantee a bad second adapter.

These 483 sites are the most expensive part of the migration and the least mechanically
translatable. That cost is accepted deliberately.

Row-level geometry algorithms survive the migration, because they manipulate `Geometry`
rather than `arcpy.Polyline`. Conversion at the adapter boundary is near-mechanical:
`arcpy.Polyline(arcpy.Array(pts))` ↔ `LineString(coords)`, `.firstPoint` ↔ `coords[0]`.

Workarounds for arcpy cursor limitations disappear. `_GeneratedLineRecord` exists only to
buffer rows because arcpy cannot insert while an `UpdateCursor` is open.
