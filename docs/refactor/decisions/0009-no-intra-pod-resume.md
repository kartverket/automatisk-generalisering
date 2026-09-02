# ADR-0009: No intra-pod resume; the stage is the resume granularity

**Status:** Accepted

## Context

A partition pod runs a stage's operations in listed order against its own workspace. A pod
lost to OOMKill, eviction or node maintenance restarts from the beginning of the stage, losing
however many operations had completed.

## Decision

No intra-pod resume. `--invalidate-from <stage>` remains the only resume mechanism, and the
stage is the granularity.

## Consequences

The blocker is structural, not effort. The stage workspace is pod-local, so resuming from
operation N requires persisting inter-operation handles to run-scratch — approximately 2K
transfers plus a merge per stage, which is exactly the cost stage grouping exists to avoid
([02-runtime §2.3](../02-runtime.md#23-stages)). Building resume would reintroduce, per operation, the overhead that
grouping amortises.

The escape hatch is a declaration change rather than an architecture change: an operator whose
runtime approaches its stage's total re-run cost is promoted to its own stage. Whether that
trade pays is Q-G, measurable once one operator is reimplemented.

Consequently the resilience budget goes into not losing pods rather than into recovering them:
`podFailurePolicy`, `terminationGracePeriodSeconds`, `safe-to-evict: "false"`, and explicit
memory and ephemeral-storage limits.

Recorded so the reason is not re-derived. "Why can't we resume mid-pod" is an obvious question
with a non-obvious answer.
