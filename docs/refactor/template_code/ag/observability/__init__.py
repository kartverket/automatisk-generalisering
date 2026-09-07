"""TEMPLATE — NOT YET WRITTEN. Target package: `src/ag/observability/`.

A horizontal leaf: imports stdlib and `ag.core.types` only, and every package may
import it except `core/`, which stays side-effect free — 03-architecture §4.1.

**Logging is not a port** (ADR-0006). Do not add a `LogPort`.

JSONL records carrying run_id, stage_id, pod_role, partition_index, partition_count,
operation, level, ts, seq — with `seq` a per-process counter, because pod clocks drift
and `ts` alone yields a plausible but wrong interleaving. Two sinks per pod, merged in
`orchestrator/`. Full design: 03-architecture §6.
"""
