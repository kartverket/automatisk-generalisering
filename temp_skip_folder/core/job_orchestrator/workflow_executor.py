"""
Responsible for reading the dag and orchestrating the execution of stages in the correct order.

Implements async execution with dependency tracking to allow parallel execution of independent stages
while respecting artifact dependencies.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict

from temp_skip_folder.core.dag.dag_loader import load_dag
from temp_skip_folder.core.dag.dag_model import DataflowDAG, ExecutionCatalog, StageSpec


class StageStatus(Enum):
    """Execution status of a stage."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ExecutionResult:
    """Result of executing a single stage."""

    stage_name: str
    status: StageStatus
    start_time: datetime
    end_time: datetime | None = None

    @property
    def duration_seconds(self) -> float:
        """Duration of execution in seconds."""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()


@dataclass
class ExecutionSummary:
    """Summary of entire DAG execution."""

    results: list[ExecutionResult] = field(default_factory=list)
    start_time: datetime | None = None
    end_time: datetime | None = None

    @property
    def total_duration_seconds(self) -> float:
        """Total execution time in seconds."""
        if self.start_time is None or self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()

    def __str__(self) -> str:
        """Human-readable execution summary."""
        lines = ["=" * 60, "Execution Summary", "=" * 60]

        if self.results:
            lines.append(f"Total Duration: {self.total_duration_seconds:.2f}s\n")
            lines.append("Stage Results:")
            lines.append("-" * 60)

            for result in self.results:
                status_str = result.status.value.upper()
                duration_str = f"{result.duration_seconds:.2f}s"
                lines.append(
                    f"  {result.stage_name:<40} {status_str:<12} {duration_str:>10}"
                )

            lines.append("-" * 60)
            completed_count = sum(
                1 for r in self.results if r.status == StageStatus.COMPLETED
            )
            lines.append(f"Completed: {completed_count}/{len(self.results)} stages")
        else:
            lines.append("No stages executed")

        lines.append("=" * 60)
        return "\n".join(lines)


async def execute_stage_async(
    stage_name: str,
    stage_spec: StageSpec,
    artifact_events: Dict[str, asyncio.Event],
) -> ExecutionResult:
    """
    Execute a stage asynchronously, respecting input artifact dependencies.

    Waits for all input artifacts to be produced (signaled via asyncio.Event),
    executes the stage operation (fan out → indexed job → fan in),
    then signals output artifacts.

    Args:
        stage_name: Name of the stage to execute.
        stage_spec: StageSpec defining the stage's inputs/outputs.
        artifact_events: Dict mapping artifact IDs to asyncio.Event objects that
            signal when the artifact is produced.

    Returns:
        ExecutionResult with stage name, status, and timing information.
    """
    from temp_skip_folder.core.job_orchestrator.stage_execution_controller import execute_stage_operation

    start_time = datetime.now()
    result = ExecutionResult(
        stage_name=stage_name,
        status=StageStatus.RUNNING,
        start_time=start_time,
    )

    # Wait for all input artifacts to be available
    if stage_spec.inputs:
        print(f"\n[{stage_name}] waiting for dependencies...")
        await asyncio.gather(
            *[artifact_events[artifact_id].wait() for artifact_id in stage_spec.inputs]
        )

    print(f"\nstarting stage: {stage_name}")

    # Execute the stage operation (fan out → indexed job → fan in)
    await execute_stage_operation(stage_name, stage_spec)

    print(f"\ncompleted stage: {stage_name}\n")

    # Signal that all output artifacts are now available
    for output_artifact in stage_spec.outputs:
        artifact_events[output_artifact].set()

    result.status = StageStatus.COMPLETED
    result.end_time = datetime.now()

    return result


async def orchestrate_dag() -> ExecutionSummary:
    """
    Load and execute a DAG with async stage execution.

    Loads the logical DAG and execution catalog from hard-coded paths in
    temp_skip_folder/core/dag/, then executes all stages concurrently while
    respecting artifact dependencies.

    Returns:
        ExecutionSummary containing results for all executed stages.
    """
    # Hard-coded paths relative to workspace root
    dag_path = Path(__file__).parent.parent / "dag" / "dependencies.yaml"
    catalog_path = Path(__file__).parent.parent / "dag" / "execution_catalog.yaml"

    print(f"\nLoading DAG from: {dag_path}")
    print(f"\nLoading catalog from: {catalog_path}")

    # Load and validate DAG
    dag: DataflowDAG = load_dag(dag_path, catalog_path)
    catalog: ExecutionCatalog = dag.execution_catalog

    print(f"\nLoaded {len(dag.artifacts)} artifacts and {len(catalog.stages)} stages\n")

    # Create asyncio.Event for each artifact to track when it's produced
    artifact_events: Dict[str, asyncio.Event] = {
        artifact_id: asyncio.Event() for artifact_id in dag.artifacts.keys()
    }

    # Create async tasks for all stages
    tasks = []
    for stage_name, stage_spec in catalog.stages.items():
        task = execute_stage_async(stage_name, stage_spec, artifact_events)
        tasks.append(task)

    # Execute all stages concurrently
    print("\nStarting stage execution...\n")
    summary_start = datetime.now()

    results = await asyncio.gather(*tasks)

    summary_end = datetime.now()
    print("\nStage execution complete.\n")

    # Build and return execution summary
    summary = ExecutionSummary(
        results=results,
        start_time=summary_start,
        end_time=summary_end,
    )

    return summary


def main() -> None:
    """Main entry point for DAG orchestrator."""
    summary = asyncio.run(orchestrate_dag())
    print(summary)


if __name__ == "__main__":
    main()