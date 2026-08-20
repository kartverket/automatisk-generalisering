"""
DAG model for defining and validating dependencies across scales, pipelines, and stages.

A DAG (Directed Acyclic Graph) is used to represent hierarchical dependencies:
- Scales can only depend on other scales
- Pipelines can only depend on other pipelines
- Stages can only depend on other stages (referenced as "pipeline:stage")

Example:
    >>> dag = PipelineDAG(
    ...     scales={"n100": ScaleNode("n100", ["n50"]), "n50": ScaleNode("n50", [])},
    ...     pipelines={...},
    ...     stages={...}
    ... )
    >>> dag.validate_dag()  # Raises ValidationError if invalid
    >>> dag.get_dependencies("scale", "n100")
    ["n50"]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set


class DAGValidationError(Exception):
    """Raised when DAG validation fails."""
    pass


@dataclass(frozen=True)
class DAGNode:
    """
    Base class for all DAG nodes.
    
    Attributes:
        name: Unique identifier for the node.
        dependencies: List of node names this node depends on.
    """
    name: str
    dependencies: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate that dependencies is a list."""
        if not isinstance(self.dependencies, list):
            raise ValueError(f"dependencies must be a list, got {type(self.dependencies)}")


@dataclass(frozen=True)
class ScaleNode(DAGNode):
    """Node representing a scale (e.g., n100, n50, n250)."""
    pass


@dataclass(frozen=True)
class PipelineNode(DAGNode):
    """Node representing a pipeline (e.g., n100_roads, n100_buildings)."""
    pass


@dataclass(frozen=True)
class StageNode(DAGNode):
    """
    Node representing a stage within a pipeline.
    
    Stages are referenced as "pipeline:stage" to avoid naming conflicts.
    Dependencies can reference other stages in the same or different pipelines.
    """
    pipeline: str = field(default="")  # The pipeline this stage belongs to

    def __post_init__(self) -> None:
        """Validate that dependencies is a list."""
        super().__post_init__()
        if not self.pipeline:
            raise ValueError("pipeline must not be empty for StageNode")

    def full_name(self) -> str:
        """Return the fully qualified name 'pipeline:stage'."""
        return f"{self.pipeline}:{self.name}"


@dataclass
class PipelineDAG:
    """
    Container for all DAG nodes representing the system's dependency structure.
    
    Attributes:
        scales: Dict mapping scale names to ScaleNode instances.
        pipelines: Dict mapping pipeline names to PipelineNode instances.
        stages: Dict mapping "pipeline:stage" to StageNode instances.
    """
    scales: Dict[str, ScaleNode] = field(default_factory=dict)
    pipelines: Dict[str, PipelineNode] = field(default_factory=dict)
    stages: Dict[str, StageNode] = field(default_factory=dict)

    def validate_dag(self) -> None:
        """
        Validate the entire DAG structure.
        
        Checks:
        1. All scale dependencies reference only scales.
        2. All pipeline dependencies reference only pipelines.
        3. All stage dependencies reference only stages.
        4. All referenced nodes exist.
        5. No cycles exist in the graph.
        
        Raises:
            DAGValidationError: If any validation check fails.
        """
        self._validate_node_types()
        self._validate_references()
        self._validate_no_cycles()

    def _validate_node_types(self) -> None:
        """Validate that each node type only depends on the same type."""
        for name, scale_node in self.scales.items():
            for dep in scale_node.dependencies:
                if dep not in self.scales:
                    raise DAGValidationError(
                        f"Scale '{name}' depends on '{dep}', which is not a scale."
                    )

        for name, pipeline_node in self.pipelines.items():
            for dep in pipeline_node.dependencies:
                if dep not in self.pipelines:
                    raise DAGValidationError(
                        f"Pipeline '{name}' depends on '{dep}', which is not a pipeline."
                    )

        for full_name, stage_node in self.stages.items():
            for dep in stage_node.dependencies:
                if dep not in self.stages:
                    raise DAGValidationError(
                        f"Stage '{full_name}' depends on '{dep}', which is not a stage."
                    )

    def _validate_references(self) -> None:
        """Validate that all referenced nodes exist."""
        # Already checked in _validate_node_types, but kept for clarity
        pass

    def _validate_no_cycles(self) -> None:
        """Check for cycles in all dependency graphs."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def has_cycle_dfs(node_type: str, node_name: str) -> bool:
            """DFS to detect cycles."""
            visited.add(f"{node_type}:{node_name}")
            rec_stack.add(f"{node_type}:{node_name}")

            dependencies = self.get_dependencies(node_type, node_name)
            for dep in dependencies:
                dep_id = f"{node_type}:{dep}"
                if dep_id not in visited:
                    if has_cycle_dfs(node_type, dep):
                        return True
                elif dep_id in rec_stack:
                    return True

            rec_stack.remove(f"{node_type}:{node_name}")
            return False

        for scale_name in self.scales:
            if f"scale:{scale_name}" not in visited:
                if has_cycle_dfs("scale", scale_name):
                    raise DAGValidationError(f"Cycle detected in scale dependencies at '{scale_name}'")

        visited.clear()
        rec_stack.clear()

        for pipeline_name in self.pipelines:
            if f"pipeline:{pipeline_name}" not in visited:
                if has_cycle_dfs("pipeline", pipeline_name):
                    raise DAGValidationError(
                        f"Cycle detected in pipeline dependencies at '{pipeline_name}'"
                    )

        visited.clear()
        rec_stack.clear()

        for stage_full_name in self.stages:
            if f"stage:{stage_full_name}" not in visited:
                if has_cycle_dfs("stage", stage_full_name):
                    raise DAGValidationError(
                        f"Cycle detected in stage dependencies at '{stage_full_name}'"
                    )

    def get_dependencies(self, node_type: str, node_name: str) -> List[str]:
        """
        Get direct dependencies of a node.
        
        Args:
            node_type: One of "scale", "pipeline", or "stage".
            node_name: The name of the node. For stages, use "pipeline:stage" format.
            
        Returns:
            List of dependency names.
            
        Raises:
            ValueError: If node_type is invalid or node not found.
        """
        if node_type == "scale":
            if node_name not in self.scales:
                raise ValueError(f"Scale '{node_name}' not found.")
            return self.scales[node_name].dependencies
        elif node_type == "pipeline":
            if node_name not in self.pipelines:
                raise ValueError(f"Pipeline '{node_name}' not found.")
            return self.pipelines[node_name].dependencies
        elif node_type == "stage":
            if node_name not in self.stages:
                raise ValueError(f"Stage '{node_name}' not found.")
            return self.stages[node_name].dependencies
        else:
            raise ValueError(f"Invalid node_type: {node_type}. Must be 'scale', 'pipeline', or 'stage'.")

    def get_transitive_dependencies(self, node_type: str, node_name: str) -> List[str]:
        """
        Get all transitive dependencies of a node (full dependency tree).
        
        Args:
            node_type: One of "scale", "pipeline", or "stage".
            node_name: The name of the node. For stages, use "pipeline:stage" format.
            
        Returns:
            Sorted list of all dependencies (direct and transitive).
            
        Raises:
            ValueError: If node_type is invalid or node not found.
        """
        all_deps: Set[str] = set()
        visited: Set[str] = set()

        def collect_deps(nt: str, nn: str) -> None:
            if f"{nt}:{nn}" in visited:
                return
            visited.add(f"{nt}:{nn}")

            deps = self.get_dependencies(nt, nn)
            for dep in deps:
                all_deps.add(dep)
                collect_deps(nt, dep)

        collect_deps(node_type, node_name)
        return sorted(list(all_deps))
