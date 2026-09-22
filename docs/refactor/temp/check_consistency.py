#!/usr/bin/env python3
"""Consistency checks over DECISIONS.md, TASKS.md and 01-terminology.md.

STAGING TOOLING. Dies with temp/, like everything else here.

Run from anywhere:  python3 docs/refactor/temp/check_consistency.py
Exit code is non-zero if any check fails, so this can go in CI unchanged.

Each check below was written because it found a real defect, not speculatively:

  A-orphan       found A18 and A17.3 — items with a `destination:` and no task,
                 which under the completion test would never have migrated.
  dangling-ref   guards the reverse: a task citing an A-id that does not exist.
  ordering       found T3.6 depending on T3.5 while sitting above it.
  term-cites     found `mint generation` citing A9.10, which did not use the phrase.
  term-headword  found the same thing from the other direction, and later caught an
                 edit that *looked* applied but had wrapped across a line break, so
                 the phrase was not greppable. Grep after editing, not only before.

The two checks here cover only A-id citations, which die with this directory. The
permanent half lives in `docs/refactor/check_terminology.py` and covers the 43
`file.md#anchor` citations that predate the lineage work. Run both; neither subsumes
the other.

A GREEN RUN CAN MEAN NOTHING. Twice now a check passed because the case it would catch
happened to be absent, not because the rule worked:

  * the A-orphan exemption matched `**A12.8**`, but a superseded entry is written
    `**A12.8 — SUPERSEDED.**`, so the rule never fired. Earlier passes were green by
    coincidence — masked by an ad-hoc by-name exclusion in the throwaway version.
  * an edit that added a term was not greppable, because the phrase wrapped a line.

Both surfaced only when ad-hoc checking got formalised. When adding a check, break it
on purpose once and confirm it fails. A rule that never fires is worse than no rule,
because a green run from it is trusted.
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DECISIONS = (HERE / "DECISIONS.md").read_text(encoding="utf-8")
TASKS = (HERE / "TASKS.md").read_text(encoding="utf-8")
TERMS = (HERE.parent / "01-terminology.md").read_text(encoding="utf-8")

# Headwords whose wording legitimately differs from the prose in DECISIONS.
# Keep this list short and justified; a new entry is a small smell.
HEADWORD_VARIANCE = {
    "lineage edge": "spelled `LineageEdge` as a type",
    "row shape": "spelled `@row_shape` / `Rows`",
    "disk-backed id map": "prose says 'the id map is disk-backed'",
    "parents": "appears as `parents=` and `PARENT_ID`",
}

# The documents are UTF-8 and the messages below carry non-ASCII; on Windows the default
# console encoding is the locale code page, so the output stream is set explicitly.
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8")

failures: list[str] = []


def report(check: str, bad: list[str], detail: str = "") -> None:
    if bad:
        failures.append(check)
        print(f"FAIL  {check}{(' — ' + detail) if detail else ''}")
        for item in bad:
            print(f"        {item}")
    else:
        print(f"ok    {check}")


def a_ids(text: str) -> set[str]:
    """Sub-items (**A9.10**) plus section headings (## A9.)."""
    return set(re.findall(r"\*\*(A\d+\.\d+[a-z]?)\b", text)) | set(
        re.findall(r"^## (A\d+)\.", text, re.M)
    )


def expand_ranges(text: str) -> set[str]:
    """A9.3–A9.9 covers A9.4 .. A9.8 as well as its endpoints."""
    out: set[str] = set()
    for lo_s, hi_s in re.findall(r"\b(A\d+\.\d+)\s*[–-]\s*(A?\d+\.\d+)", text):
        major, lo = lo_s[1:].split(".")
        hi = hi_s.split(".")[-1]
        out |= {f"A{major}.{n}" for n in range(int(lo), int(hi) + 1)}
    return out


defined = a_ids(DECISIONS)
sub_items = {a for a in defined if "." in a}
cited_in_tasks = set(re.findall(r"\bA\d+\.\d+[a-z]?\b", TASKS)) | expand_ranges(TASKS)

# An A-item may legitimately have no task if its own destination says so.
# Match `**A12.8` rather than `**A12.8**`: a superseded entry is written
# `**A12.8 — SUPERSEDED.**`, so requiring the closing marker silently never fires.
# The (?![0-9.]) stops **A1.1 matching the start of **A1.10.
exempt = {
    a
    for a in sub_items
    if re.search(
        re.escape(f"**{a}") + r"(?![0-9.]).{0,3000}?`destination:` none", DECISIONS, re.S
    )
}

report(
    "A-orphan      every A-item rides on a task (or is destination:none)",
    sorted(a for a in sub_items if a not in cited_in_tasks and a not in exempt),
    "add it to a task's doc migration, or give it destination: none",
)

report(
    "dangling-ref  every A-id cited in TASKS exists in DECISIONS",
    sorted(cited_in_tasks - defined - {a for a in defined}),
)

# --- ordering: a dependency must sit above its dependent -------------------
order = [m[1] for m in re.findall(r"^\| ([0-9]+[a-c]?|—) \| (T[0-9.]+|B\d) \|", TASKS, re.M)]
position = {task: i for i, task in enumerate(order)}
violations = []
for block in re.split(r"\n## ", TASKS)[1:]:
    head = re.match(r"[0-9]+[a-c]?\. (T[0-9.]+)", block)
    deps = re.search(r"\*\*depends on\*\* (.+)", block)
    if not (head and deps):
        continue
    me = head.group(1)
    for dep in re.findall(r"T[0-9.]+", deps.group(1)):
        if dep in position and me in position and position[dep] > position[me]:
            violations.append(f"{me} (pos {position[me]}) depends on {dep} (pos {position[dep]})")
report("ordering      dependencies precede dependents", violations)

report(
    "B-referenced  every open question is named by a task",
    sorted(b for b in set(re.findall(r"\*\*(B\d+)", DECISIONS)) if b not in TASKS),
)

# --- terminology -----------------------------------------------------------
# Rows look like:  | **term** | meaning | A11.5, A11.6 |
term_rows = re.findall(r"^\| \*\*`?(.+?)`?\*\*[^|]*\|([^|]+)\|\s*([^|]*?)\s*\|$", TERMS, re.M)
term_cites: set[str] = set()
for _, _, authority in term_rows:
    term_cites |= set(re.findall(r"\bA\d+(?:\.\d+[a-z]?)?\b", authority))

report(
    "term-cites    terminology authorities resolve in DECISIONS",
    sorted(term_cites - defined),
    "repoint to the real destination once the A-item migrates",
)

missing_headwords = []
for name, _, authority in term_rows:
    if not re.search(r"\bA\d+", authority):
        continue  # not a lineage-design term; authority is a real doc
    key = name.split(" (")[0].strip().strip("`")
    if key in HEADWORD_VARIANCE:
        continue
    squashed = re.sub(r"[\s_\-]", "", key).lower()
    if key.lower() in DECISIONS.lower():
        continue
    if squashed and squashed in re.sub(r"[\s_\-]", "", DECISIONS).lower():
        continue
    missing_headwords.append(f"{key}  (cites {authority.strip()})")
report(
    "term-headword every headword appears in DECISIONS",
    missing_headwords,
    "a rename, a typo, or an edit that wrapped across a line break",
)

print()
if failures:
    print(f"{len(failures)} check(s) failed")
    sys.exit(1)
print("all checks passed")
