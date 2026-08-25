from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from composition_configs.logic_config import DataRef

from .interface import ArchiveClient
from .local_client import LocalArchiveClient
from .validators import is_gs_path

logger = logging.getLogger(__name__)


class GcsArchiveClient(ArchiveClient):
    def __init__(
        self,
        *,
        local_client: LocalArchiveClient | None = None,
        local_input_path: str = "/tmp/input.gdb",
        local_output_path: str = "/tmp/output.gdb",
    ) -> None:
        from google.cloud import storage

        self._storage_client = storage.Client()
        self._local_client = local_client or LocalArchiveClient(
            local_input_path=local_input_path,
            local_output_path=local_output_path,
        )

    def read(self, remote: DataRef) -> DataRef:
        if not is_gs_path(remote.path):
            return self._local_client.read(remote)

        bucket_name, blob_prefix = _parse_gs_uri(remote.path)

        # Ensure prefix ends with / for folder-like paths
        prefix = blob_prefix if blob_prefix.endswith("/") else blob_prefix + "/"

        logger.info("[GcsArchiveClient] Downloading %s", remote.path)
        bucket = self._storage_client.bucket(bucket_name)
        blobs = self._storage_client.list_blobs(
            bucket_or_name=bucket_name, prefix=prefix
        )

        local_input_path = self._local_client.local_input_path
        local_base = Path(local_input_path)
        local_base.mkdir(parents=True, exist_ok=True)

        has_objects = False
        for blob in blobs:
            # Skip "directory marker" objects
            if blob.name.endswith("/"):
                continue
            has_objects = True

            # Preserve folder structure relative to prefix
            relative_path = blob.name[len(prefix) :]
            local_path = local_base / relative_path
            local_path.parent.mkdir(parents=True, exist_ok=True)

            blob.download_to_filename(str(local_path))
            logger.info(
                "[GcsArchiveClient] Downloaded gs://%s/%s -> %s",
                bucket_name,
                blob.name,
                local_path,
            )

        if not has_objects:
            raise ValueError(f"No objects found at GCS path: {remote.path}")

        return DataRef(path=str(local_base), tag=remote.tag)

    def write(self, local: DataRef, remote: DataRef) -> None:
        if not is_gs_path(remote.path):
            self._local_client.write(local, remote)
            return

        bucket_name, blob_name = _parse_gs_uri(remote.path)
        local_path = Path(local.path)
        upload_path = str(local_path)
        cleanup_zip: str | None = None

        if local_path.is_dir():
            upload_path = shutil.make_archive(
                base_name=str(local_path),
                format="zip",
                root_dir=local_path.parent,
                base_dir=local_path.name,
            )
            cleanup_zip = upload_path

        logger.info("[GcsArchiveClient] Uploading %s -> %s", upload_path, remote.path)
        bucket = self._storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(upload_path)

        if cleanup_zip and os.path.exists(cleanup_zip):
            os.remove(cleanup_zip)

    def list_objects(self, path: str) -> list[str]:
        if not is_gs_path(path):
            return self._local_client.list_objects(path)

        bucket_name, prefix = _parse_gs_uri(path)
        blobs = self._storage_client.list_blobs(
            bucket_or_name=bucket_name, prefix=prefix
        )
        return [
            f"gs://{bucket_name}/{blob.name}"
            for blob in blobs
            if not blob.name.endswith("/")
        ]

    def get_object(self, path: str) -> bytes:
        if not is_gs_path(path):
            return self._local_client.get_object(path)

        bucket_name, blob_name = _parse_gs_uri(path)
        bucket = self._storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.download_as_bytes()

    def put_object(self, path: str, data: bytes) -> None:
        if not is_gs_path(path):
            self._local_client.put_object(path, data)
            return

        bucket_name, blob_name = _parse_gs_uri(path)
        bucket = self._storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(data)

    def delete_object(self, path: str) -> None:
        if not is_gs_path(path):
            self._local_client.delete_object(path)
            return

        bucket_name, blob_name = _parse_gs_uri(path)
        bucket = self._storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.delete()


def _parse_gs_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError(f"Invalid gs path: {uri}")

    without_scheme = uri[len("gs://") :]
    if "/" not in without_scheme:
        return without_scheme, ""
    bucket_name, blob_name = without_scheme.split("/", 1)
    return bucket_name, blob_name
