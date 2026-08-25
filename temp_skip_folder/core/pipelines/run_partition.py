import logging
import os
from dataclasses import dataclass
import arcpy

from temp_skip_folder.core.infrastructure.archive.factory import create_archive_client
from temp_skip_folder.core.infrastructure.archive.validators import (
    validate_dataref_for_environment,
    validate_environment,
)
from composition_configs.logic_config import DataRef, DataRefTag
from temp_skip_folder.core.pipelines.utilities import (
    append_partition_index,
    make_local_output_path,
)
from temp_skip_folder.core.pipelines.n100.road.pipeline import n100_roads_pipeline
from env_setup import environment_setup

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
    environment: str
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
    environment = _required_env("ENVIRONMENT")
    validate_environment(environment)

    pipeline_name = _required_env("PIPELINE_NAME")
    stage_name = os.getenv("STAGE_NAME", "ramps")

    raw_partition_index = _required_env("JOB_COMPLETION_INDEX")
    try:
        partition_index = int(raw_partition_index)
        partition_index += 1  # Glemte 0 i test data, så vi starter på 1 i stedet for 0. Dette er kun for test.
    except ValueError as error:
        raise ValueError(
            "JOB_COMPLETION_INDEX must be an integer, " f"got: {raw_partition_index}"
        ) from error

    bucket = _required_env("SCALITY_BUCKET")
    if environment == "on_cloud":
        bucket = f"gs://{bucket}"
    elif environment == "on_prem":
        bucket = f"s3://{bucket}"

    input_path = f"{bucket}/partition_data/{partition_index}/test_partition_{partition_index}.gdb"
    output_path = (
        f"{bucket}/partition_data/{partition_index}/output_{partition_index}.gdb"
    )

    return WorkerContext(
        run_id=run_id,
        environment=environment,
        pipeline_name=pipeline_name,
        stage_name=stage_name,
        partition_index=partition_index,
        indexed_input_path=input_path,
        indexed_output_path=output_path,
    )


def _build_local_ouput_gdb(context: WorkerContext) -> str:
    """ """
    local_output_path = make_local_output_path(context.indexed_output_path)
    arcpy.management.CreateFileGDB(
        out_folder_path=os.path.dirname(local_output_path),
        out_name=os.path.basename(local_output_path),
    )


def _tag_for_environment(environment: str) -> DataRefTag:
    if environment == "on_cloud":
        return DataRefTag.CLOUD_OK
    return DataRefTag.PREM_ONLY


def run_partition_worker() -> None:
    context = _build_context()
    archive_client = create_archive_client(context.environment)
    _build_local_ouput_gdb(context)

    input_ref = DataRef(
        path=context.indexed_input_path,
        tag=_tag_for_environment(context.environment),
    )
    output_ref = DataRef(
        path=context.indexed_output_path,
        tag=_tag_for_environment(context.environment),
    )

    validate_dataref_for_environment(input_ref, context.environment)
    validate_dataref_for_environment(output_ref, context.environment)

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
        "Starting worker run_id=%s environment=%s pipeline=%s stage=%s partition_index=%s "
        "input=%s output=%s",
        context.run_id,
        context.environment,
        context.pipeline_name,
        context.stage_name,
        context.partition_index,
        context.indexed_input_path,
        context.indexed_output_path,
    )

    stage(
        input=input_ref,
        output=output_ref,
        read=archive_client.read,
        write=archive_client.write,
    )

    logger.info(
        "Completed worker run_id=%s pipeline=%s stage=%s partition_index=%s",
        context.run_id,
        context.pipeline_name,
        context.stage_name,
        context.partition_index,
    )


def main() -> None:
    environment_setup.main()
    run_partition_worker()


if __name__ == "__main__":
    main()
