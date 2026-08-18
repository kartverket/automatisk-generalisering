"""
Thin road network stage - simplifies road networks by removing insignificant segments.
"""

import logging
from composition_configs.logic_config import DataRef
from stage_factory import make_stage
from n100.road.function_calls import thin_road_network

logger = logging.getLogger(__name__)


def process_thin_road(input_root: DataRef, output_root: DataRef) -> None:
    """
    Process function for thinning road networks.
    
    Constructs input and output paths from the roots and calls the thin road network processing function.
    """
    input_fc = DataRef(
        path=f"{input_root.path}/input",
        tag=input_root.tag,
    )
    output_fc = DataRef(
        path=f"{output_root.path}/output",
        tag=output_root.tag,
    )
    
    thin_road_network(
        input=input_fc,
        output=output_fc,
    )


thin_road_stage = make_stage(process_thin_road)
