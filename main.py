import argparse
import os
import sys
import logging
from typing import Callable, Dict, Tuple
from pathlib import Path
import shutil
from google.cloud import storage
from minio import Minio

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s: %(message)s",
)


logger = logging.getLogger(__name__)




def create_s3_client(
    endpoint_url: str,
    access_key: str,
    secret_key: str,
) -> Minio:
    """
    Create an S3-compatible client for Scality.
    """
    return Minio(
                endpoint=endpoint_url,
                access_key=access_key,
                secret_key=secret_key
            )


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
        relative_path = obj.object_name[len(scality_folder):]
        local_path = local_base / relative_path

        local_path.parent.mkdir(parents=True, exist_ok=True)

        client.fget_object(
            bucket_name=bucket_name,
            object_name=obj.object_name,
            file_path=str(local_path),
        )

        print(f"Downloaded s3://{bucket_name}/{obj.object_name} -> {local_path}")



def upload_results_to_scality(
    client: Minio,
    bucket_name: str,
    local_path: str,
    object_name: str | None = None
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
        base_dir=local_path.name
    )

    print(f"Uploading {local_zip_path} -> s3://{bucket_name}/{object_name}")

    client.fput_object(
        bucket_name=bucket_name,
        object_name=object_name,
        file_path=local_zip_path,
        content_type="application/zip"
    )

    print("ZIP upload completed.")




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


def gcs_main():
    """
    temp main function to for GCS solution
    """
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

    upload_results_to_gcs(
        gdb_path="/tmp/GIS_Files/ag_outputs/n100/road.gdb/",
        bucket_name=os.environ.get("GCS_BUCKET"),
        gcs_folder=f"outputs/{args.scale}_{args.obj}/",

    )


def on_prem_main():
    """
    Temp function to test on prem solution
    """
    endpoint_url = os.environ.get("SCALITY_ENDPOINT")
    access_key = os.environ.get("scality_user")
    secret_key = os.environ.get("scality_pass")
    bucket_name = os.environ.get("SCALITY_BUCKET")

    args = parse_args()
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

    download_scality_folder(
        client=s3,
        bucket_name=bucket_name,
        scality_folder="GIS_Files/",
        local_folder="/tmp/GIS_Files"
    )


    

    key = (args.scale, args.obj)
    handler = DISPATCH.get(key)
    if handler is None:
        logger.error(f"No pipeline for scale={args.scale} object={args.obj}")
        print_available()
        sys.exit()

    handler(args)

    upload_results_to_scality(
        client=s3,
        bucket_name=bucket_name,
        local_path=Path("/tmp/GIS_Files/ag_outputs/n100/road.gdb/"),
        object_name=f"outputs/{args.scale}_{args.obj}/road.gdb.zip",
    )



def main():
    on_prem = os.environ.get("ON_PREM")
    if on_prem == "False":
        print("Running in GCS mode")
        gcs_main()
    else:
        print("Running in on-prem mode")
        on_prem_main()


if __name__ == "__main__":
    main()
    
