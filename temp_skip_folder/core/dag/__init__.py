"""
DAG module for managing and validating pipeline dependencies.

This module provides classes and functions for:
- Defining dependencies across scales, pipelines, and stages
- Loading DAG configuration from YAML files
- Validating DAG structure (no cycles, correct types, reference existence)
- Querying dependencies programmatically

Example:
    >>> from temp_skip_folder.core.dag import load_dag
    >>> dag = load_dag("temp_skip_folder/core/dag/dependencies.yaml")
    >>> dag.get_dependencies("scale", "n100")
    ['n50']
    >>> dag.get_dependencies("stage", "n100_roads:thin_road")
    ['n100_roads:ramps']
"""

from .dag_loader import DAGLoadError, load_dag
from .dag_model import DAGNode, DAGValidationError, PipelineDAG, PipelineNode, ScaleNode, StageNode

__all__ = [
    "DAGNode",
    "ScaleNode",
    "PipelineNode",
    "StageNode",
    "PipelineDAG",
    "DAGValidationError",
    "DAGLoadError",
    "load_dag",
]
