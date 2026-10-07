"""The escape hatch stays rare: `Attr.raw(...)` call sites in `src/ag` are counted and pinned.

Why: a structured leaf can be compiled by any adapter with correct identifier quoting; a
raw CQL string can say things no adapter compiles. Keeping the count in a test makes adding
a site a deliberate edit here, with the reason beside it. Calls are found in the syntax
tree, so a docstring or comment that mentions the constructor does not count.
"""

from __future__ import annotations

import ast
from pathlib import Path

import ag

PACKAGE = Path(ag.__file__).resolve().parent
PINNED_CALL_SITES: list[str] = []
"""Every allowed `Attr.raw` call site, as `path:line`, with its reason in a review."""


def raw_call_sites_in(source: str, path: str) -> list[str]:
    """`path:line` for every call of the form `Attr.raw(...)` in one module's source."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source, filename=path)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "raw"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "Attr"
        ):
            found.append(f"{path}:{node.lineno}")
    return found


def raw_call_sites() -> list[str]:
    found: list[str] = []
    for path in sorted(PACKAGE.rglob("*.py")):
        relative = path.relative_to(PACKAGE).as_posix()
        found.extend(raw_call_sites_in(path.read_text(encoding="utf-8"), relative))
    return found


def test_attr_raw_call_sites_are_pinned() -> None:
    assert raw_call_sites() == PINNED_CALL_SITES, (
        "an Attr.raw call site appeared or moved; each one is a deliberate edit to "
        "PINNED_CALL_SITES, with its reason in the review"
    )


def test_the_scanner_sees_calls_and_not_mentions() -> None:
    source = (
        '"""`Attr.raw(cql)` is the escape hatch."""\n'
        "# Attr.raw(...) in a comment\n"
        "def raw(cql: str) -> None: ...\n"
        'where = Attr.raw("fartsgrense > 2 * 40")\n'
        "other = Attr.cmp(f, op, v)\n"
    )
    assert raw_call_sites_in(source, "probe.py") == ["probe.py:4"]
