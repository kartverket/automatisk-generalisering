"""The row-shape check over every port Protocol: ADR-0017 RS-4.

What: every module under `ag.ports` is imported, every Protocol in it found, and every
method's parameters classified by the direction marker in their annotation. One
parametrised test per rule, so a break-it case can name the rule it breaks: every `Out`
has a row; every row names an `Out`; subject, context and refs name `In` parameters; a
handle parameter without a marker fails; a method with no `Out` is in the query list or
fails; a `Mutates` parameter fails closed until its declaration form is decided.
`ParentsOut` is exempt from the first rule and never carries a row. The cells and the
subject rules are `Rows`' own business at construction, covered in the unit tests.

How: markers are found by walking a resolved hint through `Annotated`, unions, tuples
and sequences down to `ScratchHandle`, so `inputs: tuple[In, ...]` classifies and a bare
`ScratchHandle` anywhere in a hint is an unmarked handle. A handle inside a `Spatial`
predicate is a value, not a hint, and is not seen; that is stated in the predicate
module and in the ADR so it is not mistaken for an omission. The declaration is read from
the Protocol class, never from an instance.

Why: a Protocol method with an undeclared output would reach the facade with nothing to
read, and a declaration naming a parameter that does not exist would pass every check
that iterates over declarations. Over a surface of three methods the check passes
whether or not its rules work, so each is broken once in `tools/break_once/cases/`.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from collections.abc import Iterator
from dataclasses import dataclass
from types import ModuleType
from typing import Annotated, Any, Union, get_args, get_origin, get_type_hints

import pytest

import ag.ports
from ag.core.handles import Direction, ScratchHandle
from ag.ports.row_shape import Rows

QUERIES: frozenset[str] = frozenset({"TableOps.read_rows"})
"""Methods outside the grammar: they return values and write no handle. Listed, not
inferred, so an output that lost its marker cannot pass as a query."""

RULES = (
    "out-without-row",
    "row-names-non-out",
    "input-names-non-in",
    "unmarked-handle",
    "unlisted-query",
    "mutates-fails-closed",
)


@dataclass(frozen=True)
class Method:
    """One Protocol method with its parameters classified."""

    name: str
    directions: dict[str, Direction]
    unmarked: tuple[str, ...]
    rows: dict[str, object] | None


def _modules() -> Iterator[ModuleType]:
    for info in pkgutil.iter_modules(ag.ports.__path__, prefix="ag.ports."):
        yield importlib.import_module(info.name)


def _protocols(module: ModuleType) -> Iterator[tuple[str, type]]:
    for name, obj in vars(module).items():
        if (
            inspect.isclass(obj)
            and obj.__module__ == module.__name__
            and bool(getattr(obj, "_is_protocol", False))
        ):
            yield name, obj


def _walk(hint: object) -> tuple[set[Direction], bool]:
    """The markers found in a hint, and whether a bare `ScratchHandle` was reached."""
    if hint is ScratchHandle:
        return set(), True
    origin = get_origin(hint)
    if origin is Annotated:
        inner, *metadata = get_args(hint)
        found = {meta for meta in metadata if isinstance(meta, Direction)}
        if found:
            return found, False
        return _walk(inner)
    if origin is not None:
        found: set[Direction] = set()
        bare = False
        for arg in get_args(hint):
            inner_found, inner_bare = _walk(arg)
            found |= inner_found
            bare = bare or inner_bare
        return found, bare
    return set(), False


def _classify(fn: Any, owner: str) -> Method:
    hints = get_type_hints(fn, include_extras=True)
    directions: dict[str, Direction] = {}
    unmarked: list[str] = []
    for param in list(inspect.signature(fn).parameters)[1:]:
        found, bare = _walk(hints.get(param))
        if bare or len(found) > 1:
            unmarked.append(param)
        elif found:
            directions[param] = found.pop()
    rows = getattr(fn, "__row_shape__", None)
    return Method(
        name=f"{owner}.{fn.__name__}",
        directions=directions,
        unmarked=tuple(unmarked),
        rows=dict(rows) if rows is not None else None,
    )


def surface() -> list[Method]:
    found: list[Method] = []
    for module in _modules():
        for protocol_name, protocol in _protocols(module):
            for attr, value in vars(protocol).items():
                if inspect.isfunction(value) and not attr.startswith("_"):
                    found.append(_classify(value, protocol_name))
    return found


def violations(method: Method) -> list[tuple[str, str]]:
    """(rule, message) for every rule the method breaks."""
    found: list[tuple[str, str]] = []
    outs = {p for p, d in method.directions.items() if d is Direction.OUT}
    ins = {p for p, d in method.directions.items() if d is Direction.IN}
    mutates = {p for p, d in method.directions.items() if d is Direction.MUTATES}
    rows = method.rows or {}
    for param in method.unmarked:
        found.append(
            (
                "unmarked-handle",
                f"{method.name}: {param!r} is a handle with no direction marker; "
                "every port handle parameter is In, Out, Mutates or ParentsOut.",
            )
        )
    for param in sorted(outs - rows.keys()):
        found.append(
            (
                "out-without-row",
                f"{method.name}: output {param!r} declares no row shape. Add it to "
                "@row_shape, or, for a method whose rows the caller builds, declare "
                "the ids axis at the call site once that declaration type exists.",
            )
        )
    for param, declared in rows.items():
        if param not in outs:
            found.append(
                (
                    "row-names-non-out",
                    f"{method.name}: @row_shape names {param!r}, which is not an Out "
                    "parameter; a ParentsOut carries no row.",
                )
            )
        if not isinstance(declared, Rows):
            found.append(
                (
                    "row-names-non-out",
                    f"{method.name}: @row_shape entry {param!r} is not a Rows.",
                )
            )
            continue
        for named in declared.inputs():
            if named not in ins:
                found.append(
                    (
                        "input-names-non-in",
                        f"{method.name}: row {param!r} names {named!r}, which is not "
                        "an In parameter of the method.",
                    )
                )
    if mutates:
        found.append(
            (
                "mutates-fails-closed",
                f"{method.name}: {sorted(mutates)} is Mutates, and the declaration form "
                "for a method that changes its input in place is not decided; the "
                "surface may not carry one until it is.",
            )
        )
    is_query = not outs and not mutates
    if is_query and method.name not in QUERIES:
        found.append(
            (
                "unlisted-query",
                f"{method.name}: writes no handle and is not in the query list; a "
                "query is listed, never inferred from a missing Out.",
            )
        )
    if not is_query and method.name in QUERIES:
        found.append(
            (
                "unlisted-query",
                f"{method.name}: is in the query list but writes a handle.",
            )
        )
    return found


@pytest.fixture(scope="module")
def methods() -> list[Method]:
    return surface()


def test_the_surface_is_seen(methods: list[Method]) -> None:
    """The scan is not vacuous: the methods that exist are found and classified."""
    names = {m.name: m for m in methods}
    assert {
        "GeometryOps.select",
        "GeometryOps.explode_multipart",
        "TableOps.read_rows",
    } <= (names.keys())
    explode = names["GeometryOps.explode_multipart"]
    assert explode.directions["parents"] is Direction.PARENTS_OUT
    assert explode.rows is not None and "parents" not in explode.rows


@pytest.mark.parametrize("rule", RULES, ids=RULES)
def test_rule_holds(rule: str, methods: list[Method]) -> None:
    broken = [msg for m in methods for r, msg in violations(m) if r == rule]
    assert broken == [], "\n".join(broken)


def test_walk_classifies_markers_inside_containers_and_unions() -> None:
    from ag.core.handles import In, ParentsOut

    assert _walk(tuple[In, ...]) == ({Direction.IN}, False)
    assert _walk(ParentsOut) == ({Direction.PARENTS_OUT}, False)
    assert _walk(Union[ScratchHandle, None]) == (set(), True)  # noqa: UP007
    assert _walk(ScratchHandle | None) == (set(), True)
    assert _walk(int) == (set(), False)
