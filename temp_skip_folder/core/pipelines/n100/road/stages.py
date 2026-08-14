import os
import logging
from collections.abc import Callable

from composition_configs.logic_config import DataRef
from n100.road.function_calls import thin_road_network, ramps
from utilities import make_local_output_path



logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s: %(message)s",
)


logger = logging.getLogger(__name__)

def thin_road_stage(
    *,
    input: DataRef,
    output: DataRef,
    read: Callable[[DataRef], DataRef],
    write: Callable[[DataRef, DataRef], None],
) -> None:
    """
    Thin road stage
    """
    logger.info("Starting thin road stage")
    local_input = read(input)
    local_input_fc = DataRef(
        path=f"{local_input.path}/input",
        tag=local_input.tag,
    )
    local_output = DataRef(
        path=make_local_output_path(output.path),
        tag=output.tag,
    )
    local_output_fc = DataRef(
        path=f"{local_output.path}/output",
        tag=local_output.tag,
    )

    thin_road_network(
        input=local_input_fc,
        output=local_output_fc,
    )

    write(local_output, output)

    logger.info("Thin road stage completed")

def ramps_stage(
    *,
    input: DataRef,
    output: DataRef,
    read: Callable[[DataRef], DataRef],
    write: Callable[[DataRef, DataRef], None],
) -> None:
    """
    Ramps stage
    """
    logger.info("Starting ramps stage")
    local_input = read(input)
    local_input_fc = DataRef(
        path=f"{local_input.path}/input",
        tag=local_input.tag,
    )
    local_output = DataRef(
        path=make_local_output_path(output.path),
        tag=output.tag,
    )
    local_output_fc = DataRef(
        path=f"{local_output.path}/output",
        tag=local_output.tag,
    )
    local_output_fc_points = DataRef(
        path=f"{local_output.path}/output_points",
        tag=local_output.tag,
    )

    ramps(
        input=local_input_fc,
        output_line=local_output_fc,
        output_point=local_output_fc_points,
    )
    

    write(local_output, output)

    logger.info("Ramps stage completed")
