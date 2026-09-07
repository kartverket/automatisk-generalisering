"""TEMPLATE — NOT YET WRITTEN. Target package: `src/ag/helpers/`. ADR-0005.

Reusable, object-agnostic, scale-agnostic functions that compose port calls. Called
only from inside operations, never named in a stage, never scheduled.

MEMBERSHIP TEST: an operation is decorated with `@operation`; a helper is not.

The template inlines its helpers as private functions beside the operations that use
them (`_build_topology`, `_repair_geometry` in `ag/operations/road/`). That is correct
under the promotion rule — a helper used by one object's operations stays next to
them, and moves here on a second caller from a different object. This package is
empty because that second caller does not exist yet, not because the layer is
undecided.

Subject axis when it fills: lines, polygons, points, topology, attributes, extents —
03-architecture §5.
"""
