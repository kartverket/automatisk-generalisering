"""The declarable units of processing, scale-free, in one package per object plus
`shared`.

Membership test: the function is decorated with `@operation`, or it is the frozen config
class or a private helper of one. Modules here never import `ag.core.data_objects`,
`ag.core.pipeline`, `sources` or `products` (ADR-0003).
"""
