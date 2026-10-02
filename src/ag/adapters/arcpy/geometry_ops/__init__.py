"""The ArcPy implementation of `GeometryOps`, one module per method group.

Membership test: a module here holds one group class with Protocol methods of
`GeometryOps` only, plus module-level private helpers that take the session as an
argument. `__init__` composes the groups into `ArcpyGeometryOps` with an empty body.
Group modules never import each other.
"""
