# ADR-0005: `helpers/` as the package name

**Status:** Accepted

**Closes:** Q-A

## Context

Reusable, object-agnostic, scale-agnostic functions that compose port calls need a package.
They are called only from inside operations, never named in a stage, never scheduled. This is
most of what `custom_tools/general_tools/` is today.

## Decision

`helpers/`, organised on a subject axis: `lines.py`, `polygons.py`, `points.py`,
`topology.py`, `attributes.py`, `extents.py`.

## Consequences

The junk-drawer objection is real — `general_tools/` became one — but is neutralised by two
things already decided: membership is a mechanical test (no `OperationCall` factory), and the
subject axis is declared rather than emergent. `geometry_tools.py` reached 2327 lines because
"general tools" had no axis.

If it turns out wrong, the rename is one `git mv` plus one line in `.importlinter`.

Rejected alternatives:

- `tools/`, `toolkit/` — "tool" is retired; it collides with port methods and arcpy tools.
- `composites/` — collides with composite and multipart geometry, which is everyday
  vocabulary in a GIS codebase.
- `subroutines/` — accurate about "never invoked independently", but dated.
- `techniques/` — fuzzy boundary against `operations/`.
- `operations/shared/` — reserved for operations shared between objects, which
  [02-runtime §6.1](../02-runtime.md#61-a-run-is-a-selection) requires.
