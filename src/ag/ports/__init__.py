"""The driven-port Protocols and the values that cross them.

One flat module per port Protocol, plus the value types, predicates, row-shape grammar,
column constants, capability record and port errors. Membership test: it is a Protocol a
second adapter could implement, or a value named in a Protocol signature. It imports
only `ag.core.handles`, `ag.core.types`, `ag.core.injection` and `ag.core.errors`.
"""
