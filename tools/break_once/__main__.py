"""Command line: `python -m tools.break_once [set ...] [--check] [--out FILE]`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine import load_sets, preflight, run_set


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tools.break_once",
        description="Breaks each guard of a case set once, runs its tests, restores the file.",
    )
    parser.add_argument("sets", nargs="*", help="case sets to run; default: all")
    parser.add_argument(
        "--check",
        action="store_true",
        help="preflight only: needles match and targets collect; nothing is edited",
    )
    parser.add_argument(
        "--out", type=Path, help="write the report here instead of stdout"
    )
    args = parser.parse_args(argv)
    sets = load_sets(args.sets or None)
    problems = preflight(sets)
    if problems:
        print("break-it-once: harness errors, nothing was edited", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    cases = sum(len(case_set.cases) for case_set in sets)
    if args.check:
        print(
            f"break-it-once: {cases} cases in {len(sets)} set(s); needles match, targets collect"
        )
        return 0
    bad = 0
    reports: list[str] = []
    for case_set in sets:
        set_bad, report = run_set(case_set)
        bad += set_bad
        reports.append(report)
    text = "\n".join(reports)
    if args.out is None:
        print(text)
    else:
        args.out.write_text(text, encoding="utf-8")
    print(f"break-it-once: {cases} cases, {bad} unexpected", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
