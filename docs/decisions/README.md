# Architecture decision records

The ADRs in this directory are the source of truth for the architecture and the design
direction of `src/ag`. They exist so that separate pull requests build towards the same
design. Work does not contradict a Direction statement; a change that would is a Direction
change.

**Consolidation in progress.** The ADRs are being consolidated into themed ADRs. Until the
cut-over they live in `docs/refactor/decisions/`, the ADRs there stay in force, and nothing
cites a new number.

## Index

Reading order, not numeric order. Filled in at the cut-over.

| ADR | prefix | theme | governs |
|---|---|---|---|

## What an ADR is

One ADR per theme, not per decision. A theme is a subject a contributor has a question
about: the ports, what crosses them, how an operation is declared, how a stage is declared
and run. A decision that fits no existing theme and constrains future work opens a new
theme; a decision that fits one is a section or a detail in it.

An ADR opens with:

- **Status**: the status and the date, nothing else.
- **Scope**: the packages the ADR governs and, while the lineage decision record exists,
  the A-items it absorbed.
- **Direction**: the few statements that define the theme.

The body is sections. Each opens with a one- or two-sentence **Direction** line, followed
by **Details**: the rules, contracts and specifics that serve it. The ADR ends with
**Rejected**: the alternatives likely to be proposed again, each with why it was rejected
and what would reopen it.

Every section, detail and rejected entry carries a stable, visible id: the theme prefix,
then `-n` for a section, `-Dn` for a detail and `-Rn` for a rejected entry, numbered across
the whole ADR so an item can move between sections. Ids are never renumbered or reused; a
removed id is simply gone.

## Writing rules

- **Current state only.** Every ADR reads as if written today. No history, no contrast
  with an earlier design, no citation of a retired ADR. Replaced or removed content is
  deleted, not marked superseded; a superseded ADR file is removed. Git holds the history.
- **The lean test for a detail.** It stays if it constrains future code or design, or
  stops a likely mistake. It goes if it only explains or reports how a decision was
  reached.
- **The Rejected test.** An alternative is kept only if it is likely to be proposed again
  given the current design, and then with what would reopen it. Everything else that was
  considered lives in git.
- **Numbers.** Each ADR takes the next number and keeps it. ADR numbers are never reused,
  because git history and the evidence files cite them.
- **Provenance lives only in this README.** When ADRs are merged or retired, the table
  below records where each retired number's content went. An ADR's Status carries status
  and date only, and no ADR names the numbers it absorbed.
- **Citations.** Code, docstrings, the terminology and the design documents cite an ADR
  by number and id, `ADR-0017 RS-D5`, never by path or section title, so the directory can
  move and sections can be reordered without breaking a reference.

## Changing an ADR

The architect owns the record. Two tiers of change.

**Direction is locked.** A top-level Direction statement or a section's Direction line
changes only with the architect's approval of that specific change: the exact text, or a
change described precisely enough to apply without further judgment. A new ADR's Direction
statements are approved as a Direction change.

**Details change with the work.** Once the architect has agreed the direction or choice a
detail serves, the detail may be added, adapted, changed, moved or removed to match it. A
detail change that contradicts, narrows or widens its section's Direction is a Direction
change, whatever its size.

A change to an ADR is described per item, and the same description serves a pull request
or a discussion:

- the ADR and id;
- the kind of change: add, adapt, change, move or remove;
- before and after, one line each;
- why, pointing to the decision it follows;
- "Direction affected: no", or "yes" with the reason.

A merge of ADRs re-decides nothing; a merge that changes meaning is a Direction change,
and its retired numbers go into the provenance table below. The pull request lists every
changed item. When a change removes a rejected alternative or changes a Direction, the
commit message names it.

## Provenance

Where the content of a retired number went. Filled in at the cut-over.

| retired | content now in |
|---|---|

**A-ids.** While the lineage decision record exists at `docs/refactor/temp/DECISIONS.md`,
each decided A-item names its destination, and an ADR's Scope names the A-items it absorbed.
Once every item has landed, the record is deleted with `docs/refactor/`. An A-id cited
after that, in an ADR's Scope or in `evidence/`, resolves through git:

```bash
git log -S'A12.5a' --all -- docs/refactor/temp/DECISIONS.md
```
