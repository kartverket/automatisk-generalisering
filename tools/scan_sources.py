"""Static scans for three rules an import contract or a type stub cannot express.

What: three rules, each over the roots that `SCOPES` assigns it. `environment-read`:
no environment read outside `ag/runtime/env.py`. `import-by-string`: no `importlib`,
`runpy` or `__import__` outside `ag/runtime/stage_ref.py`. `arcpy-session-only`: under
the ArcPy adapter and the engine-touching test support, the engine is reached through
the session module or inside its guard, and never behind the constrained stub's back.

How: parses every module under a scope's root with `ast`. The first two rules match
imports, attribute access on the `os` module and the `__import__` name. The third
reports, outside the scope's allowlist: (1) any import of `arcpy` other than
`import arcpy`, optionally aliased, since a submodule import such as
`from arcpy.management import Delete` resolves past the stub; (2) any reference to the
alias outside a guard block, except the import statement and a type annotation, where a
guard block is a `with` whose item's context expression is a call to an attribute named
`guard`, later items of the same `with` counting as inside, and a `def`, `lambda` or
generator expression written inside the block counting as outside, since it runs later;
(3) a reference to `getattr`, `setattr`, `delattr`, `hasattr`, `vars`, `attrgetter` or
`methodcaller` as a name, an attribute or an import, whatever the target, an attribute
access `__dict__` or `__getattribute__`, and a `sys.modules` subscript, inside a guard
too;
(4) the name `ExecuteError` as a name, an attribute or an import, inside a guard too;
(5) an `except` clause whose type expression mentions the alias. One finding per line
and rule.
A call on an engine object, such as a cursor, is a review rule and is not scanned. Run
from the repository root as `python tools/scan_sources.py`; the exit code is non-zero
when anything is found.

Why: `os` is part of the standard library and a dynamic import is invisible to
import-linter, so neither rule can be an import contract. `Settings` is built once by an
entry point and passed down, and the one import by string accepts only
`ag.generalization.*`; a second site for either would bypass that. `importlib` is banned
wholesale on purpose: a legitimate later need is added to the allowlist in a reviewed
diff. The stub makes a tool, `arcpy.env` or a vendor exception a type error, but a
getattr, a `__dict__` lookup or a submodule import reaches the engine without a type
error; the session module alone executes tools and names vendor exceptions, and every
other engine call runs inside its guard (ADR-0018 AR-D23).
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Collection, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

ENVIRONMENT_READ = "environment-read"
IMPORT_BY_STRING = "import-by-string"
ARCPY_SESSION_ONLY = "arcpy-session-only"
RULES = frozenset({ENVIRONMENT_READ, IMPORT_BY_STRING, ARCPY_SESSION_ONLY})

_OS_ENVIRONMENT_NAMES = frozenset(
    {"environ", "environb", "getenv", "getenvb", "putenv", "unsetenv"}
)
_DYNAMIC_IMPORT_MODULES = frozenset({"importlib", "runpy"})
_REFLECTION_NAMES = frozenset(
    {"getattr", "setattr", "delattr", "hasattr", "vars", "attrgetter", "methodcaller"}
)
_DEFERRED = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.GeneratorExp)
_REFLECTION_ATTRIBUTES = frozenset({"__dict__", "__getattribute__"})
_VENDOR_EXCEPTION = "ExecuteError"

REPO = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().relative_to(REPO).as_posix()
_NO_EXEMPTIONS: Mapping[str, frozenset[str]] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class Scope:
    """One root, the rules that apply under it, and the files each rule exempts.

    Allowlist entries are POSIX paths relative to `root`; a rule without an entry
    exempts nothing.
    """

    root: Path
    rules: frozenset[str]
    allowlist: Mapping[str, frozenset[str]] = _NO_EXEMPTIONS

    def exempt(self, *, path: str, rule: str) -> bool:
        return path in self.allowlist.get(rule, frozenset())


SCOPES: dict[str, Scope] = {
    "src-ag": Scope(
        root=REPO / "src" / "ag",
        rules=frozenset({ENVIRONMENT_READ, IMPORT_BY_STRING}),
        allowlist={
            ENVIRONMENT_READ: frozenset({"runtime/env.py"}),
            IMPORT_BY_STRING: frozenset({"runtime/stage_ref.py"}),
        },
    ),
    "adapters-arcpy": Scope(
        root=REPO / "src" / "ag" / "adapters" / "arcpy",
        rules=frozenset({ARCPY_SESSION_ONLY}),
        allowlist={ARCPY_SESSION_ONLY: frozenset({"session.py"})},
    ),
    "tests-support-arcpy": Scope(
        root=REPO / "tests" / "support" / "arcpy",
        rules=frozenset({ARCPY_SESSION_ONLY, IMPORT_BY_STRING}),
    ),
}


@dataclass(frozen=True, slots=True)
class Finding:
    """One violation: the file relative to the scanned root, the line, and the rule.

    What: the unit the scanner reports and the static test asserts on.

    Why: a rule name rather than a message is what the allowlist and the tests key on, so
    the wording of a message can change without touching either.
    """

    path: str
    line: int
    rule: str
    message: str

    def render(self) -> str:
        """Formats the finding as `path:line: [rule] message`."""
        return f"{self.path}:{self.line}: [{self.rule}] {self.message}"


def scan_source(
    *, source: str, path: str, rules: Collection[str] = RULES
) -> list[Finding]:
    """Returns every violation of `rules` in one module's source text.

    What: applies the rules to `source` and ignores every allowlist; `path` is only used
    to label the findings.

    How: aliases of the `os` and `arcpy` modules are collected from the import statements
    first, so `import os as o` followed by `o.environ` is still found. The first two
    rules are one walk over the syntax tree; the third is a visit that tracks whether
    the node sits inside a guard block or a type annotation.

    Why: keeping the allowlist out of this function is what lets the static test prove
    that each rule fires, independently of which files are exempt.
    """
    tree = ast.parse(source, filename=path)
    findings: list[Finding] = []
    if ENVIRONMENT_READ in rules or IMPORT_BY_STRING in rules:
        findings.extend(_runtime_findings(tree=tree, path=path, rules=rules))
    if ARCPY_SESSION_ONLY in rules:
        findings.extend(_engine_findings(tree=tree, path=path))
    first: dict[tuple[int, str], Finding] = {}
    for found in sorted(findings, key=lambda found: (found.line, found.rule)):
        first.setdefault((found.line, found.rule), found)
    return list(first.values())


def scan_tree(scope: Scope, /) -> list[Finding]:
    """Scans every `.py` file under the scope's root and drops allowlisted findings.

    What: the whole check for one scope, as the pre-commit hook and the static test run
    it.

    How: paths are compared in POSIX form relative to the root, so the allowlist reads
    the same on Windows and Linux. Files are read as UTF-8 whatever the platform default
    is.
    """
    findings: list[Finding] = []
    for file in sorted(scope.root.rglob("*.py")):
        relative = file.relative_to(scope.root).as_posix()
        for found in scan_source(
            source=file.read_text(encoding="utf-8"), path=relative, rules=scope.rules
        ):
            if not scope.exempt(path=relative, rule=found.rule):
                findings.append(found)
    return findings


def missing_allowlisted_files(scope: Scope, /) -> list[str]:
    """Returns allowlist entries that name no file under the scope's root.

    Why: an allowlist entry for a file that was renamed or never existed exempts nothing
    and hides that the exempt code moved somewhere the scan now rejects, or accepts.
    """
    return sorted(
        entry
        for entries in scope.allowlist.values()
        for entry in entries
        if not (scope.root / entry).is_file()
    )


def main() -> int:
    """Scans every scope, prints each finding, and returns the process exit code."""
    problems = 0
    for scope in SCOPES.values():
        label = scope.root.relative_to(REPO).as_posix()
        for found in scan_tree(scope):
            print(f"{label}/{found.render()}")
            problems += 1
        for entry in missing_allowlisted_files(scope):
            print(f"{label}/{entry}: allowlisted in {HERE} but does not exist")
            problems += 1
    if problems:
        print(f"{problems} problem(s) found")
        return 1
    print("source scans: no environment read, import by string or engine reach-through")
    return 0


def _runtime_findings(
    *, tree: ast.Module, path: str, rules: Collection[str]
) -> Iterator[Finding]:
    """The environment-read and import-by-string findings, whichever are asked for."""
    os_aliases = _aliases_of("os", tree=tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in _DYNAMIC_IMPORT_MODULES:
                    yield _finding(
                        path=path,
                        node=node,
                        rule=IMPORT_BY_STRING,
                        what=f"import {alias.name}",
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level == 0 and module.split(".")[0] in _DYNAMIC_IMPORT_MODULES:
                yield _finding(
                    path=path,
                    node=node,
                    rule=IMPORT_BY_STRING,
                    what=f"from {module} import ...",
                )
            if node.level == 0 and module == "os":
                for alias in node.names:
                    if alias.name in _OS_ENVIRONMENT_NAMES:
                        yield _finding(
                            path=path,
                            node=node,
                            rule=ENVIRONMENT_READ,
                            what=f"from os import {alias.name}",
                        )
        elif isinstance(node, ast.Name) and node.id == "__import__":
            yield _finding(
                path=path, node=node, rule=IMPORT_BY_STRING, what="__import__"
            )
        elif (
            isinstance(node, ast.Attribute)
            and node.attr in _OS_ENVIRONMENT_NAMES
            and isinstance(node.value, ast.Name)
            and node.value.id in os_aliases
        ):
            yield _finding(
                path=path, node=node, rule=ENVIRONMENT_READ, what=f"os.{node.attr}"
            )


def _engine_findings(*, tree: ast.Module, path: str) -> Iterator[Finding]:
    """The arcpy-session-only findings: the import forms, then the visit."""
    aliases = _aliases_of("arcpy", tree=tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("arcpy."):
                    yield _engine_finding(
                        path, node, f"`import {alias.name}` resolves past the stub"
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level == 0 and (module == "arcpy" or module.startswith("arcpy.")):
                yield _engine_finding(
                    path, node, f"`from {module} import ...` resolves past the stub"
                )
            for alias in node.names:
                if alias.name == _VENDOR_EXCEPTION:
                    yield _engine_finding(
                        path,
                        node,
                        f"`{_VENDOR_EXCEPTION}` is named in the session module only",
                    )
                if alias.name in _REFLECTION_NAMES:
                    yield _engine_finding(
                        path, node, f"`{alias.name}` reaches the engine behind the stub"
                    )
    yield from _visit(tree, path=path, aliases=aliases, guarded=False)


def _visit(
    node: ast.AST, *, path: str, aliases: frozenset[str], guarded: bool
) -> Iterator[Finding]:
    """Walks `node`, reporting the engine reach-throughs under it.

    `guarded` says whether `node` sits inside a guard block; it is dropped on entering
    code that runs later than the block; annotations are skipped.
    """
    if isinstance(node, _DEFERRED):
        guarded = False
    if isinstance(node, ast.Name) and node.id in aliases and not guarded:
        yield _engine_finding(
            path, node, f"`{node.id}` is referenced outside the session's guard"
        )
    if isinstance(node, ast.Name) and node.id in _REFLECTION_NAMES:
        yield _engine_finding(
            path, node, f"`{node.id}` reaches the engine behind the stub"
        )
    if isinstance(node, ast.Attribute) and (
        node.attr in _REFLECTION_NAMES or node.attr in _REFLECTION_ATTRIBUTES
    ):
        yield _engine_finding(
            path, node, f"`{node.attr}` reaches the engine behind the stub"
        )
    if isinstance(node, ast.Subscript) and _is_sys_modules(node.value):
        yield _engine_finding(
            path, node, "`sys.modules` reaches the engine behind the stub"
        )
    if isinstance(node, ast.Name | ast.Attribute) and _names_vendor_exception(node):
        yield _engine_finding(
            path, node, f"`{_VENDOR_EXCEPTION}` is named in the session module only"
        )
    if isinstance(node, ast.ExceptHandler) and node.type is not None:
        if any(_mentions(child, aliases) for child in ast.walk(node.type)):
            yield _engine_finding(
                path, node, "an `except` on an engine class belongs to the session"
            )
    if isinstance(node, ast.With):
        inside = guarded
        for item in node.items:
            yield from _visit(
                item.context_expr, path=path, aliases=aliases, guarded=inside
            )
            if item.optional_vars is not None:
                yield from _visit(
                    item.optional_vars, path=path, aliases=aliases, guarded=inside
                )
            if _is_guard(item.context_expr):
                inside = True
        for statement in node.body:
            yield from _visit(statement, path=path, aliases=aliases, guarded=inside)
        return
    for child in _children_outside_annotations(node):
        yield from _visit(child, path=path, aliases=aliases, guarded=guarded)


def _children_outside_annotations(node: ast.AST) -> Iterator[ast.AST]:
    """The child nodes of `node`, skipping annotation expressions."""
    skipped: set[int] = set()
    if isinstance(node, ast.arg) and node.annotation is not None:
        skipped.add(id(node.annotation))
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        if node.returns is not None:
            skipped.add(id(node.returns))
    if isinstance(node, ast.AnnAssign):
        skipped.add(id(node.annotation))
    for child in ast.iter_child_nodes(node):
        if id(child) not in skipped:
            yield child


def _is_guard(expression: ast.expr) -> bool:
    """Whether a `with` item is a call to an attribute named `guard`."""
    return (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Attribute)
        and expression.func.attr == "guard"
    )


def _is_sys_modules(expression: ast.expr) -> bool:
    return (
        isinstance(expression, ast.Attribute)
        and expression.attr == "modules"
        and isinstance(expression.value, ast.Name)
        and expression.value.id == "sys"
    )


def _names_vendor_exception(node: ast.Name | ast.Attribute) -> bool:
    if isinstance(node, ast.Name):
        return node.id == _VENDOR_EXCEPTION
    return node.attr == _VENDOR_EXCEPTION


def _mentions(node: ast.AST, aliases: frozenset[str]) -> bool:
    return isinstance(node, ast.Name) and node.id in aliases


def _aliases_of(module: str, *, tree: ast.Module) -> frozenset[str]:
    """Names the top-level `module` is bound to in this module by `import`."""
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == module:
                    aliases.add(alias.asname or module)
    return frozenset(aliases)


def _finding(*, path: str, node: ast.stmt | ast.expr, rule: str, what: str) -> Finding:
    """Builds a finding at the node's line, naming the one file the rule allows."""
    allowed = {
        ENVIRONMENT_READ: "ag/runtime/env.py",
        IMPORT_BY_STRING: "ag/runtime/stage_ref.py",
    }[rule]
    return Finding(
        path=path,
        line=node.lineno,
        rule=rule,
        message=f"`{what}` is allowed only in {allowed}",
    )


def _engine_finding(
    path: str, node: ast.stmt | ast.expr | ast.ExceptHandler, message: str, /
) -> Finding:
    """Builds an arcpy-session-only finding at the node's line."""
    return Finding(
        path=path, line=node.lineno, rule=ARCPY_SESSION_ONLY, message=message
    )


if __name__ == "__main__":
    sys.exit(main())
