"""The ArcPy adapter: the session, the base class and one package per port.

The root holds `session.py`, `_base.py`, `support/` and the port packages, and nothing
else. Membership test: the code needs ArcPy. Any module here may import `arcpy` for the
non-tool names declared in `typings/arcpy/`; tools, `arcpy.env` and vendor exceptions
are reached through `session.py` only.
"""
