# ADR-0003: ScratchHandle, not DataObject, at the port boundary

**Status:** Accepted

## Context

Two IO vocabularies exist. `DataObject` (`Source` / `Derived`) is what a stage declares: it
carries identity, lineage, legality and a remote location, and the dependency graph,
classification and pinning are all computed over it. `ScratchHandle` is what an operation
receives: a named slot in the pod scratch root, with no identity and no location.

Port signatures must name one of them.

## Decision

Every port method takes `ScratchHandle`. `DataObject` never appears in `ports/`.

## Consequences

Adapters stay ignorant of the planning layer. A `DataObject` parameter would drag identity,
classification and pinning into every adapter, and an adapter would need the registry to
resolve a location.

The rule that an operation sees no URI, no client, no partition index and no context radius
extends unchanged to adapters.

An adapter cannot make a decision based on where data came from. That is intended:
classification is computed at plan time, and an adapter that could see a location could
branch on it.

`ports/` may import `core.handles` and `core.types`, but not `core.pipeline`.
