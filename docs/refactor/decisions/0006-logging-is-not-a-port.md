# ADR-0006: Logging is not a port

**Status:** Accepted

## Context

Every pod tier emits diagnostics, and with no workflow-engine UI the run record is the only
view of a run. The port test is a distinct external capability plus a foreseeable second
implementation.

## Decision

No `LogPort`. `observability/` is an ordinary package importing stdlib `logging` and
`core.types` only. Archived logs are transported by the existing `ArchiveClient`.

## Consequences

Logging fails the port test on every clause: stdlib, no vendor to adapt, no second
implementation foreseeable. Adding a port would be ceremony around `logging`.

`observability/` is a horizontal leaf: every package may import it except `core/`, which
stays side-effect free.

Context fields travel in a `ContextVar` injected by a logging filter rather than as a
parameter. This is the one place ambient passing is accepted, because the context carries no
capability — see ADR-0008.

Because there is no port, the JSONL record schema is the contract instead, and changing it
breaks the merge in `orchestrator/`.
