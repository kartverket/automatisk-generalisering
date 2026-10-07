#!/usr/bin/env python3
"""Terminology invariants. PERMANENT — this outlives `temp/`.

Run:  python3 docs/refactor/check_terminology.py
Exits non-zero on failure, so it can go into CI unchanged.

`01-terminology.md` says of itself: "Where a definition and a design document disagree,
the authoritative document listed in the entry wins and this file is the bug." Nothing
enforced that. These two checks do:

  authority-resolves  every `file.md#anchor` an entry cites actually exists. Rename a
                      heading in 02-runtime.md and the glossary silently points nowhere.
  headword-present    every term appears somewhere in the document it cites. Rename a
                      concept and the glossary keeps the old word, which is worse than
                      having no glossary — people trust it.

WHY THESE TWO AND NOT THE REST. The checks in `temp/check_consistency.py` are about the
migration itself — A-items riding on tasks, task ordering — and they die when `temp/`
does. These two do not: after migration the authority column stops citing A-ids and
starts citing ADRs and docstrings, and the same two questions still need answering.
There are already 43 anchor citations here that predate the lineage work.

A NOTE ON GREEN RUNS, learned twice while building the sibling script.

A check can pass because the case it would catch happens to be absent, not because the
rule works. The orphan check in `temp/` ran green for several passes with its exemption
rule permanently misfiring — a hardcoded by-name exclusion masked it. Separately, an edit
that *looked* applied was not greppable because the phrase wrapped across a line break.

Both only surfaced when ad-hoc checking got formalised. So: when adding a check here,
break it on purpose once and confirm it fails. A green run from a rule that never fires
is worse than no check, because it is trusted.
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent
TERMS_PATH = DOCS / "01-terminology.md"
TERMS = TERMS_PATH.read_text(encoding="utf-8")

# Headwords whose wording legitimately differs from the prose they cite.
# Keep short and justified; a growing list is a smell, not a solution.
HEADWORD_VARIANCE = {
    "lineage edge": "spelled `LineageEdge` as a type",
    "row shape": "spelled `@row_shape` / `Rows`",
    "disk-backed id map": "prose says 'the id map is disk-backed'",
    "parents": "appears as `parents=` and `PARENT_ID`",
    "halo": "the entry is 'halo / context radius'; prose uses either",
}

# The documents are UTF-8 and the messages below carry non-ASCII; on Windows the default
# console encoding is the locale code page, so the output stream is set explicitly.
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8")

failures: list[str] = []


def report(check: str, bad: list[str], hint: str = "") -> None:
    if bad:
        failures.append(check)
        print(f"FAIL  {check}{(' — ' + hint) if hint else ''}")
        for item in bad:
            print(f"        {item}")
    else:
        print(f"ok    {check}")


def github_anchor(heading: str) -> str:
    """GitHub's slug: lowercase, drop punctuation, spaces to hyphens."""
    text = re.sub(r"`", "", heading.strip())
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return re.sub(r"\s+", "-", text.strip()).lower()


def anchors_of(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        github_anchor(m.group(1))
        for m in re.finditer(
            r"^#{1,6}\s+(.+?)\s*$", path.read_text(encoding="utf-8"), re.M
        )
    }


# Rows: | **term** | meaning | authority |
rows = re.findall(r"^\| \*\*`?(.+?)`?\*\*([^|]*)\|([^|]+)\|\s*(.*?)\s*\|$", TERMS, re.M)

# --- 1. every cited anchor resolves ---------------------------------------
anchor_cache: dict[str, set[str]] = {}
broken: list[str] = []
for name, _, _, authority in rows:
    for target, anchor in re.findall(r"\]\(([0-9a-z-]+\.md)#([a-z0-9-]+)\)", authority):
        if target not in anchor_cache:
            anchor_cache[target] = anchors_of(DOCS / target)
        if not anchor_cache[target]:
            broken.append(f"{name}: {target} does not exist")
        elif anchor not in anchor_cache[target]:
            broken.append(f"{name}: {target}#{anchor} — no such heading")
report(
    "authority-resolves  every cited file.md#anchor exists",
    broken,
    "a heading was renamed, or the citation was never right",
)

# --- 2. every headword appears in what it cites ---------------------------
doc_cache: dict[str, str] = {}
missing: list[str] = []
for name, _, _, authority in rows:
    key = name.split(" (")[0].strip().strip("`")
    if key in HEADWORD_VARIANCE:
        continue
    targets = set(re.findall(r"\]\(([0-9a-z-]+\.md)#", authority))
    if not targets:
        continue  # A-id citations are temp/'s problem until migration completes
    hay = ""
    for target in targets:
        if target not in doc_cache:
            p = DOCS / target
            doc_cache[target] = p.read_text(encoding="utf-8") if p.exists() else ""
        hay += doc_cache[target]
    squashed_hay = re.sub(r"[\s_\-]", "", hay).lower()
    squashed_key = re.sub(r"[\s_\-]", "", key).lower()
    if key.lower() in hay.lower() or (squashed_key and squashed_key in squashed_hay):
        continue
    missing.append(f"{key}  (cites {', '.join(sorted(targets))})")
report(
    "headword-present    every term appears in the doc it cites",
    missing,
    "a concept was renamed and the glossary kept the old word",
)

print()
if failures:
    print(f"{len(failures)} check(s) failed")
    sys.exit(1)
print("all terminology checks passed")
