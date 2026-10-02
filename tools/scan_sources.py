"""Static scans over `src/ag` for two rules an import contract cannot express.

What: reports environment reads outside `ag/runtime/env.py`, and imports by string
(`importlib`, `runpy`, `__import__`) outside `ag/runtime/stage_ref.py`.

How: parses every module under the scanned root with `ast` and matches imports, attribute
access on the `os` module and the `__import__` name. Each rule has an allowlist of files,
relative to the scanned root. Run from the repository root as
`python tools/scan_sources.py`; the exit code is non-zero when anything is found.

Why: `os` is part of the standard library and a dynamic import is invisible to
import-linter, so neither rule can be an import contract.
`Settings` is built once by an entry point and passed down, and the one import by string
accepts only `ag.generalization.*`; a second site for either would bypass that. `importlib`
is banned wholesale on purpose: a legitimate later need is added to the allowlist in a
reviewed diff.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ENVIRONMENT_READ = "environment-read"
IMPORT_BY_STRING = "import-by-string"

ALLOWLIST: dict[str, frozenset[str]] = {
    ENVIRONMENT_READ: frozenset({"runtime/env.py"}),
    IMPORT_BY_STRING: frozenset({"runtime/stage_ref.py"}),
}

_OS_ENVIRONMENT_NAMES = frozenset(
    {"environ", "environb", "getenv", "getenvb", "putenv", "unsetenv"}
)
_DYNAMIC_IMPORT_MODULES = frozenset({"importlib", "runpy"})

DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "src" / "ag"


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


def scan_source(*, source: str, path: str) -> list[Finding]:
    """Returns every violation of either rule in one module's source text.

    What: applies both rules to `source` and ignores the allowlist; `path` is only used to
    label the findings.

    How: one walk over the syntax tree. Aliases of the `os` module are collected from the
    import statements first, so `import os as o` followed by `o.environ` is still found.

    Why: keeping the allowlist out of this function is what lets the static test prove
    that each rule fires, independently of which files are exempt.
    """
    tree = ast.parse(source, filename=path)
    os_aliases = _os_aliases(tree=tree)
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in _DYNAMIC_IMPORT_MODULES:
                    findings.append(
                        _finding(
                            path=path,
                            node=node,
                            rule=IMPORT_BY_STRING,
                            what=f"import {alias.name}",
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level == 0 and module.split(".")[0] in _DYNAMIC_IMPORT_MODULES:
                findings.append(
                    _finding(
                        path=path,
                        node=node,
                        rule=IMPORT_BY_STRING,
                        what=f"from {module} import ...",
                    )
                )
            if node.level == 0 and module == "os":
                for alias in node.names:
                    if alias.name in _OS_ENVIRONMENT_NAMES:
                        findings.append(
                            _finding(
                                path=path,
                                node=node,
                                rule=ENVIRONMENT_READ,
                                what=f"from os import {alias.name}",
                            )
                        )
        elif isinstance(node, ast.Name) and node.id == "__import__":
            findings.append(
                _finding(path=path, node=node, rule=IMPORT_BY_STRING, what="__import__")
            )
        elif (
            isinstance(node, ast.Attribute)
            and node.attr in _OS_ENVIRONMENT_NAMES
            and isinstance(node.value, ast.Name)
            and node.value.id in os_aliases
        ):
            findings.append(
                _finding(
                    path=path, node=node, rule=ENVIRONMENT_READ, what=f"os.{node.attr}"
                )
            )
    return sorted(findings, key=lambda found: (found.line, found.rule))


def scan_tree(*, root: Path) -> list[Finding]:
    """Scans every `.py` file under `root` and drops findings in allowlisted files.

    What: the whole check, as the pre-commit hook and the static test run it.

    How: paths are compared in POSIX form relative to `root`, so the allowlist reads the
    same on Windows and Linux. Files are read as UTF-8 whatever the platform default is.
    """
    findings: list[Finding] = []
    for file in sorted(root.rglob("*.py")):
        relative = file.relative_to(root).as_posix()
        for found in scan_source(
            source=file.read_text(encoding="utf-8"), path=relative
        ):
            if relative not in ALLOWLIST[found.rule]:
                findings.append(found)
    return findings


def missing_allowlisted_files(*, root: Path) -> list[str]:
    """Returns allowlist entries that name no file under `root`.

    Why: an allowlist entry for a file that was renamed or never existed exempts nothing
    and hides that the exempt code moved somewhere the scan now rejects, or accepts.
    """
    return sorted(
        entry
        for entries in ALLOWLIST.values()
        for entry in entries
        if not (root / entry).is_file()
    )


def main() -> int:
    """Scans `src/ag`, prints each finding, and returns the process exit code."""
    findings = scan_tree(root=DEFAULT_ROOT)
    missing = missing_allowlisted_files(root=DEFAULT_ROOT)
    for found in findings:
        print(found.render())
    for entry in missing:
        print(f"{entry}: allowlisted in tools/scan_sources.py but does not exist")
    if findings or missing:
        print(f"{len(findings) + len(missing)} problem(s) found")
        return 1
    print("source scans: no environment read or import by string outside its module")
    return 0


def _os_aliases(*, tree: ast.Module) -> frozenset[str]:
    """Names the `os` module is bound to in this module."""
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "os":
                    aliases.add(alias.asname or "os")
    return frozenset(aliases)


def _finding(*, path: str, node: ast.stmt | ast.expr, rule: str, what: str) -> Finding:
    """Builds a finding at the node's line."""
    allowed = ", ".join(sorted(ALLOWLIST[rule]))
    return Finding(
        path=path,
        line=node.lineno,
        rule=rule,
        message=f"`{what}` is allowed only in ag/{allowed}",
    )


if __name__ == "__main__":
    sys.exit(main())
