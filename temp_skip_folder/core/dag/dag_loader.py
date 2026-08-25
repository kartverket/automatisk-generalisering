"""Load logical data DAG and execution catalog from YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from .dag_model import (
    ArtifactNode,
    DAGValidationError,
    DataflowDAG,
    ExecutionCatalog,
    StageSpec,
)


class DAGLoadError(Exception):
    """Raised when DAG configuration cannot be loaded or parsed."""

    pass


def load_dag(
    config_path: str | Path, catalog_path: str | Path | None = None
) -> DataflowDAG:
    """Load and validate a dataflow DAG and execution catalog.

    Logical DAG file schema:

    artifacts:
      artifact.id:
        dependencies:
          - source.artifact

    Execution catalog file schema:

    stages:
      pipeline:stage_name:
        scale: n100
        pipeline: n100_roads
        module: generalization.n100.road.thin_road
        function: run
        inputs:
          - source.artifact
        outputs:
          - artifact.id

    Args:
        config_path: Path to the logical DAG YAML file.
        catalog_path: Path to execution catalog YAML file. If omitted, defaults
            to a sibling file named ``execution_catalog.yaml``.

    Returns:
        Validated DataflowDAG instance with execution catalog attached.
    """
    config_path = Path(config_path)
    resolved_catalog_path = (
        Path(catalog_path)
        if catalog_path is not None
        else config_path.with_name("execution_catalog.yaml")
    )

    config = _load_yaml(config_path, "logical DAG")
    catalog_config = _load_yaml(resolved_catalog_path, "execution catalog")

    _assert_no_legacy_sections(config, config_path)

    try:
        artifacts = _parse_artifacts(config.get("artifacts"))
        execution_catalog = _parse_execution_catalog(catalog_config)

        dag = DataflowDAG(artifacts=artifacts, execution_catalog=execution_catalog)
        dag.validate_dag()
        dag.validate_with_catalog(execution_catalog)
        return dag
    except DAGValidationError:
        raise
    except Exception as e:
        raise DAGLoadError(f"Failed to load DAG configuration: {e}") from e


def _load_yaml(path: Path, label: str) -> Dict[str, Any]:
    """Load one YAML file and return a dictionary payload."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError as e:
        raise DAGLoadError(f"{label.capitalize()} file not found: {path}") from e
    except yaml.YAMLError as e:
        raise DAGLoadError(f"Failed to parse {label} YAML: {e}") from e

    if config is None:
        return {}
    if not isinstance(config, dict):
        raise DAGLoadError(
            f"{label.capitalize()} root must be a dict, got {type(config)}"
        )

    return config


def _assert_no_legacy_sections(config: Dict[str, Any], config_path: Path) -> None:
    """Hard-cut guard against old scale/pipeline/stage DAG schema."""
    legacy_keys = {"scales", "pipelines", "stages"}
    present = sorted(legacy_keys.intersection(config.keys()))
    if present:
        raise DAGLoadError(
            f"Legacy DAG sections {present} found in {config_path}. "
            "Use the new 'artifacts' schema and a separate execution catalog."
        )


def _parse_artifacts(artifacts_config: Any) -> Dict[str, ArtifactNode]:
    """Parse artifact nodes from logical DAG configuration."""
    if artifacts_config is None:
        raise DAGLoadError("Logical DAG must define top-level 'artifacts' section")
    if not isinstance(artifacts_config, dict):
        raise DAGLoadError(f"'artifacts' must be a dict, got {type(artifacts_config)}")

    artifacts: Dict[str, ArtifactNode] = {}
    for artifact_id, artifact_data in artifacts_config.items():
        if not isinstance(artifact_data, dict):
            raise DAGLoadError(
                f"Artifact '{artifact_id}' configuration must be a dict, got {type(artifact_data)}"
            )

        dependencies = artifact_data.get("dependencies", [])
        if not isinstance(dependencies, list):
            raise DAGLoadError(
                f"Artifact '{artifact_id}' dependencies must be a list, got {type(dependencies)}"
            )

        kind = artifact_data.get("kind", "artifact")
        if not isinstance(kind, str):
            raise DAGLoadError(
                f"Artifact '{artifact_id}' kind must be a string, got {type(kind)}"
            )

        artifacts[artifact_id] = ArtifactNode(
            name=artifact_id,
            dependencies=dependencies,
            kind=kind,
        )

    return artifacts


def _parse_execution_catalog(catalog_config: Dict[str, Any]) -> ExecutionCatalog:
    """Parse execution catalog from YAML configuration."""
    stages_config = catalog_config.get("stages")
    if stages_config is None:
        raise DAGLoadError("Execution catalog must define top-level 'stages' section")
    if not isinstance(stages_config, dict):
        raise DAGLoadError(f"'stages' must be a dict, got {type(stages_config)}")

    stages: Dict[str, StageSpec] = {}
    for stage_name, stage_data in stages_config.items():
        if not isinstance(stage_data, dict):
            raise DAGLoadError(
                f"Stage '{stage_name}' configuration must be a dict, got {type(stage_data)}"
            )

        scale = stage_data.get("scale")
        pipeline = stage_data.get("pipeline")
        module = stage_data.get("module")
        function = stage_data.get("function")
        inputs = stage_data.get("inputs", [])
        outputs = stage_data.get("outputs", [])
        owner = stage_data.get("owner", "")
        runtime = stage_data.get("runtime", {})

        if not isinstance(inputs, list):
            raise DAGLoadError(
                f"Stage '{stage_name}' inputs must be a list, got {type(inputs)}"
            )
        if not isinstance(outputs, list):
            raise DAGLoadError(
                f"Stage '{stage_name}' outputs must be a list, got {type(outputs)}"
            )
        if not isinstance(runtime, dict):
            raise DAGLoadError(
                f"Stage '{stage_name}' runtime must be a dict, got {type(runtime)}"
            )

        stages[stage_name] = StageSpec(
            name=stage_name,
            scale=scale,
            pipeline=pipeline,
            module=module,
            function=function,
            inputs=inputs,
            outputs=outputs,
            owner=owner,
            runtime=runtime,
        )

    return ExecutionCatalog(stages=stages)
