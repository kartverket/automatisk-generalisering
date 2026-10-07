"""Gives the `arcpy` marker the same behaviour in every environment.

What: tests marked `arcpy` need ArcPy and run under an ArcGIS Pro Python environment. This
file decides what happens to them where ArcPy cannot be imported.

How: three cases.
- A bare run without ArcPy skips every marked test, with the import error as the reason, so
  `pytest` works in WSL, in CI and under any Windows Python.
- A run that selects the marker explicitly (`-m arcpy`, or any expression that needs the
  marker to be satisfied) without ArcPy ends the session at once with a non-zero exit code.
- An unmarked test that imports ArcPy is not touched and fails on its `ImportError`.

Why: skipping alone would let a misconfigured Pro environment report green with every
ArcPy test skipped, which is the one run where a skip is the wrong answer. The pre-commit
hook and CI do not rely on the skip: they run `pytest -m "not arcpy"`, which selects the
same tests on every machine, including one where ArcPy is importable.
"""

from __future__ import annotations

import ast
import importlib

import pytest

ARCPY_MARKER = "arcpy"


def pytest_configure(config: pytest.Config) -> None:
    """Ends the session when `-m` asks for ArcPy tests and ArcPy cannot be imported."""
    expression: str = config.getoption("markexpr", default="") or ""
    if not _explicitly_selects(expression=expression, marker=ARCPY_MARKER):
        return
    error = _arcpy_import_error()
    if error is not None:
        pytest.exit(
            f"-m {expression!r} selects tests marked '{ARCPY_MARKER}', but ArcPy cannot "
            f"be imported here ({error}). Run them under an ArcGIS Pro Python "
            "environment; see docs/contributing/testing.md.",
            returncode=1,
        )


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Skips tests marked `arcpy` when ArcPy cannot be imported."""
    marked = [item for item in items if item.get_closest_marker(ARCPY_MARKER)]
    if not marked:
        return
    error = _arcpy_import_error()
    if error is None:
        return
    skip = pytest.mark.skip(
        reason=f"needs ArcPy, which cannot be imported here ({error}); "
        "run under an ArcGIS Pro Python environment with `pytest -m arcpy`"
    )
    for item in marked:
        item.add_marker(skip)


def _arcpy_import_error() -> ImportError | None:
    """Tries to import ArcPy; returns the error, or None when the import works."""
    try:
        importlib.import_module("arcpy")
    except ImportError as error:
        return error
    return None


def _explicitly_selects(*, expression: str, marker: str) -> bool:
    """True when the `-m` expression can only be satisfied by a test carrying `marker`.

    A test carrying only `marker` must match and a test carrying no marker must not, so
    `arcpy` and `arcpy or slow` select it explicitly, while `not arcpy` and `not slow` do
    not.
    """
    if not expression.strip():
        return False
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        return False
    with_marker = _evaluate(node=tree.body, present=frozenset({marker}))
    without_marker = _evaluate(node=tree.body, present=frozenset())
    return with_marker and not without_marker


def _evaluate(*, node: ast.expr, present: frozenset[str]) -> bool:
    """Evaluates a marker expression for a test that carries the markers in `present`."""
    if isinstance(node, ast.BoolOp):
        results = [_evaluate(node=value, present=present) for value in node.values]
        return all(results) if isinstance(node.op, ast.And) else any(results)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _evaluate(node=node.operand, present=present)
    if isinstance(node, ast.Call):
        return _evaluate(node=node.func, present=present)
    if isinstance(node, ast.Name):
        return node.id in present
    return False
