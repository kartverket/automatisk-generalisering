"""
Factory for creating stage functions that abstract common I/O and path handling boilerplate.

This factory reduces repetitive code across stages by handling:
- Calling read() and write() functions
- Constructing local DataRef paths for input and output
- Managing temporary local paths
"""

import logging
from typing import Callable, Any
from composition_configs.logic_config import DataRef
from utilities import make_local_output_path

logger = logging.getLogger(__name__)


def make_stage(
    process_fn: Callable,
) -> Callable:
    """
    Factory function that creates a stage function from a process function.

    Handles the boilerplate of:
    - Reading input data via the read() callback
    - Constructing local DataRef paths with configured subdirectories
    - Writing output data via the write() callback

    Args:
        process_fn: A callable that accepts named parameters:
            - input_root: DataRef pointing to the local input root directory
            - output_root: DataRef pointing to the local output root directory
            - **kwargs: Any additional parameters

            The process_fn is responsible for constructing both input and output paths
            from these roots. This allows:
            - Single input stage: construct one input_fc from input_root
            - Multi-input stage: construct multiple input_fc (e.g., roads, buildings)
            - Single output stage: construct one output_fc from output_root
            - Multi-output stage: construct multiple output_fc (e.g., output, output_points)


    Returns:
        A stage function with the standard signature:
        stage(*, input: DataRef, output: DataRef, read: Callable, write: Callable) -> None

    Example:
        # Single input, single output stage
        def process_thin_road(input_root, output_root):
            input_fc = DataRef(
                path=f"{input_root.path}/input",
                tag=input_root.tag
            )
            output_fc = DataRef(
                path=f"{output_root.path}/output",
                tag=output_root.tag
            )
            thin_road_network(input=input_fc, output=output_fc)

        thin_road_stage = make_stage(process_thin_road)

        # Multi-output stage
        def process_ramps(input_root, output_root):
            input_fc = DataRef(
                path=f"{input_root.path}/input",
                tag=input_root.tag
            )
            output_fc = DataRef(
                path=f"{output_root.path}/output",
                tag=output_root.tag
            )
            output_points_fc = DataRef(
                path=f"{output_root.path}/output_points",
                tag=output_root.tag
            )
            ramps(
                input=input_fc,
                output_line=output_fc,
                output_point=output_points_fc,
            )

        ramps_stage = make_stage(process_ramps)

        # Multi-input, single output stage
        def process_conflict_resolution(input_root, output_root):
            input_roads = DataRef(
                path=f"{input_root.path}/roads",
                tag=input_root.tag
            )
            input_buildings = DataRef(
                path=f"{input_root.path}/buildings",
                tag=input_root.tag
            )
            output_fc = DataRef(
                path=f"{output_root.path}/buildings_resolved",
                tag=output_root.tag
            )
            resolve_building_conflicts(
                roads=input_roads,
                buildings=input_buildings,
                output=output_fc
            )

        conflict_resolution_stage = make_stage(process_conflict_resolution)
    """

    def stage(
        *,
        input: DataRef,
        output: DataRef,
        read: Callable[[DataRef], DataRef],
        write: Callable[[DataRef, DataRef], None],
    ) -> None:
        # Read input data to local filesystem
        local_input_root = read(input)

        # Construct local output root path
        local_output_root = DataRef(
            path=make_local_output_path(output.path),
            tag=output.tag,
        )

        # Call the process function
        # The process_fn is responsible for constructing all input_fc and output_fc
        # from the roots (e.g., /input, /output, /output_points, /roads, /buildings)
        process_fn(input_root=local_input_root, output_root=local_output_root)

        # Write output data back to remote storage
        write(local_output_root, output)

    return stage
