"""Every ADR citation resolves, and no ADR body cites the staging record.

What: four rules over the tracked files under `src/`, `tests/` and `docs/`. An `ADR-nnnn`
names a file under `docs/decisions/`; an id such as `RS-D5` exists in the ADR whose prefix
it carries; a retired number, one the README's provenance table lists, is cited nowhere but
that README and `docs/decisions/evidence/`; an ADR body cites no A-id, B-id, task id, slice
or pull request outside its Scope line.

How: the file list is `git ls-files`, so untracked work cannot make the check fail on one
machine and pass in CI; the ADR directory itself is read from disk, so a new ADR is both
resolvable and checked before it is staged. Ids are collected from section headings and
`**XX-Dn**` bullets, and only the prefixes the ADRs define are matched. The id rule skips
`docs/refactor/temp/`, the staging record, whose working documents discuss ids that are not
in force.

Why: no hook resolves ADR ids otherwise, and the cut-over to themed ADRs changed every
citation at once. A rule that never fires is worse than none, so each is broken once in
`tools/break_once/cases/adr_citations.py`.
"""

from __future__ import annotations

import re
import subprocess
from functools import cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DECISIONS = ROOT / "docs" / "decisions"
README = DECISIONS / "README.md"
EVIDENCE = DECISIONS / "evidence"
STAGING = ROOT / "docs" / "refactor" / "temp"
SCANNED = ("src", "tests", "docs")
TEXT_SUFFIXES = frozenset(
    {".py", ".md", ".toml", ".yaml", ".yml", ".txt", ".cfg", ".ini"}
)

RULES = (
    "number-resolves",
    "id-exists",
    "no-retired-number",
    "body-cites-no-staging-id",
)

NUMBER = re.compile(r"ADR-(\d{4})\b")
ID_LINE = re.compile(r"^(?:## |- \*\*)([A-Z]{2})-((?:D|R)?\d+)\b", re.M)
STAGING_ID = re.compile(
    r"\bA\d+\.\d+[a-z]?\b|\bB\d+\b|\bT\d+\.\d+\b|\bslice \d|\bPR #\d+"
)
PROVENANCE_ROW = re.compile(r"^\| (\d{4}) \| ", re.M)


@cache
def tracked_text_files() -> tuple[Path, ...]:
    """The tracked text files under the scanned roots, from `git ls-files`.

    A tracked path whose deletion is not yet staged is skipped: it has no content.
    """
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", *SCANNED],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    names = (n for n in out.decode("utf-8").split("\0") if n)
    paths = (ROOT / n for n in names if Path(n).suffix in TEXT_SUFFIXES)
    return tuple(p for p in paths if p.exists())


@cache
def adr_files() -> dict[int, Path]:
    """The ADRs on disk, by number."""
    found = {int(p.name[:4]): p for p in DECISIONS.glob("[0-9][0-9][0-9][0-9]-*.md")}
    assert found, f"no ADR files under {DECISIONS}"
    return found


@cache
def ids_by_prefix() -> dict[str, tuple[int, frozenset[str]]]:
    """Per prefix, the ADR that defines it and the ids it defines."""
    table: dict[str, tuple[int, set[str]]] = {}
    for number, path in adr_files().items():
        for prefix, tail in ID_LINE.findall(path.read_text(encoding="utf-8")):
            owner, ids = table.setdefault(prefix, (number, set()))
            assert owner == number, (
                f"prefix {prefix} is defined by ADR {owner} and {number}"
            )
            ids.add(f"{prefix}-{tail}")
    assert table, "no ids found in the ADRs"
    return {prefix: (number, frozenset(ids)) for prefix, (number, ids) in table.items()}


@cache
def retired_numbers() -> frozenset[int]:
    """The numbers the README's provenance table retires."""
    text = README.read_text(encoding="utf-8")
    start = text.index("## Provenance")
    numbers = frozenset(int(n) for n in PROVENANCE_ROW.findall(text[start:]))
    assert numbers, "the provenance table lists no retired number"
    return numbers


def _is_under(path: Path, parent: Path) -> bool:
    return parent == path or parent in path.parents


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def number_resolves() -> list[str]:
    bad: list[str] = []
    for path in tracked_text_files():
        if _is_under(path, EVIDENCE):
            continue
        for match in NUMBER.finditer(path.read_text(encoding="utf-8")):
            number = int(match.group(1))
            if number not in adr_files() and number not in retired_numbers():
                bad.append(f"{_relative(path)}: ADR-{number:04d} names no file")
    return bad


def id_exists() -> list[str]:
    prefixes = "|".join(sorted(ids_by_prefix()))
    token = re.compile(rf"\b({prefixes})-((?:D|R)?\d+)\b")
    bad: list[str] = []
    for path in tracked_text_files():
        if _is_under(path, EVIDENCE) or _is_under(path, STAGING):
            continue
        for prefix, tail in token.findall(path.read_text(encoding="utf-8")):
            number, ids = ids_by_prefix()[prefix]
            if f"{prefix}-{tail}" not in ids:
                bad.append(
                    f"{_relative(path)}: {prefix}-{tail} is not in ADR-{number:04d}"
                )
    return bad


def no_retired_number() -> list[str]:
    bad: list[str] = []
    for path in tracked_text_files():
        if path == README or _is_under(path, EVIDENCE):
            continue
        for match in NUMBER.finditer(path.read_text(encoding="utf-8")):
            number = int(match.group(1))
            if number in retired_numbers():
                bad.append(f"{_relative(path)}: ADR-{number:04d} is retired")
    return bad


def body_cites_no_staging_id() -> list[str]:
    bad: list[str] = []
    for number, path in adr_files().items():
        body = _without_scope(path.read_text(encoding="utf-8"))
        for match in STAGING_ID.finditer(body):
            bad.append(f"ADR-{number:04d}: cites {match.group(0)!r} outside Scope")
    return bad


def _without_scope(text: str) -> str:
    """The ADR text minus its Scope paragraph, the one place an A-id may appear."""
    start = text.find("**Scope:**")
    if start < 0:
        return text
    end = text.find("\n\n", start)
    return text[:start] + (text[end:] if end >= 0 else "")


CHECKS = {
    "number-resolves": number_resolves,
    "id-exists": id_exists,
    "no-retired-number": no_retired_number,
    "body-cites-no-staging-id": body_cites_no_staging_id,
}


@pytest.mark.parametrize("rule", RULES)
def test_rule_holds(rule: str) -> None:
    failures = CHECKS[rule]()
    assert not failures, "\n".join(failures)


def test_every_prefix_is_defined_once() -> None:
    assert ids_by_prefix()
