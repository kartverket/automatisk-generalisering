"""Reusable composites below the operation level, one module per subject (lines,
polygons, points, topology, attributes, extents).

Membership test (ADR-0018 AR-D21) and the promotion rule of 03-architecture §5: a private
helper moves here when a
second object needs it. A helper takes the toolbox and scratch as arguments, has no
`@operation` decorator, and never imports `operations`.
"""
