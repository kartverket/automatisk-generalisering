"""Generate Mermaid diagrams from the DAG YAML configuration.

Usage:
    python temp_skip_folder/core/dag/dag_to_mermaid.py

Optional arguments:
    --config /path/to/dependencies.yaml
    --output /path/to/dependencies_diagram.md
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

try:
    from temp_skip_folder.core.dag import load_dag
except ModuleNotFoundError:
    # Support direct execution: python temp_skip_folder/core/dag/dag_to_mermaid.py
    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root))
    from temp_skip_folder.core.dag import load_dag

logger = logging.getLogger(__name__)


def _sanitize(node_id: str) -> str:
    """Convert node IDs to Mermaid-safe identifiers."""
    return (
        node_id.replace(":", "__").replace("-", "_").replace(".", "_").replace("/", "_")
    )


def _build_section(
    title: str,
    nodes: Dict[str, List[str]],
    producers: Dict[str, str] | None = None,
) -> List[str]:
    """Build one Mermaid section for artifact dependencies."""
    lines: List[str] = [f"## {title}", "", "```mermaid", "flowchart LR"]

    # Declare all nodes first so isolated nodes are still rendered.
    for node in sorted(nodes):
        sid = _sanitize(node)
        producer_suffix = ""
        if producers and node in producers:
            producer_suffix = f"<br/>producer: {producers[node]}"
        lines.append(f'  {sid}["{node}{producer_suffix}"]')

    edge_count = 0
    for node in sorted(nodes):
        node_sid = _sanitize(node)
        for dep in sorted(nodes[node]):
            dep_sid = _sanitize(dep)
            # Dependency direction: dependency -> dependent node.
            lines.append(f"  {dep_sid} --> {node_sid}")
            edge_count += 1

    if edge_count == 0:
        lines.append("  empty([No dependencies])")

    lines.extend(["```", ""])
    return lines


def _build_hierarchy_edges(
    artifacts: Dict[str, List[str]],
    producers: Dict[str, str],
    stage_to_pipeline: Dict[str, str],
    stage_to_scale: Dict[str, str],
) -> Tuple[Set[Tuple[str, str]], Set[Tuple[str, str]], Set[Tuple[str, str]]]:
    """Build dependency edges collapsed to stage, pipeline, and scale levels."""
    stage_edges: Set[Tuple[str, str]] = set()
    pipeline_edges: Set[Tuple[str, str]] = set()
    scale_edges: Set[Tuple[str, str]] = set()

    for artifact, dependencies in artifacts.items():
        consumer_stage = producers.get(artifact)
        if consumer_stage is None:
            continue

        for dependency in dependencies:
            producer_stage = producers.get(dependency)
            if producer_stage is None:
                continue

            if producer_stage != consumer_stage:
                stage_edges.add((producer_stage, consumer_stage))

            producer_pipeline = stage_to_pipeline.get(producer_stage)
            consumer_pipeline = stage_to_pipeline.get(consumer_stage)
            if (
                producer_pipeline
                and consumer_pipeline
                and producer_pipeline != consumer_pipeline
            ):
                pipeline_edges.add((producer_pipeline, consumer_pipeline))

            producer_scale = stage_to_scale.get(producer_stage)
            consumer_scale = stage_to_scale.get(consumer_stage)
            if producer_scale and consumer_scale and producer_scale != consumer_scale:
                scale_edges.add((producer_scale, consumer_scale))

    return stage_edges, pipeline_edges, scale_edges


def _build_hierarchy_section(
    title: str,
    stage_names: Set[str],
    pipeline_names: Set[str],
    scale_names: Set[str],
    stage_edges: Set[Tuple[str, str]],
    pipeline_edges: Set[Tuple[str, str]],
    scale_edges: Set[Tuple[str, str]],
) -> List[str]:
    """Build one Mermaid section for dependency edges at hierarchy levels."""
    lines: List[str] = [f"## {title}", "", "```mermaid", "flowchart TB"]

    lines.append('  subgraph scales["Scale Dependencies"]')
    for scale_name in sorted(scale_names):
        sid = _sanitize(f"scale:{scale_name}")
        lines.append(f'    {sid}["{scale_name}"]')
    for src, dst in sorted(scale_edges):
        src_id = _sanitize(f"scale:{src}")
        dst_id = _sanitize(f"scale:{dst}")
        lines.append(f"    {src_id} --> {dst_id}")
    lines.append("  end")

    lines.append('  subgraph pipelines["Pipeline Dependencies"]')
    for pipeline_name in sorted(pipeline_names):
        pid = _sanitize(f"pipeline:{pipeline_name}")
        lines.append(f'    {pid}["{pipeline_name}"]')
    for src, dst in sorted(pipeline_edges):
        src_id = _sanitize(f"pipeline:{src}")
        dst_id = _sanitize(f"pipeline:{dst}")
        lines.append(f"    {src_id} --> {dst_id}")
    lines.append("  end")

    lines.append('  subgraph stages["Stage Dependencies"]')
    for stage_name in sorted(stage_names):
        stage_id = _sanitize(f"stage:{stage_name}")
        lines.append(f'    {stage_id}["{stage_name}"]')
    for src, dst in sorted(stage_edges):
        src_id = _sanitize(f"stage:{src}")
        dst_id = _sanitize(f"stage:{dst}")
        lines.append(f"    {src_id} --> {dst_id}")
    lines.append("  end")

    lines.extend(["```", ""])
    return lines


def build_mermaid_markdown(config_path: Path) -> str:
    """Load DAG config and produce markdown with Mermaid diagrams."""
    dag = load_dag(config_path)

    artifacts = {name: node.dependencies for name, node in dag.artifacts.items()}
    producers: Dict[str, str] = {}

    stage_names: Set[str] = set()
    pipeline_names: Set[str] = set()
    scale_names: Set[str] = set()
    stage_edges: Set[Tuple[str, str]] = set()
    pipeline_edges: Set[Tuple[str, str]] = set()
    scale_edges: Set[Tuple[str, str]] = set()

    if dag.execution_catalog is not None:
        producers = dag.execution_catalog.producers_by_artifact()
        stage_names = set(dag.execution_catalog.stages.keys())
        stage_to_pipeline = {
            stage_name: spec.pipeline
            for stage_name, spec in dag.execution_catalog.stages.items()
        }
        stage_to_scale = {
            stage_name: spec.scale
            for stage_name, spec in dag.execution_catalog.stages.items()
        }
        pipeline_names = set(stage_to_pipeline.values())
        scale_names = set(stage_to_scale.values())
        stage_edges, pipeline_edges, scale_edges = _build_hierarchy_edges(
            artifacts=artifacts,
            producers=producers,
            stage_to_pipeline=stage_to_pipeline,
            stage_to_scale=stage_to_scale,
        )

    lines: List[str] = [
        "# Dataflow DAG",
        "",
        "Source: core/dag/dependencies.yaml",
        "Execution catalog: core/dag/execution_catalog.yaml",
        "",
    ]
    lines.extend(
        _build_section("Artifacts (Filenames Only)", artifacts, producers=None)
    )
    lines.extend(
        _build_hierarchy_section(
            title="Hierarchy Dependencies",
            stage_names=stage_names,
            pipeline_names=pipeline_names,
            scale_names=scale_names,
            stage_edges=stage_edges,
            pipeline_edges=pipeline_edges,
            scale_edges=scale_edges,
        )
    )

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    script_dir = Path(__file__).resolve().parent
    default_config = script_dir / "dependencies.yaml"
    default_output = script_dir / "dependencies_diagram.md"

    parser = argparse.ArgumentParser(
        description="Generate Mermaid diagrams from DAG YAML."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=default_config,
        help=f"Path to DAG YAML config (default: {default_config}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"Path to output markdown file (default: {default_output}).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser.parse_args()


def main() -> int:
    """Script entrypoint."""
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    config_path = args.config.resolve()
    output_path = args.output.resolve()

    markdown = build_mermaid_markdown(config_path)
    output_path.write_text(markdown, encoding="utf-8")

    logger.info("Wrote Mermaid diagram to %s", output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
