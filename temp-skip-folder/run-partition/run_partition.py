import logging
import os
from dataclasses import dataclass

from composition_configs.logic_config import DataRef
from io_adapters import (
    ReadCallable,
    WriteCallable,
    append_partition_index,
    make_local_fs_read_write,
)
from n100.road.pipeline import n100_roads_pipeline


logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s: %(message)s",
)


logger = logging.getLogger(__name__)


PIPELINE_REGISTRY = {
    "n100_roads": n100_roads_pipeline,
}


@dataclass(frozen=True)
class WorkerContext:
    run_id: str
    pipeline_name: str
    stage_name: str
    partition_index: int
    indexed_input_path: str
    indexed_output_path: str


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _build_context() -> WorkerContext:
    run_id = _required_env("RUN_ID")
    pipeline_name = _required_env("PIPELINE_NAME")
    input_path = _required_env("INPUT_PATH")
    output_path = _required_env("OUTPUT_PATH")
    stage_name = os.getenv("STAGE_NAME", "thin_road")

    raw_partition_index = _required_env("JOB_COMPLETION_INDEX")
    try:
        partition_index = int(raw_partition_index)
    except ValueError as error:
        raise ValueError(
            "JOB_COMPLETION_INDEX must be an integer, "
            f"got: {raw_partition_index}"
        ) from error

    return WorkerContext(
        run_id=run_id,
        pipeline_name=pipeline_name,
        stage_name=stage_name,
        partition_index=partition_index,
        indexed_input_path=append_partition_index(input_path, partition_index),
        indexed_output_path=append_partition_index(output_path, partition_index),
    )


def run_partition_worker(*, read: ReadCallable, write: WriteCallable) -> None:
    context = _build_context()

    pipeline = PIPELINE_REGISTRY.get(context.pipeline_name)
    if pipeline is None:
        valid_pipelines = ", ".join(sorted(PIPELINE_REGISTRY))
        raise ValueError(
            f"Invalid pipeline '{context.pipeline_name}'. "
            f"Valid pipelines: {valid_pipelines}"
        )

    stage = pipeline.get_stage(context.stage_name)
    if stage is None:
        valid_stages = ", ".join(sorted(pipeline.stages))
        raise ValueError(
            f"Invalid stage '{context.stage_name}' for pipeline '{context.pipeline_name}'. "
            f"Valid stages: {valid_stages}"
        )

    logger.info(
        "Starting worker run_id=%s pipeline=%s stage=%s partition_index=%s "
        "input=%s output=%s",
        context.run_id,
        context.pipeline_name,
        context.stage_name,
        context.partition_index,
        context.indexed_input_path,
        context.indexed_output_path,
    )

    stage(
        input=DataRef(path=context.indexed_input_path),
        output=DataRef(path=context.indexed_output_path),
        read=read,
        write=write,
    )

    logger.info(
        "Completed worker run_id=%s pipeline=%s stage=%s partition_index=%s",
        context.run_id,
        context.pipeline_name,
        context.stage_name,
        context.partition_index,
    )