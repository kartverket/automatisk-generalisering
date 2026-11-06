"""Tools that run on the engine: the third root under the constrained ArcPy stub.

What: scripts that need ArcPy and are not tests, such as the `read_rows` timing run. A
module here imports `arcpy` inside the function that reaches it, under the session's
guard, and runs tools through `session.run_tool`, as the adapter does (ADR-0018 AR-D23).

Why: `tools/` sits in the root pyright environment, where `arcpy` is unresolvable, so an
engine-touching tool needs a root of its own. This one has its execution environment in
`pyproject.toml`, under the stub, and its own scope in `tools/scan_sources.py`, so a tool
is held to the same rule as the adapter and the engine-touching test support. Nothing
here imports from `tests/`: a tool outlives a test layout.
"""
