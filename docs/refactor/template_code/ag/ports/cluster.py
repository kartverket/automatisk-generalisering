"""TEMPLATE — not shipped. Target module: `src/ag/ports/cluster.py`.

Kubernetes job lifecycle. 4-5 methods.

DRIVEN, NOT DRIVING, WHICH IS EASY TO GET BACKWARDS. Kubernetes is the system's one
driving actor - it starts the pods - but that direction enters through
`runtime/`'s entry points, which are primary adapters. THIS port is the orchestrator
reaching OUT to the cluster API to create and watch jobs, and the arrow points the
same way as every other port here (03-architecture §4.5).

TWO CLUSTERS, ONE CONTRACT. On-prem and cloud differ in reachability, which is what
placement decides; they do not differ in job lifecycle. The second implementation is
therefore a configuration of the same adapter rather than a second adapter, and the
port earns its place on the arcpy-replaceability test instead: a change of execution
substrate must cost an adapter, not a rewrite.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from ag.core.types import Environment, RunId, StageName


class JobState(Enum):
    """Terminal states are FAILED and SUCCEEDED. Everything else is in flight."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

    @property
    def terminal(self) -> bool:
        return self in (JobState.SUCCEEDED, JobState.FAILED)


@dataclass(frozen=True)
class JobSpec:
    """What the orchestrator asks for. Not a Kubernetes manifest.

    THE FIELDS 03-architecture §8.2 CALLS OUT ARE HERE AS VALUES, because they are the
    highest-value resilience settings in the system and each is a number rather than a
    mechanism:

      `grace_period_s` must be long enough to upload the scratch dump on SIGTERM.
      `memory_limit_gib` and `ephemeral_storage_gib` are explicit because OOMKill and
      ephemeral-storage eviction are the two failures that are NEW at K partitions,
      and both are caused by uneven partitions.

    `podFailurePolicy`, `restartPolicy: Never` and the safe-to-evict annotation are
    NOT here: they are the same for every job this system creates, so they belong in
    the adapter that renders the manifest, not in a spec every caller must restate.
    """

    run_id: RunId
    stage: StageName
    environment: Environment
    image: str
    command: tuple[str, ...]
    parallelism: int = 1
    memory_limit_gib: float = 8.0
    ephemeral_storage_gib: float = 64.0
    grace_period_s: int = 300
    labels: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class JobStatus:
    name: str
    state: JobState
    active: int = 0
    succeeded: int = 0
    failed: int = 0


class ClusterClient(Protocol):
    """Job lifecycle. The orchestrator's only view of the cluster."""

    def submit(self, *, spec: JobSpec) -> str:
        """Create the job; return its name."""
        ...

    def status(self, *, name: str) -> JobStatus: ...

    def watch(self, *, name: str) -> Iterator[JobStatus]:
        """Status changes until a terminal state. An iterator rather than a callback
        so the orchestrator's control flow stays readable and a caller can stop."""
        ...

    def logs(self, *, name: str, pod_index: int) -> Iterator[str]:
        """stdout for one pod. GROUND TRUTH, per 03-architecture §6: the cluster
        collector receives it even if the pod dies, which the local JSONL an
        OOM-killed pod never uploaded does not."""
        ...

    def delete(self, *, name: str) -> None: ...
