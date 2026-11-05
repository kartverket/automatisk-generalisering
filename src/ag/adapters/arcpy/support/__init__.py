"""Engine-bound code that more than one method group of the ArcPy adapter needs.

Membership test: it may call the engine through the session; a second group module
needs it, now or as a named port method still to land, which the module docstring names
by ADR id; and it is named for the engine artefact it handles, such as `dataset_schema`
or `geometry_values`. A support module never imports a group module or a port package.
"""
