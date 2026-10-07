"""Break-it-once evidence: every guard broken once, its tests failing, the file restored.

Run from the repository root: `python -m tools.break_once [set ...] [--check] [--out FILE]`.
The engine is `engine.py`; the case tables are the modules of `cases/`, one per mutated
source package, each exporting `CASES` and `SUITE`.
"""
