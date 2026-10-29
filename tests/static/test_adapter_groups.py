"""The group rules of the adapters, and the adapter x port matrix: ADR-0018 AR-D14.

What: for each adapter root, by syntax tree, every name a group class defines is a public
method of its port's Protocol; no name is defined in two group classes of one port
package; nothing in a port package or `support/` assigns `self.<name>`, since state lives
in the base and the shared object; the composed class in a port package's `__init__` has
a body of at most a docstring; and the root holds only the shared object module,
`_base.py`, `support/` and the port packages. The matrix is static: one assignment per
(adapter, port) under `TYPE_CHECKING`, which pyright checks over this module, with a
runtime test beside it that every public Protocol method is implemented by exactly one
group class and that every composed class is listed.

Why: the groups are composed by multiple inheritance, so two groups defining one helper
name would not be a type error, and the first lookup in the MRO would win silently. The
rule removes the hazard by construction, helpers are module-level functions, and this
test is what makes the rule hold as the groups multiply. Over a surface of three methods
it passes whether or not its rules work, so each is broken once in
`tools/break_once/cases/`; the static matrix is broken under pyright by hand, since no
pytest run sees it.
"""

from __future__ import annotations

import ast
import importlib
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from ag.adapters.fakes.memory.cartographic_ops import MemoryCartographicOps
from ag.adapters.fakes.memory.geometry_ops import MemoryGeometryOps
from ag.adapters.fakes.memory.table_ops import MemoryTableOps
from ag.ports.cartographic_ops import CartographicOps
from ag.ports.geometry_ops import GeometryOps
from ag.ports.table_ops import TableOps

if TYPE_CHECKING:
    from ag.adapters.fakes.memory.store import MemoryStore

    _store = MemoryStore()
    _memory_geometry: GeometryOps = MemoryGeometryOps(store=_store)
    _memory_table: TableOps = MemoryTableOps(store=_store)
    _memory_cartographic: CartographicOps = MemoryCartographicOps(store=_store)

PORTS: dict[str, type] = {
    "geometry_ops": GeometryOps,
    "table_ops": TableOps,
    "cartographic_ops": CartographicOps,
}
"""Port package name to the Protocol it implements."""

ADAPTERS: dict[str, tuple[str, str]] = {
    "arcpy": ("ag.adapters.arcpy", "session.py"),
    "memory": ("ag.adapters.fakes.memory", "store.py"),
}
"""Adapter to its root package and the module holding its one shared object."""

MATRIX: dict[tuple[str, str], type] = {
    ("memory", "geometry_ops"): MemoryGeometryOps,
    ("memory", "table_ops"): MemoryTableOps,
    ("memory", "cartographic_ops"): MemoryCartographicOps,
}
"""(adapter, port) to the composed class; each row has an assignment above."""

RULES = (
    "protocol-methods-only",
    "no-duplicate-method",
    "no-state-outside-base",
    "composed-body-empty",
    "root-contents",
)


@dataclass(frozen=True)
class GroupClass:
    port: str
    module: str
    name: str
    defined: tuple[str, ...]


def _root(adapter: str) -> Path:
    package, _ = ADAPTERS[adapter]
    file = importlib.import_module(package).__file__
    assert file is not None
    return Path(file).parent


def _defined_names(node: ast.ClassDef) -> tuple[str, ...]:
    """Every name a class body defines, a leading docstring excepted."""
    names: list[str] = []
    for statement in node.body:
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.append(statement.name)
        elif isinstance(statement, ast.Assign):
            names.extend(t.id for t in statement.targets if isinstance(t, ast.Name))
        elif isinstance(statement, ast.AnnAssign) and isinstance(
            statement.target, ast.Name
        ):
            names.append(statement.target.id)
        elif not (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        ) and not isinstance(statement, ast.Pass):
            names.append(f"<{type(statement).__name__} at line {statement.lineno}>")
    return tuple(names)


def _classes(path: Path) -> list[ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node for node in tree.body if isinstance(node, ast.ClassDef)]


def _group_classes(adapter: str) -> list[GroupClass]:
    found: list[GroupClass] = []
    for port in PORTS:
        for module in sorted((_root(adapter) / port).glob("*.py")):
            if module.name == "__init__.py":
                continue
            for node in _classes(module):
                found.append(
                    GroupClass(port, module.name, node.name, _defined_names(node))
                )
    return found


def _self_assignments(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign | ast.AugAssign):
            targets = [node.target]
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                found.append(
                    f"{path.parent.name}/{path.name}:{target.lineno} self.{target.attr}"
                )
    return found


def _protocol_methods(protocol: type) -> set[str]:
    return {
        name
        for name, value in vars(protocol).items()
        if inspect.isfunction(value) and not name.startswith("_")
    }


def violations(adapter: str) -> list[tuple[str, str]]:
    """(rule, message) for everything in `adapter`'s root that breaks a rule."""
    found: list[tuple[str, str]] = []
    root = _root(adapter)
    groups = _group_classes(adapter)
    for group in groups:
        allowed = _protocol_methods(PORTS[group.port])
        for name in group.defined:
            if name not in allowed:
                found.append(
                    (
                        "protocol-methods-only",
                        f"{adapter}/{group.port}/{group.module}: class {group.name} "
                        f"defines {name!r}, which is not a method of the Protocol; a "
                        "helper is a module-level function.",
                    )
                )
    for port in PORTS:
        seen: dict[str, str] = {}
        for group in (g for g in groups if g.port == port):
            for name in group.defined:
                if name in seen:
                    found.append(
                        (
                            "no-duplicate-method",
                            f"{adapter}/{port}: {name!r} is defined in {seen[name]} and "
                            f"in {group.name}; a Protocol method has one group.",
                        )
                    )
                seen.setdefault(name, group.name)
    for package in (*PORTS, "support"):
        for path in sorted((root / package).rglob("*.py")):
            for assignment in _self_assignments(path):
                found.append(
                    (
                        "no-state-outside-base",
                        f"{adapter}: {assignment}; a group holds no state, and only "
                        "_base.py and the shared object assign an attribute.",
                    )
                )
    for port in PORTS:
        for node in _classes(root / port / "__init__.py"):
            body = _defined_names(node)
            if body:
                found.append(
                    (
                        "composed-body-empty",
                        f"{adapter}/{port}: composed class {node.name} defines {body}; "
                        "its body is empty, the groups define everything.",
                    )
                )
    _, shared = ADAPTERS[adapter]
    allowed_entries = {"__init__.py", "_base.py", shared, "support", *PORTS}
    for entry in sorted(root.iterdir()):
        if entry.name == "__pycache__":
            continue
        if entry.name not in allowed_entries:
            found.append(
                (
                    "root-contents",
                    f"{adapter}: {entry.name} is in the adapter root, which holds only "
                    f"{sorted(allowed_entries)}.",
                )
            )
    return found


@pytest.mark.parametrize("rule", RULES, ids=RULES)
@pytest.mark.parametrize("adapter", sorted(ADAPTERS), ids=sorted(ADAPTERS))
def test_rule_holds(adapter: str, rule: str) -> None:
    broken = [msg for r, msg in violations(adapter) if r == rule]
    assert broken == [], "\n".join(broken)


@pytest.mark.parametrize(
    ("adapter", "port"), sorted(MATRIX), ids=[f"{a}-{p}" for a, p in sorted(MATRIX)]
)
def test_every_protocol_method_is_implemented_by_one_group(
    adapter: str, port: str
) -> None:
    package, _ = ADAPTERS[adapter]
    composed = MATRIX[adapter, port]
    group_package = f"{package}.{port}."
    for name in sorted(_protocol_methods(PORTS[port])):
        owners = [
            base.__name__
            for base in composed.__mro__
            if name in vars(base) and base.__module__.startswith(group_package)
        ]
        assert len(owners) == 1, (
            f"{adapter}/{port}: {name} is implemented by {owners or 'no group'}"
        )


def test_every_composed_class_is_in_the_matrix() -> None:
    listed = {cls.__name__ for cls in MATRIX.values()}
    for adapter in ADAPTERS:
        for port in PORTS:
            for node in _classes(_root(adapter) / port / "__init__.py"):
                assert node.name in listed, (
                    f"{adapter}/{port}: {node.name} is not in MATRIX"
                )


def test_the_scan_sees_the_memory_groups() -> None:
    by_name = {g.name: g for g in _group_classes("memory")}
    assert by_name["Selection"].defined == ("select",)
    assert by_name["Shape"].defined == ("explode_multipart",)
    assert by_name["RowIO"].defined == ("read_rows",)
