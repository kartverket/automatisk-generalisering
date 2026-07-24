import argparse
import os
import sys
import logging
from typing import Callable, Dict, Tuple
from pathlib import Path
import shutil
from google.cloud import storage

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s: %(message)s",
)


logger = logging.getLogger(__name__)

def upload_results_to_gcs(
    gdb_path: str,
    bucket_name: str,
    gcs_folder: str,
) -> None:
    """

    """
    gdb_path = Path(gdb_path)
    if gcs_folder and not gcs_folder.endswith("/"):
        gcs_folder += "/"


    zip_file = Path(
        shutil.make_archive(
            base_name=str(gdb_path),
            format="zip",
            root_dir=gdb_path.parent,
            base_dir=gdb_path.name
        )
    )


    client = storage.Client()
    bucket = client.bucket(bucket_name)


    
    blob_name = f"{gcs_folder}{zip_file.name}"
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(str(zip_file))
    logger.info(f"Uploaded {zip_file} -> gs://{bucket_name}/{blob_name}")

def download_gcs_folder(
    bucket_name: str,
    gcs_folder: str,
    local_folder: str,
) -> None:
    """
    Download all files from a GCS folder/prefix to a local folder.

    Args:
        bucket_name: Name of the GCS bucket.
        gcs_folder: Folder/prefix inside the bucket, e.g. "data/input/"
        local_folder: Local destination folder, e.g. "/tmp/mydata"
    """

    # Ensure prefix ends with /
    if gcs_folder and not gcs_folder.endswith("/"):
        gcs_folder += "/"

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    blobs = client.list_blobs(bucket_name, prefix=gcs_folder)

    local_base = Path(local_folder)
    local_base.mkdir(parents=True, exist_ok=True)

    for blob in blobs:
        # Skip "directory marker" objects
        if blob.name.endswith("/"):
            continue

        # Preserve folder structure relative to gcs_folder
        relative_path = blob.name[len(gcs_folder):]
        local_path = local_base / relative_path

        local_path.parent.mkdir(parents=True, exist_ok=True)

        blob.download_to_filename(str(local_path))
        print(f"Downloaded gs://{bucket_name}/{blob.name} -> {local_path}")




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
def pipeline_n100_road(args: argparse.Namespace) -> None:
    from generalization.n100.road.data_preparation_2 import run as run_n100_road

    logger.info("Starting pipeline for %s", args)
    run_n100_road()


def pipeline_n10_arealdekke(args: argparse.Namespace) -> None:
    # from generalization.n10.arealdekke.orchestrator.arealdekke_orchestrator import run as run_n10_arealdekke
    logger.info("Starting pipeline for %s", args)
    # run_n10_arealdekke()


DISPATCH: Dict[Tuple[str, str], Callable[[argparse.Namespace], None]] = {
    ("n100", "road"): pipeline_n100_road,
    ("n10", "arealdekke"): pipeline_n10_arealdekke,
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
    args = parse_args()
    check_uid_gid()
    check_read_only()
    download_gcs_folder(
        bucket_name=os.environ.get("GCS_BUCKET"),
        gcs_folder="GIS_Files/",
        local_folder="/tmp/GIS_Files",
    )

    if not args.scale or not args.obj:
        logger.error("Error: --scale and --object required (or set SCALE/OBJECT env)")
        print_available()
        sys.exit()

    key = (args.scale, args.obj)
    handler = DISPATCH.get(key)
    if handler is None:
        logger.error(f"No pipeline for scale={args.scale} object={args.obj}")
        print_available()
        sys.exit()

    handler(args)


if __name__ == "__main__":
    main()
    upload_results_to_gcs(
        gdb_path="/tmp/GIS_Files/ag_outputs/n100/road.gdb/",
        bucket_name=os.environ.get("GCS_BUCKET"),
        gcs_folder="output/",
    )
