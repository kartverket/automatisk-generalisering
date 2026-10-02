"""TEMPLATE — PARTIAL. Target package: `src/ag/adapters/arcpy/`.

The arcpy adapter. Only `predicates.py` exists so far, and it is the half that needs
no arcpy: the De Morgan rewrite that makes ADR-0001's predicate algebra expressible
against a tool that can only invert at a leaf.

Still to write: `session.py` (the one lazily-bound `import arcpy` in the whole system,
plus environment, licence, handle release and the `GetMessages()` drain),
`geometry_ops.py`, `table_ops.py`, `cartographic_ops.py`, `geometry.py` (the
`Geometry` <-> `arcpy.Polyline` converters) and `errors.py`.

WHY THE PURE PART CAME FIRST. `push_negation` is the only place the design claims
something non-obvious about the predicate model - that a tree of `And`/`Or`/`Not` can
be driven through an API that inverts single predicates and nothing else. That claim
is testable with tuples, on any machine, with no licence. Everything else in this
package is a translation table.
"""
