"""Reusable composites below the operation level, one module per subject (lines,
polygons, points, topology, attributes, extents).

Membership test, the promotion rule of ADR-0005: a private helper moves here when a
second object needs it. A helper takes the toolbox and scratch as arguments, has no
`@operation` decorator, and never imports `operations`.
"""
