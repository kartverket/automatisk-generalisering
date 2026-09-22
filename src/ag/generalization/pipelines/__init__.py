"""Stage and pipeline declarations, one directory per (object, scale) and one module per
stage.

Membership test: the module declares `Derived` objects, a `Handles` class and its
`Stage`, or a `Pipeline`. It imports `operations` for declarations only and runs nothing
at import.
"""
