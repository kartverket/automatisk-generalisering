"""The break-it-once engine: preflight, baseline, mutate, verdict, restore.

What: a case names a source file, one or more exact text edits that remove a guard, and
the pytest targets that must then fail. A run proves, per case, that the targets pass on
the clean tree and fail once the guard is gone, and restores the file either way.

How: three stages. Preflight, before anything is edited: every needle matches its file
exactly once and every target collects; a stale needle or a renamed test is a harness
error, never a caught guard. Per case: a baseline run of the case's own targets with the
identical command, which must exit 0 with every target reported `PASSED`; then the edit,
the same run again, which must exit 1 with every target reported, a node id as `FAILED`
or `ERROR` and a module as `ERROR`, since a module target is one that must fail to
import; then the restore, in a `finally`. Last, the set's suite on the restored tree.
The pytest flags the verdict reads are passed explicitly: `-rA` for the per-test summary
lines and `--continue-on-collection-errors` so a module that fails to import is reported
beside the other targets instead of ending the session. Bytecode under `src` is cleared
before each run, because Python validates a `.pyc` by source size and mtime only.

Why: a guard that has never been seen to fail is not known to work, and a verdict that
accepts any nonzero exit would read a renamed test (exit 4, "not found") as a failure.
The baseline closes the other false green: a target that fails in isolation on the clean
tree would fail under every mutation too.
"""

from __future__ import annotations

import importlib
import os
import pkgutil
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTEST_FLAGS = (
    "-q",
    "-rA",
    "-p",
    "no:cacheprovider",
    "--no-header",
    "--continue-on-collection-errors",
)
_SUMMARY_LINE = re.compile(r"^(FAILED|ERROR|SKIPPED|XFAIL|XPASS) ", re.M)


@dataclass(frozen=True)
class Case:
    """One guard: the file, the edits that remove it, and the targets that then fail.

    A target is a pytest node id, or a test module path when the edit must make that
    module fail to import.
    """

    id: str
    title: str
    file: str
    edits: tuple[tuple[str, str], ...]
    tests: tuple[str, ...]


@dataclass(frozen=True)
class CaseSet:
    """The cases of one lift, and the suite run after the last restore."""

    name: str
    cases: tuple[Case, ...]
    suite: tuple[str, ...]


def tests_in(file: str, *names: str) -> tuple[str, ...]:
    """Node ids for `names` in one test file."""
    return tuple(f"{file}::{name}" for name in names)


def load_sets(names: Sequence[str] | None = None) -> list[CaseSet]:
    """The case sets under `cases/`, all of them or the named ones, by module name."""
    from . import cases as package

    found: dict[str, CaseSet] = {}
    for info in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package.__name__}.{info.name}")
        found[info.name] = CaseSet(info.name, module.CASES, module.SUITE)
    if names is None:
        return [found[name] for name in sorted(found)]
    unknown = [name for name in names if name not in found]
    if unknown:
        raise SystemExit(
            f"unknown case set(s): {', '.join(unknown)}; known: {', '.join(sorted(found))}"
        )
    return [found[name] for name in names]


def run_pytest(
    targets: tuple[str, ...], *, collect_only: bool = False
) -> tuple[int, str]:
    """Runs pytest on `targets` with the fixed flags; returns the exit code and output."""
    for cache in (ROOT / "src").rglob("__pycache__"):
        shutil.rmtree(cache)
    extra = ("--collect-only",) if collect_only else ()
    # UTF-8 on both sides whatever the console code page: the child writes UTF-8 and the
    # output is decoded as UTF-8, so a non-ASCII character in a message cannot break a run.
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *PYTEST_FLAGS, *extra, *targets],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"},
    )
    return proc.returncode, proc.stdout + proc.stderr


def read_source(path: Path) -> tuple[bytes, str]:
    """The file's bytes, and its text with `\\n` line endings whatever the file uses.

    Needles are written with `\\n`; a clone with CRLF files must match them too, and the
    restore must put back the exact bytes, so the bytes are kept beside the text.
    """
    data = path.read_bytes()
    return data, data.decode("utf-8").replace("\r\n", "\n")


def write_source(path: Path, text: str, *, like: bytes) -> None:
    """Writes `text` with the line endings the original bytes `like` use."""
    newline = "\r\n" if b"\r\n" in like else "\n"
    path.write_bytes(text.replace("\n", newline).encode("utf-8"))


def reported(kinds: str, target: str, out: str, *, members: bool = False) -> bool:
    """Whether a summary line `<kind> <target>` is in `out`.

    A parametrised node id is reported with its `[param]` suffix, so the target may be
    followed by `[...]`, by ` - message`, or by the end of the line. With `members`, a
    module target also counts when one of its tests is reported (`<module>::name`), which
    the baseline wants and the verdict must not: a module target's expected failure is
    the module's own `ERROR` line, not a test inside it failing.
    """
    suffix = r"(?:\[[^\]]*\]|::\S+)?" if members else r"(?:\[[^\]]*\])?"
    pattern = rf"^(?:{kinds}) {re.escape(target)}{suffix}(?: - .*)?$"
    return re.search(pattern, out, re.M) is not None


def mutate(original: str, edits: tuple[tuple[str, str], ...]) -> str | None:
    """Applies the edits, or returns None when a needle is missing or not unique."""
    mutated = original
    for old, new in edits:
        if old == "":
            mutated += new
            continue
        if mutated.count(old) != 1:
            return None
        mutated = mutated.replace(old, new)
    return mutated


def preflight(sets: Iterable[CaseSet]) -> list[str]:
    """Problems that make a run meaningless, found on the clean tree before any edit."""
    problems: list[str] = []
    targets: set[str] = set()
    for case_set in sets:
        for case in case_set.cases:
            _, original = read_source(ROOT / case.file)
            if mutate(original, case.edits) is None:
                problems.append(
                    f"{case_set.name}/{case.id}: a needle is missing from {case.file} "
                    "or matches more than once"
                )
            targets.update(case.tests)
    code, out = run_pytest(tuple(sorted(targets)), collect_only=True)
    if code != 0:
        detail = [
            line for line in out.splitlines() if "ERROR" in line or "not found" in line
        ]
        problems.append(
            "targets do not collect:\n  " + "\n  ".join(detail or [out.strip()])
        )
    problems.extend(
        f"target not collected: {target}" for target in uncollected(targets, out)
    )
    return problems


def uncollected(targets: Iterable[str], collect_output: str) -> list[str]:
    """Targets that a `--collect-only -q` run did not list.

    Why not the exit code alone: when a module is itself a target, pytest treats a node
    id inside it that no longer exists as matched and exits 0, so a renamed test would
    pass unnoticed. A node id must appear as itself or with a `[param]` suffix; a module
    must have at least one collected `module::name`.
    """
    collected = [line.strip() for line in collect_output.splitlines() if "::" in line]
    missing: list[str] = []
    for target in sorted(set(targets)):
        if target.endswith(".py"):
            found = any(item.startswith(f"{target}::") for item in collected)
        else:
            found = any(
                item == target or item.startswith(f"{target}[") for item in collected
            )
        if not found:
            missing.append(target)
    return missing


def baseline(case: Case) -> str | None:
    """Why the case's targets do not pass on the clean tree, or None when they do."""
    code, out = run_pytest(case.tests)
    return baseline_problem(case, code, out)


def baseline_problem(case: Case, code: int, out: str) -> str | None:
    """Reads a clean-tree run: exit 0, a `PASSED` line per target, nothing else reported.

    A module target passes through any of its tests passing; a node id through its own
    line, with any parameter.
    """
    missing = [
        target
        for target in case.tests
        if not reported("PASSED", target, out, members=target.endswith(".py"))
    ]
    not_passed = [line for line in out.splitlines() if _SUMMARY_LINE.match(line)]
    if code == 0 and not missing and not not_passed:
        return None
    detail = not_passed or [f"no PASSED line for {target}" for target in missing]
    return f"baseline exit {code}:\n" + "\n".join(detail[:8])


def verdict(case: Case, code: int, out: str) -> bool:
    """Whether the mutated run failed the way the case says it must.

    Exit code 1 (tests failed or errored; 4 is an unknown target, 2 an interrupted
    session), a `FAILED` or `ERROR` line per node id, and for a module target the
    module's own `ERROR` line: a test failing inside the module is not the collection
    failure the case claims.
    """
    if code != 1:
        return False
    return all(
        reported("ERROR", target, out)
        if target.endswith(".py")
        else reported("FAILED|ERROR", target, out)
        for target in case.tests
    )


def excerpt(out: str) -> str:
    """The lines of a pytest report a reader needs: assertions, verdict lines, summary."""
    keep: list[str] = []
    for line in out.splitlines():
        stripped = line.strip()
        if (
            stripped.startswith(("E ", ">", "FAILED", "ERROR"))
            or "passed" in stripped
            or "failed" in stripped
        ) and line.rstrip() not in keep:
            keep.append(line.rstrip())
    return "\n".join(keep[:14])


def describe(old: str, new: str) -> str:
    """One line naming an edit by its first line."""
    if old == "":
        return f"append {new.strip().splitlines()[0]!r} ..."
    if new.strip() == "":
        return f"delete `{old.strip().splitlines()[0]}`"
    return f"`{old.strip().splitlines()[0]}` -> `{new.strip().splitlines()[0]}`"


def run_case(case: Case) -> tuple[bool, str]:
    """Baseline, mutate, run, restore; returns (as expected, the case's report)."""
    head = f"### {case.id}: {case.title}\n\nFile: `{case.file}`."
    problem = baseline(case)
    if problem is not None:
        return (
            False,
            f"{head}\n\nResult: **HARNESS ERROR, nothing mutated**\n\n```\n{problem}\n```\n",
        )
    path = ROOT / case.file
    original_bytes, original = read_source(path)
    mutated = mutate(original, case.edits)
    if mutated is None:
        return (
            False,
            f"{head}\n\nResult: **HARNESS ERROR, needle not unique, nothing mutated**\n",
        )
    write_source(path, mutated, like=original_bytes)
    try:
        code, out = run_pytest(case.tests)
    finally:
        path.write_bytes(original_bytes)
    ok = verdict(case, code, out)
    edits = "; ".join(describe(old, new) for old, new in case.edits)
    targets = ", ".join(t.split("::")[-1] if "::" in t else t for t in case.tests)
    result = "FAILED as expected" if ok else "UNEXPECTED"
    return ok, (
        f"{head} Edit: {edits}.\n\nTargets: {targets}. Baseline: passed.\n\n"
        f"Result: **{result}** (exit {code})\n\n```\n{excerpt(out)}\n```\n"
    )


def run_set(case_set: CaseSet) -> tuple[int, str]:
    """Runs every case of one set and its suite afterwards; returns (bad count, report)."""
    lines = [
        f"Case set `{case_set.name}`, run by `python -m tools.break_once {case_set.name}`. "
        "Per case: its targets pass on the clean tree (baseline), one source file is "
        "edited to remove the guard, the same targets must then fail, and the file is "
        "restored. The set's suite runs after the last restore.\n"
    ]
    bad = 0
    for case in case_set.cases:
        ok, report = run_case(case)
        bad += 0 if ok else 1
        lines.append(report)
    code, out = run_pytest(case_set.suite)
    bad += 0 if code == 0 else 1
    lines.append(
        f"### After the last restore\n\n```\n{out.strip().splitlines()[-1]}\n```\n"
    )
    return bad, "\n".join(lines)
