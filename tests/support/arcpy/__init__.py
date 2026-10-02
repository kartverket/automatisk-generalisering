"""The engine-touching fixture builders: small `.gdb` inputs written with ArcPy directly.

This package is the second root the constrained ArcPy stub applies to
(`pyproject.toml`, `[[tool.pyright.executionEnvironments]]`): tools go through
`ag.adapters.arcpy.session.run_tool`, rows through the stub's cursors, and a tool call,
`arcpy.env` or a vendor exception name is a type error here as in the adapter. Membership
test: the module imports `arcpy`. Import these modules lazily, inside an `arcpy`-marked
fixture or test and never at the top of a test module: collection imports test modules, and
CI has no ArcPy.
"""
