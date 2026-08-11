import os
import logging
from collections.abc import Callable

from composition_configs.logic_config import DataRef
from n100.road.function_calls import thin_road_network
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
    local_output = DataRef(path=make_local_output_path(output.path))

    thin_road_network(
        input=local_input,
        output=local_output,
    )

    write(local_output, output)

    logger.info("Thin road stage completed")
