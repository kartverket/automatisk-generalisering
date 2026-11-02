"""The constrained ArcPy stub: the names the ArcPy adapter may reach on `arcpy` directly.

It declares nothing yet. Pyright applies this stub to `src/ag/adapters/arcpy/` and
`tests/support/arcpy/`, so every attribute of `arcpy` is an error there: a tool goes
through the session's `run_tool`, and `arcpy.env` and the vendor exceptions are the
session's alone; `ag.adapters.arcpy.session` states the rule and cites its record. A
non-tool name that a group module needs on the engine directly, such as a cursor class,
is declared here with its reason in the same pull request, and never widened for an
editor's sake. This stub does not cover a submodule import such as
`import arcpy.management`, and attributes reached through one are not checked; the static
scan refuses that form.
"""
