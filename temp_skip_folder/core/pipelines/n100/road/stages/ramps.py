"""
Road ramps stage - identifies and processes road ramps (on/off ramps).

Produces dual outputs:
- output_line: The ramp line features
- output_points: Points marking ramp locations
"""

import logging
from composition_configs.logic_config import DataRef
from stage_factory import make_stage
from n100.road.function_calls import ramps

logger = logging.getLogger(__name__)


def process_ramps(input_root: DataRef, output_root: DataRef) -> None:
    input_fc = DataRef(
        path=f"{input_root.path}/input",
        tag=input_root.tag,
    )
    output_fc = DataRef(
        path=f"{output_root.path}/output",
        tag=output_root.tag,
    )
    output_points_fc = DataRef(
        path=f"{output_root.path}/output_points",
        tag=output_root.tag,
    )

    ramps(
        input=input_fc,
        output_line=output_fc,
        output_point=output_points_fc,
    )


ramps_stage = make_stage(process_ramps)
