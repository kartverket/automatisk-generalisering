"""
Loader for DAG configuration from YAML files.

Handles parsing, validation, and instantiation of the PipelineDAG from a YAML config file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from .dag_model import DAGValidationError, PipelineDAG, PipelineNode, ScaleNode, StageNode


class DAGLoadError(Exception):
    """Raised when DAG configuration cannot be loaded or parsed."""
    pass


def load_dag(config_path: str | Path) -> PipelineDAG:
    """
    Load and validate a DAG from a YAML configuration file.
    
    The YAML file should have the following structure:
    
    scales:
      n100:
        dependencies:
          - n50
      n50:
        dependencies: []
    
    pipelines:
      n100_roads:
        dependencies: []
      n100_buildings:
        dependencies:
          - n100_roads
    
    stages:
      n100_roads:
        thin_road:
          dependencies:
            - n100_roads:ramps
        ramps:
          dependencies: []
    
    Args:
        config_path: Path to the YAML configuration file.
        
    Returns:
        Validated PipelineDAG instance.
        
    Raises:
        DAGLoadError: If the configuration file cannot be read or parsed.
        DAGValidationError: If the DAG structure is invalid.
    """
    config_path = Path(config_path)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError as e:
        raise DAGLoadError(f"Configuration file not found: {config_path}") from e
    except yaml.YAMLError as e:
        raise DAGLoadError(f"Failed to parse YAML configuration: {e}") from e

    if config is None:
        config = {}

    try:
        scales = _parse_scales(config.get("scales", {}))
        pipelines = _parse_pipelines(config.get("pipelines", {}))
        stages = _parse_stages(config.get("stages", {}))

        dag = PipelineDAG(scales=scales, pipelines=pipelines, stages=stages)
        dag.validate_dag()

        return dag
    except DAGValidationError:
        raise
    except Exception as e:
        raise DAGLoadError(f"Failed to load DAG configuration: {e}") from e


def _parse_scales(scales_config: Dict[str, Any]) -> Dict[str, ScaleNode]:
    """Parse scale nodes from configuration."""
    scales: Dict[str, ScaleNode] = {}

    if not isinstance(scales_config, dict):
        raise DAGLoadError(f"'scales' must be a dict, got {type(scales_config)}")

    for scale_name, scale_data in scales_config.items():
        if not isinstance(scale_data, dict):
            raise DAGLoadError(f"Scale '{scale_name}' configuration must be a dict, got {type(scale_data)}")

        dependencies = scale_data.get("dependencies", [])
        if not isinstance(dependencies, list):
            raise DAGLoadError(
                f"Scale '{scale_name}' dependencies must be a list, got {type(dependencies)}"
            )

        scales[scale_name] = ScaleNode(name=scale_name, dependencies=dependencies)

    return scales


def _parse_pipelines(pipelines_config: Dict[str, Any]) -> Dict[str, PipelineNode]:
    """Parse pipeline nodes from configuration."""
    pipelines: Dict[str, PipelineNode] = {}

    if not isinstance(pipelines_config, dict):
        raise DAGLoadError(f"'pipelines' must be a dict, got {type(pipelines_config)}")

    for pipeline_name, pipeline_data in pipelines_config.items():
        if not isinstance(pipeline_data, dict):
            raise DAGLoadError(
                f"Pipeline '{pipeline_name}' configuration must be a dict, got {type(pipeline_data)}"
            )

        dependencies = pipeline_data.get("dependencies", [])
        if not isinstance(dependencies, list):
            raise DAGLoadError(
                f"Pipeline '{pipeline_name}' dependencies must be a list, got {type(dependencies)}"
            )

        pipelines[pipeline_name] = PipelineNode(name=pipeline_name, dependencies=dependencies)

    return pipelines


def _parse_stages(stages_config: Dict[str, Any]) -> Dict[str, StageNode]:
    """Parse stage nodes from configuration."""
    stages: Dict[str, StageNode] = {}

    if not isinstance(stages_config, dict):
        raise DAGLoadError(f"'stages' must be a dict, got {type(stages_config)}")

    for pipeline_name, pipeline_stages in stages_config.items():
        if not isinstance(pipeline_stages, dict):
            raise DAGLoadError(
                f"Stages for pipeline '{pipeline_name}' must be a dict, got {type(pipeline_stages)}"
            )

        for stage_name, stage_data in pipeline_stages.items():
            if not isinstance(stage_data, dict):
                raise DAGLoadError(
                    f"Stage '{pipeline_name}:{stage_name}' configuration must be a dict, "
                    f"got {type(stage_data)}"
                )

            dependencies = stage_data.get("dependencies", [])
            if not isinstance(dependencies, list):
                raise DAGLoadError(
                    f"Stage '{pipeline_name}:{stage_name}' dependencies must be a list, "
                    f"got {type(dependencies)}"
                )

            full_name = f"{pipeline_name}:{stage_name}"
            stages[full_name] = StageNode(
                name=stage_name, pipeline=pipeline_name, dependencies=dependencies
            )

    return stages
