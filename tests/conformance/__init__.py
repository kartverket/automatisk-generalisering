"""The adapter conformance suite: one module per port method group, parametrized over
adapters.

Membership test: the case drives a port Protocol, not the facade, and must hold for
every adapter. The in-memory adapter runs everywhere; the ArcPy cases carry the `arcpy`
marker and run under an ArcGIS Pro Python environment and, later, in the image.
"""
