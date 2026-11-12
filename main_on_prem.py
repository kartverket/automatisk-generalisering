import argparse
import functools
import io
import json
import os
import random
import sys
import logging
import time
import traceback
from datetime import datetime, timezone
from typing import Callable, Dict, ParamSpec, Tuple, TypeVar
from pathlib import Path
import shutil
import tempfile
import zipfile
import urllib3
from minio import Minio
from minio.error import S3Error, ServerError
from generalization.n100.road.pipeline_checkpoint import ScalityPipelineCheckpoint

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s: %(message)s",
)


logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

OPERATION_RETRY_ATTEMPTS = 6
OPERATION_RETRY_TOTAL_DELAY_S = 600
OPERATION_RETRY_DELAY_S = OPERATION_RETRY_TOTAL_DELAY_S / OPERATION_RETRY_ATTEMPTS
COMPLETED_OUTPUT_CUTOFF = datetime(2026, 11, 10, tzinfo=timezone.utc)


def is_transient_error(error: BaseException) -> bool:
    """True for errors worth retrying: network failures and 5xx responses."""
    if isinstance(error, S3Error):
        return error.response.status >= 500
    if isinstance(error, ServerError):
        return error.status_code >= 500
    return isinstance(
        error,
        (
            urllib3.exceptions.HTTPError,
            ConnectionError,
            TimeoutError,
        ),
    )


def retry_on_transient_error(func: Callable[P, R]) -> Callable[P, R]:
    """Retry the whole operation, sleeping a fixed delay between attempts."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        for attempt in range(1, OPERATION_RETRY_ATTEMPTS + 1):
            try:
                return func(*args, **kwargs)
            except Exception as error:
                if not is_transient_error(error) or attempt == OPERATION_RETRY_ATTEMPTS:
                    raise
                logger.warning(
                    "%s failed (attempt %d/%d): %s. Retrying in %.1fs",
                    func.__name__,
                    attempt,
                    OPERATION_RETRY_ATTEMPTS,
                    error,
                    OPERATION_RETRY_DELAY_S,
                )
                time.sleep(OPERATION_RETRY_DELAY_S)
        raise AssertionError("unreachable")

    return wrapper


@retry_on_transient_error
def download_file(
    client: Minio, bucket_name: str, object_name: str, file_path: Path
) -> None:
    """Download an object, retrying the whole download on transient errors."""
    client.fget_object(
        bucket_name=bucket_name,
        object_name=object_name,
        file_path=str(file_path),
    )


@retry_on_transient_error
def upload_file(
    client: Minio, bucket_name: str, object_name: str, file_path: str
) -> None:
    """Upload a local zip file, retrying the whole upload on transient errors."""
    client.fput_object(
        bucket_name=bucket_name,
        object_name=object_name,
        file_path=file_path,
        content_type="application/zip",
    )


@retry_on_transient_error
def get_object_last_modified(
    client: Minio, bucket_name: str, object_name: str
) -> datetime:
    """Return an object's last-modified timestamp, retrying transient errors."""
    return client.stat_object(
        bucket_name=bucket_name,
        object_name=object_name,
    ).last_modified


class RetryingScalityPipelineCheckpoint(ScalityPipelineCheckpoint):
    """Scality checkpoint whose save, load and delete retry on transient errors."""

    @retry_on_transient_error
    def save(self, step_name: str) -> None:
        super().save(step_name)

    @retry_on_transient_error
    def load(self) -> str | None:
        return super().load()

    @retry_on_transient_error
    def delete(self) -> None:
        super().delete()


def create_s3_client(
    endpoint_url: str,
    access_key: str,
    secret_key: str,
) -> Minio:
    """
    Create an S3-compatible client for Scality.
    """
    return Minio(endpoint=endpoint_url, access_key=access_key, secret_key=secret_key)


def download_scality_folder(
    client: Minio,
    bucket_name: str,
    scality_folder: str,
    local_folder: str,
) -> None:
    """
    Download all files from a Scality/S3 folder/prefix to a local folder.

    Args:
        bucket_name: Name of the Scality bucket.
        scality_folder: Folder/prefix inside the bucket, e.g. "data/input/"
        local_folder: Local destination folder, e.g. "/tmp/mydata"
    """

    # Ensure prefix ends with /
    if scality_folder and not scality_folder.endswith("/"):
        scality_folder += "/"

    objects = client.list_objects(
        bucket_name=bucket_name,
        prefix=scality_folder,
        recursive=True,
    )

    local_base = Path(local_folder)
    local_base.mkdir(parents=True, exist_ok=True)

    for obj in objects:
        # Skip "directory marker" objects
        if obj.object_name.endswith("/"):
            continue

        # Preserve folder structure relative to scality_folder
        relative_path = obj.object_name[len(scality_folder) :]
        local_path = local_base / relative_path

        local_path.parent.mkdir(parents=True, exist_ok=True)

        """client.fget_object(
            bucket_name=bucket_name,
            object_name=obj.object_name,
            file_path=str(local_path),
        )"""
        download_file(client, bucket_name, obj.object_name, local_path)

        logger.info(f"Downloaded s3://{bucket_name}/{obj.object_name} -> {local_path}")


def upload_results_to_scality(
    client: Minio, bucket_name: str, local_path: str, object_name: str | None = None
):
    """
    Upload a local ZIP file to a Scality bucket.

    Args:
        client: MinIO client instance.
        bucket_name: Name of the Scality bucket.
        local_zip_path: Path to local .zip file.
        object_name: Destination object name in the bucket.
                     If None, the local filename is used.

    Example:
        upload_zip_to_scality(
            client,
            bucket_name="my-bucket",
            local_zip_path="/tmp/archive.zip",
            object_name="backups/archive.zip"
        )
    """

    local_zip_path = shutil.make_archive(
        base_name=str(local_path),
        format="zip",
        root_dir=local_path.parent,
        base_dir=local_path.name,
    )

    logger.info(f"Uploading {local_zip_path} -> s3://{bucket_name}/{object_name}")

    """
    client.fput_object(
        bucket_name=bucket_name,
        object_name=object_name,
        file_path=local_zip_path,
        content_type="application/zip",
    )"""
    upload_file(client, bucket_name, object_name, local_zip_path)

    logger.info("ZIP upload completed.")


def upload_error_to_scality(
    client: Minio,
    bucket_name: str,
    error: BaseException,
    job_completion_index: str,
    prefix: str = "indexed_error_log",
) -> None:
    """
    Upload the full error (message and traceback) as a JSON file to Scality.

    Retried pods share the same completion index, so the pod name (HOSTNAME)
    is part of the object name to keep every attempt's log.
    Never raises: a failed upload must not mask the original pipeline error.
    """
    object_name = f"{prefix.strip('/')}/{job_completion_index}.json"
    payload = {
        "job_completion_index": job_completion_index,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        ),
    }
    data = json.dumps(payload, indent=2).encode("utf-8")

    try:
        client.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            data=io.BytesIO(data),
            length=len(data),
            content_type="application/json",
        )

        logger.info("Uploaded error file to s3://%s/%s", bucket_name, object_name)
    except Exception:
        logger.exception("Failed to upload error file to Scality")


def check_uid_gid():
    current_uid = os.getuid()
    current_gid = os.getgid()
    logger.info("current uid: %s current gid: %s", current_uid, current_gid)


def check_read_only():
    tmp_file = "/tmp/file.txt"
    with open(tmp_file, "w", encoding="utf-8") as f:
        f.write("written to and read from /tmp")

    with open(tmp_file, "r", encoding="utf-8") as f:
        content = f.read()

    logger.info(content)
    os.remove(tmp_file)

    root_file = "file.txt"
    try:
        with open(root_file, "w", encoding="utf-8") as f:
            f.write("written to and read from root")

        with open(root_file, "r", encoding="utf-8") as f:
            content2 = f.read()
        logger.info(content2)
        os.remove(root_file)
    except Exception as e:
        logger.info("Failed to write to root: ")
        logger.info(e)


# pipeline imports
def pipeline_n100_road(
    args: argparse.Namespace, checkpoint: ScalityPipelineCheckpoint | None = None
) -> None:
    from generalization.n100.road.data_preparation_2 import run as run_n100_road

    logger.info("Starting pipeline for %s", args)
    run_n100_road(checkpoint=checkpoint)


def pipeline_n10_arealdekke(args: argparse.Namespace) -> None:
    # from generalization.n10.arealdekke.orchestrator.arealdekke_orchestrator import run as run_n10_arealdekke
    logger.info("Starting pipeline for %s", args)
    # run_n10_arealdekke()


def pipeline_n100_buildings(
    args: argparse.Namespace, checkpoint: ScalityPipelineCheckpoint | None = None
) -> None:
    from generalization.n100.building.building_main import main as run_n100_buildings

    logger.info("Starting pipeline for %s", args)
    run_n100_buildings(checkpoint=checkpoint)


DISPATCH: Dict[Tuple[str, str], Callable[[argparse.Namespace], None]] = {
    ("n100", "road"): pipeline_n100_road,
    ("n10", "arealdekke"): pipeline_n10_arealdekke,
    ("n100", "building"): pipeline_n100_buildings,
}


def print_available() -> None:
    logger.info("Available pipelines:")
    for scale, obj in DISPATCH.keys():
        logger.info(f"  - scale={scale} object={obj}")


def parse_args():
    parser = argparse.ArgumentParser(description="Dispatch to pipelines")
    parser.add_argument(
        "--scale", type=str, default=os.getenv("SCALE"), help="Scale to run (env SCALE)"
    )
    parser.add_argument(
        "--object",
        dest="obj",
        type=str,
        default=os.getenv("OBJECT"),
        help="Object to process (env OBJECT)",
    )
    return parser.parse_args()


def main():
    """
    Temp function to test on prem solution
    """
    endpoint_url = os.environ.get("SCALITY_ENDPOINT")
    access_key = os.environ.get("scality_user")
    secret_key = os.environ.get("scality_pass")
    bucket_name = os.environ.get("SCALITY_BUCKET")

    args = parse_args()
    job_completion_index = None
    if os.environ.get("JOB_COMPLETION_INDEX"):
        job_completion_index = os.environ.get("JOB_COMPLETION_INDEX")
        os.environ["PARTITION_INDEX"] = job_completion_index

    check_uid_gid()
    check_read_only()
    if not args.scale or not args.obj:
        logger.error("Error: --scale and --object required (or set SCALE/OBJECT env)")
        print_available()
        sys.exit()

    s3 = create_s3_client(
        endpoint_url=endpoint_url,
        access_key=access_key,
        secret_key=secret_key,
    )

    if job_completion_index:
        object_name = (
            f"outputs/{args.scale}_{args.obj}/output_{job_completion_index}.gdb.zip"
        )
        try:
            last_modified = get_object_last_modified(
                client=s3,
                bucket_name=bucket_name,
                object_name=object_name,
            )
        except S3Error as error:
            logger.info("S3 error when looking up last modified of output: %s", error)
        else:
            if last_modified >= COMPLETED_OUTPUT_CUTOFF:
                logger.info(
                    "Skipping completion index %s: s3://%s/%s was last modified at %s",
                    job_completion_index,
                    bucket_name,
                    object_name,
                    last_modified,
                )
                return

    download_scality_folder(
        client=s3,
        bucket_name=bucket_name,
        scality_folder="GIS_Files/",
        local_folder="/tmp/GIS_Files",
    )

    key = (args.scale, args.obj)
    handler = DISPATCH.get(key)
    if handler is None:
        logger.error(f"No pipeline for scale={args.scale} object={args.obj}")
        print_available()
        sys.exit()

    if job_completion_index:
        namespace = f"{args.scale}_{args.obj}_{job_completion_index}"
    else:
        namespace = f"{args.scale}_{args.obj}"
    checkpoint = RetryingScalityPipelineCheckpoint(
        client=s3,
        bucket_name=bucket_name,
        gdb_path=Path(f"/tmp/GIS_Files/ag_outputs/{args.scale}/{args.obj}.gdb"),
        namespace=namespace,
    )
    try:
        handler(args, checkpoint=checkpoint)
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        if job_completion_index:
            upload_error_to_scality(
                client=s3,
                bucket_name=bucket_name,
                error=e,
                job_completion_index=job_completion_index,
            )
        sys.exit(1)

    if job_completion_index:
        object_name = (
            f"outputs/{args.scale}_{args.obj}/output_{job_completion_index}.gdb.zip"
        )
    else:
        object_name = f"outputs/{args.scale}_{args.obj}/output.gdb.zip"
    upload_results_to_scality(
        client=s3,
        bucket_name=bucket_name,
        local_path=Path(f"/tmp/GIS_Files/ag_outputs/{args.scale}/{args.obj}.gdb/"),
        object_name=object_name,
    )
    if args.scale == "n100" and args.obj == "building":
        upload_results_to_scality(
            client=s3,
            bucket_name=bucket_name,
            local_path=Path("/tmp/GIS_Files/ag_outputs/n100/final_outputs.gdb/"),
            object_name=f"outputs/{args.scale}_{args.obj}/final_outputs.gdb.zip",
        )


if __name__ == "__main__":
    main()
