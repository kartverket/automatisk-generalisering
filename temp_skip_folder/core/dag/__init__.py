"""DAG module for logical artifact dependencies and execution catalog metadata.

The module splits dependency concerns into:
- Logical DAG: artifact dependency graph.
- Execution catalog: stage metadata with inputs and outputs.
"""

from .dag_loader import DAGLoadError, load_dag
from .dag_model import (
    ArtifactNode,
    DAGNode,
    DAGValidationError,
    DataflowDAG,
    ExecutionCatalog,
    PipelineDAG,
    StageSpec,
)

__all__ = [
    "DAGNode",
    "ArtifactNode",
    "StageSpec",
    "ExecutionCatalog",
    "DataflowDAG",
    "PipelineDAG",
    "DAGValidationError",
    "DAGLoadError",
    "load_dag",
]
