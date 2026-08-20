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
from typing import Dict, List

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
        node_id.replace(":", "__")
        .replace("-", "_")
        .replace(".", "_")
        .replace("/", "_")
    )


def _build_section(title: str, nodes: Dict[str, List[str]]) -> List[str]:
    """Build one Mermaid section for a node category."""
    lines: List[str] = [f"## {title}", "", "```mermaid", "flowchart LR"]

    # Declare all nodes first so isolated nodes are still rendered.
    for node in sorted(nodes):
        sid = _sanitize(node)
        lines.append(f'  {sid}["{node}"]')

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


def build_mermaid_markdown(config_path: Path) -> str:
    """Load DAG config and produce markdown with Mermaid diagrams."""
    dag = load_dag(config_path)

    scales = {name: node.dependencies for name, node in dag.scales.items()}
    pipelines = {name: node.dependencies for name, node in dag.pipelines.items()}
    stages = {name: node.dependencies for name, node in dag.stages.items()}

    lines: List[str] = [
        "# Pipeline DAG",
        "",
        f"Source: core/dag/dependencies.yaml",
        "",
    ]
    lines.extend(_build_section("Scales", scales))
    lines.extend(_build_section("Pipelines", pipelines))
    lines.extend(_build_section("Stages", stages))

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    script_dir = Path(__file__).resolve().parent
    default_config = script_dir / "dependencies.yaml"
    default_output = script_dir / "dependencies_diagram.md"

    parser = argparse.ArgumentParser(description="Generate Mermaid diagrams from DAG YAML.")
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
