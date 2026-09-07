# ADR-0008: `Toolbox` passed explicitly, not ambient

**Status:** Accepted

**Closes:** Q-E

## Context

Operations and helpers need three or four ports. Injecting each individually is noise at 100+
call sites; a module-level singleton set at pod startup would remove the parameter entirely.

## Decision

A frozen `Toolbox` bundling `geometry`, `table`, `cartographic` and `graph`, assembled once by
the pod entry point and passed as a single explicit parameter to every operation and helper
that needs a port.

## Consequences

The precedent decides it: [02-runtime §2.4](../02-runtime.md#24-operations) already passes `ScratchScope` as an explicit
parameter into operations and derives it downward into helpers. Two dependency-passing styles
in one signature is worse than either used consistently.

Dependencies stay visible in the signature, and tests stay stateless — a fake `Toolbox` is
constructed and passed, with no global to set or reset.

One parameter rather than four, so the noise argument against explicit injection mostly
disappears.

The exception is observability context (ADR-0006), which travels in a `ContextVar`. It
carries no capability — nothing can be called through it — so it does not create the second
style this decision exists to avoid.

Revisit if the parameter proves worse in practice than predicted once real operations exist.
