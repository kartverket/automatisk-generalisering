"""`typing.cast` stays rare: its call sites in `src/ag` are counted and pinned.

What: every call of `typing.cast` in the package, found over the syntax tree under any
spelling the import allows (`cast(...)`, `typing.cast(...)`, an aliased module or an
aliased name), counted per module and pinned to the facade's one.

Why: a cast asserts something no one checked. The one in the facade is where a wrapped
port is handed out as the port type, and the composition root needs none of its own
(ADR-0017 RS-R4 is the alternative it replaces). Keeping the count in a test makes a
second cast a deliberate edit here, with the reason beside it. Counted by syntax, so a
docstring that mentions a cast does not count and an alias cannot hide one.
"""

from __future__ import annotations

import ast
from pathlib import Path

import ag

PACKAGE = Path(ag.__file__).resolve().parent
PINNED: dict[str, int] = {"lineage/facade.py": 1}
"""Module to its number of `typing.cast` call sites, with the reason in a review."""


def _cast_names(tree: ast.Module) -> tuple[set[str], set[str]]:
    """(names bound to `typing.cast`, names bound to the `typing` module) in `tree`."""
    functions: set[str] = set()
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "typing":
                    modules.add(alias.asname or "typing")
        elif isinstance(node, ast.ImportFrom) and node.module == "typing":
            for alias in node.names:
                if alias.name == "cast":
                    functions.add(alias.asname or "cast")
    return functions, modules


def cast_call_sites_in(source: str, path: str) -> list[str]:
    """`path:line` for every `typing.cast` call in one module's source."""
    tree = ast.parse(source, filename=path)
    functions, modules = _cast_names(tree)
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_cast = (isinstance(func, ast.Name) and func.id in functions) or (
            isinstance(func, ast.Attribute)
            and func.attr == "cast"
            and isinstance(func.value, ast.Name)
            and func.value.id in modules
        )
        if is_cast:
            found.append(f"{path}:{node.lineno}")
    return found


def cast_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        relative = path.relative_to(PACKAGE).as_posix()
        sites = cast_call_sites_in(path.read_text(encoding="utf-8"), relative)
        if sites:
            counts[relative] = len(sites)
    return counts


def test_cast_call_sites_are_pinned() -> None:
    assert cast_counts() == PINNED, (
        "a typing.cast call site appeared or moved; each one is a deliberate edit to "
        "PINNED, with its reason in the review"
    )


def test_the_scanner_sees_every_spelling_and_no_mention() -> None:
    source = (
        '"""`cast(P, facade)` is the one cast."""\n'
        "# cast(...) in a comment\n"
        "import typing\n"
        "import typing as t\n"
        "from typing import cast\n"
        "from typing import cast as c\n"
        "def cast_rows() -> None: ...\n"
        "a = cast(int, 1)\n"
        "b = typing.cast(int, 1)\n"
        "c_ = t.cast(int, 1)\n"
        "d = c(int, 1)\n"
        "e = other.cast(int, 1)\n"
        "f = cast_rows()\n"
    )
    assert cast_call_sites_in(source, "probe.py") == [
        "probe.py:8",
        "probe.py:9",
        "probe.py:10",
        "probe.py:11",
    ]
