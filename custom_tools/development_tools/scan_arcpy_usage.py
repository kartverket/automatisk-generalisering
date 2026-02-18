#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    "build",
    "dist",
    "site-packages",
}


@dataclass(frozen=True)
class Occurrence:
    file: str
    line: int


def _is_git_repo(root: Path) -> bool:
    try:
        subprocess.check_output(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=root,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return True
    except Exception:
        return False


def iter_python_files(root: Path, use_git: bool) -> Iterable[Path]:
    if use_git and _is_git_repo(root):
        out = subprocess.check_output(["git", "ls-files", "*.py"], cwd=root, text=True)
        for rel in out.splitlines():
            path = (root / rel).resolve()
            if path.is_file():
                yield path
        return

    for path in root.rglob("*.py"):
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def _attr_chain(node: ast.AST) -> list[str] | None:
    """
    Convert an Attribute/Name tree like a.b.c into ["a","b","c"].
    """
    parts: list[str] = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        parts.reverse()
        return parts
    return None


def _build_local_to_arcpy_aliases(tree: ast.AST) -> dict[str, str]:
    """
    Map local names to fully-qualified arcpy paths based on imports.

    Examples:
      import arcpy as ap                 => ap -> arcpy
      import arcpy.management as mgmt    => mgmt -> arcpy.management
      from arcpy import management as m  => m -> arcpy.management
      from arcpy.management import Buffer as Buf => Buf -> arcpy.management.Buffer
    """
    local_to = {"arcpy": "arcpy"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "arcpy":
                    local_to[alias.asname or "arcpy"] = "arcpy"
                elif alias.name.startswith("arcpy."):
                    # import arcpy.management as mgmt
                    local_to[alias.asname or alias.name.split(".")[-1]] = alias.name

        elif isinstance(node, ast.ImportFrom):
            if node.module == "arcpy":
                for alias in node.names:
                    local_to[alias.asname or alias.name] = f"arcpy.{alias.name}"
            elif node.module and node.module.startswith("arcpy."):
                for alias in node.names:
                    local_to[alias.asname or alias.name] = f"{node.module}.{alias.name}"

    return local_to


def _split_toolbox_and_tool(full: str) -> tuple[str, str]:
    """
    Turn a resolved call name into (toolbox, tool).

    Examples:
      arcpy.management.Buffer                  -> ("management", "Buffer")
      arcpy.cartography.ResolveBuildingConflicts -> ("cartography", "ResolveBuildingConflicts")
      arcpy.da.SearchCursor                    -> ("da", "SearchCursor")
      arcpy.FeatureVerticesToPoints_management -> ("management", "FeatureVerticesToPoints")  (legacy style)
      arcpy.Exists                             -> ("core", "Exists")
    """
    parts = full.split(".")
    if not parts or parts[0] != "arcpy":
        return ("unknown", full)

    # arcpy.<toolbox>.<tool>[.<more>]
    if len(parts) >= 3:
        toolbox = parts[1]
        tool = ".".join(parts[2:])  # keep deeper names if any
        return (toolbox, tool)

    # arcpy.<something>
    name = parts[1] if len(parts) == 2 else "unknown"
    # legacy GP style: ToolName_management, ToolName_analysis, ...
    if "_" in name:
        prefix, suffix = name.rsplit("_", 1)
        if suffix.isalpha() and suffix.islower():
            return (suffix, prefix)
    return ("core", name)


def scan_file(path: Path) -> list[tuple[str, Occurrence]]:
    src = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError:
        return []

    local_to = _build_local_to_arcpy_aliases(tree)
    hits: list[tuple[str, Occurrence]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func = node.func

        # Case: Buf(...) where Buf was imported from arcpy.*
        if isinstance(func, ast.Name) and func.id in local_to:
            resolved = local_to[func.id]
            if resolved.startswith("arcpy."):
                hits.append((resolved, Occurrence(str(path), node.lineno)))
            continue

        # Case: arcpy.management.Buffer(...) or ap.management.Buffer(...)
        chain = _attr_chain(func)
        if not chain:
            continue

        head = chain[0]
        if head not in local_to:
            continue

        resolved_head = local_to[head]  # "arcpy" or "arcpy.management" etc.
        resolved_parts = resolved_head.split(".") + chain[1:]
        if resolved_parts and resolved_parts[0] == "arcpy":
            resolved = ".".join(resolved_parts)
            hits.append((resolved, Occurrence(str(path), node.lineno)))

    return hits


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find real ArcPy call sites, then summarize toolboxes/tools used."
    )
    parser.add_argument("--root", default=".", help="Project root (default: .)")
    parser.add_argument(
        "--no-git", action="store_true", help="Walk filesystem instead of git ls-files"
    )
    parser.add_argument(
        "--min-count", type=int, default=1, help="Only show tools used at least N times"
    )
    parser.add_argument(
        "--list-tools", action="store_true", help="Print tools per toolbox"
    )
    parser.add_argument(
        "--with-locations",
        action="store_true",
        help="Show file:line locations for each tool",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    files = list(iter_python_files(root, use_git=not args.no_git))

    occurrences_by_full: dict[str, list[Occurrence]] = defaultdict(list)
    for file_path in files:
        for full, occ in scan_file(file_path):
            occurrences_by_full[full].append(occ)

    toolbox_tool_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for full, occs in occurrences_by_full.items():
        toolbox, tool = _split_toolbox_and_tool(full)
        toolbox_tool_counts[toolbox][tool] += len(occs)

    # Print summary
    unique_tools_per_toolbox = {
        tb: len(counter) for tb, counter in toolbox_tool_counts.items()
    }
    sorted_toolboxes = sorted(
        toolbox_tool_counts.keys(),
        key=lambda tb: (-(unique_tools_per_toolbox[tb]), tb),
    )

    print(f"Scanned: {len(files)} Python files")
    total_unique = sum(unique_tools_per_toolbox.values())
    print(f"Found:   {total_unique} unique ArcPy tools\n")

    print("Toolboxes (unique tools):")
    for tb in sorted_toolboxes:
        print(f"  {tb}: {unique_tools_per_toolbox[tb]}")

    if args.list_tools:
        print("\nTools:")
        for tb in sorted_toolboxes:
            tools_sorted = sorted(
                toolbox_tool_counts[tb].items(),
                key=lambda kv: (-kv[1], kv[0]),
            )
            # apply min-count
            tools_sorted = [(t, c) for t, c in tools_sorted if c >= args.min_count]
            if not tools_sorted:
                continue

            print(f"\n[{tb}]")
            for tool, count in tools_sorted:
                print(f"  {tool} ({count})")
                if args.with_locations:
                    # locations are keyed by fully resolved name; reconstruct candidate full names
                    # for printing locations, match any resolved full that maps to this (tb, tool)
                    for full, occs in occurrences_by_full.items():
                        tb2, tool2 = _split_toolbox_and_tool(full)
                        if tb2 == tb and tool2 == tool:
                            for occ in occs:
                                rel = str(Path(occ.file).resolve().relative_to(root))
                                print(f"    - {rel}:{occ.line}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
