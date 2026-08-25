"""Models for a dataflow-first DAG and execution catalog.

The logical DAG is defined strictly in terms of artifacts and their dependencies.
Execution concerns (which stage can produce which artifacts, ownership, runtime
settings) live in a separate execution catalog.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set


class DAGValidationError(Exception):
    """Raised when DAG validation fails."""
    pass


@dataclass(frozen=True)
class DAGNode:
    """Base class for dataflow nodes."""
    name: str
    dependencies: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate that dependencies is a list."""
        if not isinstance(self.dependencies, list):
            raise ValueError(f"dependencies must be a list, got {type(self.dependencies)}")


@dataclass(frozen=True)
class ArtifactNode(DAGNode):
    """Node representing an artifact in the logical dataflow DAG."""
    kind: str = field(default="artifact")


@dataclass(frozen=True)
class StageSpec:
    """Execution metadata for a stage that can produce artifacts."""

    name: str
    scale: str
    pipeline: str
    module: str
    function: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    owner: str = field(default="")
    runtime: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate shape of stage metadata."""
        if not self.scale:
            raise ValueError(f"Stage '{self.name}' scale must not be empty")
        if not self.pipeline:
            raise ValueError(f"Stage '{self.name}' pipeline must not be empty")
        if not self.module:
            raise ValueError(f"Stage '{self.name}' module must not be empty")
        if not self.function:
            raise ValueError(f"Stage '{self.name}' function must not be empty")
        if not isinstance(self.inputs, list):
            raise ValueError(f"Stage '{self.name}' inputs must be a list")
        if not isinstance(self.outputs, list):
            raise ValueError(f"Stage '{self.name}' outputs must be a list")
        if not self.outputs:
            raise ValueError(f"Stage '{self.name}' must declare at least one output")
        if not isinstance(self.runtime, dict):
            raise ValueError(f"Stage '{self.name}' runtime must be a dict")


@dataclass
class ExecutionCatalog:
    """Execution metadata index keyed by stage name."""

    stages: Dict[str, StageSpec] = field(default_factory=dict)

    def producers_by_artifact(self) -> Dict[str, str]:
        """Return artifact -> producing stage mapping."""
        result: Dict[str, str] = {}
        for stage_name, stage in self.stages.items():
            for output in stage.outputs:
                result[output] = stage_name
        return result


@dataclass
class DataflowDAG:
    """Logical artifact dependency graph and optional execution catalog."""

    artifacts: Dict[str, ArtifactNode] = field(default_factory=dict)
    execution_catalog: ExecutionCatalog | None = field(default=None)

    def validate_dag(self) -> None:
        """Validate the logical artifact DAG."""
        self._validate_references()
        self._validate_no_cycles()

    def _validate_references(self) -> None:
        """Validate that every artifact dependency points to an existing artifact."""
        for artifact_id, node in self.artifacts.items():
            for dep in node.dependencies:
                if dep not in self.artifacts:
                    raise DAGValidationError(
                        f"Artifact '{artifact_id}' depends on missing artifact '{dep}'."
                    )

    def _validate_no_cycles(self) -> None:
        """Check for cycles in the artifact graph."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def has_cycle_dfs(node_name: str) -> bool:
            """DFS to detect cycles."""
            visited.add(node_name)
            rec_stack.add(node_name)

            dependencies = self.get_dependencies(node_name)
            for dep in dependencies:
                if dep not in visited:
                    if has_cycle_dfs(dep):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(node_name)
            return False

        for artifact_id in self.artifacts:
            if artifact_id not in visited and has_cycle_dfs(artifact_id):
                raise DAGValidationError(
                    f"Cycle detected in artifact dependencies at '{artifact_id}'."
                )

    def validate_with_catalog(self, catalog: ExecutionCatalog) -> None:
        """Validate logical DAG against execution catalog declarations."""
        produced_artifacts: Dict[str, str] = {}

        for stage_name, stage in catalog.stages.items():
            for artifact in stage.inputs:
                if artifact not in self.artifacts:
                    raise DAGValidationError(
                        f"Stage '{stage_name}' input '{artifact}' does not exist in logical DAG."
                    )

            for artifact in stage.outputs:
                if artifact not in self.artifacts:
                    raise DAGValidationError(
                        f"Stage '{stage_name}' output '{artifact}' does not exist in logical DAG."
                    )
                if artifact in produced_artifacts:
                    raise DAGValidationError(
                        f"Artifact '{artifact}' has multiple producers: "
                        f"'{produced_artifacts[artifact]}' and '{stage_name}'."
                    )
                produced_artifacts[artifact] = stage_name

                logical_dependencies = set(self.artifacts[artifact].dependencies)
                stage_inputs = set(stage.inputs)
                if not logical_dependencies.issubset(stage_inputs):
                    raise DAGValidationError(
                        f"Stage '{stage_name}' output '{artifact}' is missing required logical "
                        f"inputs: {sorted(logical_dependencies - stage_inputs)}"
                    )

    def get_dependencies(self, artifact_id: str) -> List[str]:
        """Get direct dependencies for one artifact."""
        if artifact_id not in self.artifacts:
            raise ValueError(f"Artifact '{artifact_id}' not found.")
        return self.artifacts[artifact_id].dependencies

    def get_transitive_dependencies(self, artifact_id: str) -> List[str]:
        """Get all transitive dependencies for an artifact."""
        all_deps: Set[str] = set()
        visited: Set[str] = set()

        def collect_deps(current_artifact: str) -> None:
            if current_artifact in visited:
                return
            visited.add(current_artifact)

            deps = self.get_dependencies(current_artifact)
            for dep in deps:
                all_deps.add(dep)
                collect_deps(dep)

        collect_deps(artifact_id)
        return sorted(list(all_deps))

    def get_producer(self, artifact_id: str) -> str | None:
        """Return stage name that produces artifact, if catalog is attached."""
        if artifact_id not in self.artifacts:
            raise ValueError(f"Artifact '{artifact_id}' not found.")
        if self.execution_catalog is None:
            return None

        for stage_name, stage in self.execution_catalog.stages.items():
            if artifact_id in stage.outputs:
                return stage_name
        return None


# Backward-compatible alias while moving to a dataflow-first naming model.
PipelineDAG = DataflowDAG
