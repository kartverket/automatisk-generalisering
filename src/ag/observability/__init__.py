"""Structured run records, the logging context and timing.

A horizontal leaf outside the layer stack. Membership test: the module imports the
standard library and `ag.core.types` only. Every package except `ag.core` may import it;
`ag.core` and `ag.generalization.pipelines` may not import the context accessor.
"""
