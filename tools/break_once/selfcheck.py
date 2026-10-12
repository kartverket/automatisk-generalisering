"""The harness checking itself where a subprocess and a real edit are needed.

What: four scenarios the unit tests in `tests/unit/tools/test_break_once.py` cannot cover
without pytest running: a renamed target stops at preflight; with preflight bypassed the
baseline stops the same case; a target that fails in isolation is stopped by the baseline;
a renamed test that a case references fails the preflight the hook runs. Every file the
scenarios touch is hashed before and after.

How: `python -m tools.break_once --self-check`. The probe cases are built in memory from
the first case set, so the committed tables are not edited; the one temporary test file is
removed in a `finally`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .engine import (
    ROOT,
    Case,
    CaseSet,
    load_sets,
    preflight,
    read_source,
    run_case,
    write_source,
)

PROBE_TEST = "tests/unit/tools/test_zz_self_check_probe.py"
PROBE_SOURCE = (
    '"""Temporary: test_second passes only after test_first ran in the same session."""\n'
    "\n_seen: list[int] = []\n\n\n"
    "def test_first() -> None:\n    _seen.append(1)\n\n\n"
    "def test_second() -> None:\n    assert _seen\n"
)


def _digest(paths: list[Path]) -> dict[Path, str]:
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def self_check() -> tuple[int, str]:
    """Runs the four scenarios; returns (number that did not behave, the report)."""
    sets = load_sets()
    first_set = sets[0]
    sample = first_set.cases[0]
    node = next(t for case in first_set.cases for t in case.tests if "::" in t)
    test_file, test_name = node.split("::", 1)
    watched = sorted(
        {ROOT / case.file for case_set in sets for case in case_set.cases}
        | {
            ROOT / t.split("::")[0]
            for case_set in sets
            for case in case_set.cases
            for t in case.tests
        }
    )
    before = _digest(watched)
    lines: list[str] = []
    bad = 0

    def record(title: str, ok: bool, detail: str) -> None:
        nonlocal bad
        bad += 0 if ok else 1
        lines.append(
            f"### {title}\n\nResult: **{'as expected' if ok else 'UNEXPECTED'}**\n\n"
            f"```\n{detail.strip()}\n```\n"
        )

    stale = Case(
        "SC-A",
        "a real edit with a renamed target",
        sample.file,
        sample.edits,
        (f"{test_file}::test_this_name_does_not_exist",),
    )
    problems = preflight([CaseSet("self-check", (stale,), ())])
    record(
        "A. A renamed target stops at preflight, nothing edited",
        any("not found" in problem for problem in problems),
        "\n".join(problems),
    )

    ok, report = run_case(stale)
    record(
        "B. With preflight bypassed, the baseline stops the same case",
        not ok and "HARNESS ERROR" in report,
        report.split("Result: ", 1)[-1],
    )

    probe = ROOT / PROBE_TEST
    probe.write_text(PROBE_SOURCE, encoding="utf-8")
    try:
        dependent = Case(
            "SC-E",
            "a real edit named by a test that needs another test's state",
            sample.file,
            sample.edits,
            (f"{PROBE_TEST}::test_second",),
        )
        collects = preflight([CaseSet("self-check", (dependent,), ())])
        ok, report = run_case(dependent)
    finally:
        probe.unlink()
    record(
        "E. A target that fails in isolation is stopped by the baseline",
        not collects and not ok and "HARNESS ERROR" in report,
        f"preflight problems: {collects or 'none, it collects'}\n"
        + report.split("Result: ", 1)[-1],
    )

    path = ROOT / test_file
    data, text = read_source(path)
    needle = f"def {test_name}("
    renamed = text.replace(needle, f"def {test_name}_renamed(")
    write_source(path, renamed, like=data)
    try:
        problems = preflight(sets)
    finally:
        path.write_bytes(data)
    record(
        "H. A renamed referenced test fails the preflight the hook runs",
        any(test_name in problem for problem in problems),
        "\n".join(problems),
    )

    after = _digest(watched)
    changed = [str(p.relative_to(ROOT)) for p in watched if before[p] != after[p]]
    record(
        "Hashes of every case file and test file",
        not changed and not probe.exists(),
        "identical before and after"
        if not changed
        else "CHANGED: " + ", ".join(changed),
    )
    return bad, "\n".join(lines)
