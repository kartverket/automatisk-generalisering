# Architecture decision records

The ADRs in this directory are the source of truth for the architecture and the design
direction of `src/ag`. They exist so that separate pull requests build towards the same
design. Work does not contradict a Direction statement; a change that would is a Direction
change.

## Index

Reading order, not numeric order.

| ADR | prefix | theme | governs |
|---|---|---|---|
| [ADR-0018](0018-architecture.md) | AR | Architecture: the boundary, the ports and the packages | `ports/` as a package, `adapters/`, `generalization/helpers/`, `observability/`, the composition roots, `.importlinter`, the conformance matrix |
| [ADR-0019](0019-port-contract.md) | PC | Port contract: what crosses a port | handles at the boundary, `predicates.py`, `attributes.py`, `geometry.py`, row IO on `TableOps` |
| [ADR-0017](0017-row-shape-grammar.md) | RS | Row shape, the declared grammar of port outputs | `row_shape.py`, `columns.py`, every port Protocol, the checks in `tests/static/` |
| [ADR-0020](0020-operations.md) | OP | Operations: declaration, injection and tuning | `core/operations.py`, `core/handles.py`, `core/injection.py`, `ports/toolbox.py`, configs and tuning |
| [ADR-0021](0021-stages.md) | ST | Stages: identities, inputs and execution | `core/pipeline.py`, `sources.py`, `products.py`, `locations.py`, fan-out, fan-in, resume |

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

Where the content of a retired number went.

| retired | content now in |
|---|---|
| 0001 | ADR-0019 Direction 2, PC-2, PC-D5 to PC-D9, PC-R1, PC-R2 |
| 0002 | ADR-0018 Direction 3, AR-D2, AR-D5, AR-D8, AR-D10, AR-D13 |
| 0003 | ADR-0019 Direction 1, PC-1, PC-D1 to PC-D3 |
| 0004 | ADR-0019 Direction 4, PC-4, PC-D22, PC-D24, PC-D25, PC-R4 |
| 0005 | ADR-0018 AR-D20 to AR-D22, AR-R8 |
| 0006 | ADR-0018 Direction 5, AR-4, AR-D17 to AR-D19, AR-R7 |
| 0007 | ADR-0018 Direction 4, AR-3, AR-D14 to AR-D16, AR-R6 |
| 0008 | ADR-0020 Direction 4, OP-3, OP-D19 to OP-D23, OP-R5 |
| 0009 | ADR-0021 Direction 4, ST-3, ST-D23, ST-D24, ST-R6 |
| 0010 | ADR-0018 Direction 1, AR-1, AR-D1 to AR-D4, AR-R1, AR-R2, AR-R5 |
| 0011 | ADR-0020 Direction 1 and 2, OP-1, OP-D1 to OP-D9, OP-R1 |
| 0012 | ADR-0021 Direction 1, ST-1, ST-D1 to ST-D10, ST-R1, ST-R2 |
| 0013 | ADR-0020 Direction 5, OP-4, OP-D24 to OP-D34, OP-R6 |
| 0014 | ADR-0020 Direction 3, OP-2, OP-D10 to OP-D18, OP-R2, OP-R4 |
| 0015 | ADR-0019 Direction 3, PC-3, PC-D10 to PC-D21, PC-R3 |
| 0016 | ADR-0021 Direction 2 and 3, ST-2, ST-D11 to ST-D22, ST-R3, ST-R5 |

**A-ids.** While the lineage decision record exists at `docs/refactor/temp/DECISIONS.md`,
each decided A-item names its destination, and an ADR's Scope names the A-items it absorbed.
Once every item has landed, the record is deleted with `docs/refactor/`. An A-id cited
after that, in an ADR's Scope or in `evidence/`, resolves through git:

```bash
git log -S'A12.5a' --all -- docs/refactor/temp/DECISIONS.md
```

## Sources

Cited by the ADRs; kept here so the citations are checkable.

- Cockburn, *Hexagonal Architecture*: https://alistair.cockburn.us/hexagonal-architecture
- Percival and Gregory, *Architecture Patterns with Python* (O'Reilly)
- PEP 544, *Protocols: Structural subtyping*: https://peps.python.org/pep-0544/
- OGC *Common Query Language (CQL2)*: https://docs.ogc.org/is/21-065r2/21-065r2.html
- import-linter: https://import-linter.readthedocs.io/en/stable/
