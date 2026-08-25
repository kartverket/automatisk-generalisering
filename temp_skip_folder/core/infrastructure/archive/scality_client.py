from __future__ import annotations

import io
import logging
import os
import shutil
from pathlib import Path

from composition_configs.logic_config import DataRef

from .interface import ArchiveClient
from .local_client import LocalArchiveClient
from .validators import is_s3_path

logger = logging.getLogger(__name__)


class ScalityArchiveClient(ArchiveClient):
    def __init__(
        self,
        *,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        local_client: LocalArchiveClient | None = None,
        local_input_path: str = "/tmp/input.gdb",
        local_output_path: str = "/tmp/output.gdb",
    ) -> None:
        from minio import Minio

        self._client = Minio(
            endpoint=endpoint_url,
            access_key=access_key,
            secret_key=secret_key,
        )
        self._local_client = local_client or LocalArchiveClient(
            local_input_path=local_input_path,
            local_output_path=local_output_path,
        )

    def read(self, remote: DataRef) -> DataRef:
        if not is_s3_path(remote.path):
            return self._local_client.read(remote)

        bucket_name, object_key = _parse_s3_uri(remote.path)
        if not object_key:
            raise ValueError(f"S3 path must include object key: {remote.path}")

        # Ensure prefix ends with / for folder-like paths
        prefix = object_key if object_key.endswith("/") else object_key + "/"

        # List all objects with this prefix
        objects = self._client.list_objects(
            bucket_name=bucket_name,
            prefix=prefix,
            recursive=True,
        )

        local_input_path = self._local_client.local_input_path
        local_base = Path(local_input_path)
        local_base.mkdir(parents=True, exist_ok=True)

        has_objects = False
        for obj in objects:
            if obj.object_name.endswith("/"):
                continue
            has_objects = True

            # Preserve folder structure
            relative_path = obj.object_name[len(prefix) :]
            local_path = local_base / relative_path
            local_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info("[ScalityArchiveClient] Downloading %s", obj.object_name)
            self._client.fget_object(
                bucket_name=bucket_name,
                object_name=obj.object_name,
                file_path=str(local_path),
            )

        if not has_objects:
            raise ValueError(f"No objects found at S3 path: {remote.path}")

        return DataRef(path=str(local_base), tag=remote.tag)

    def write(self, local: DataRef, remote: DataRef) -> None:
        if not is_s3_path(remote.path):
            self._local_client.write(local, remote)
            return

        bucket_name, object_key = _parse_s3_uri(remote.path)
        if not object_key:
            raise ValueError(f"S3 path must include object key: {remote.path}")

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

        logger.info(
            "[ScalityArchiveClient] Uploading %s -> %s",
            upload_path,
            remote.path,
        )
        self._client.fput_object(
            bucket_name=bucket_name,
            object_name=object_key,
            file_path=upload_path,
            content_type="application/zip" if upload_path.endswith(".zip") else None,
        )

        if cleanup_zip and os.path.exists(cleanup_zip):
            os.remove(cleanup_zip)

    def list_objects(self, path: str) -> list[str]:
        if not is_s3_path(path):
            return self._local_client.list_objects(path)

        bucket_name, prefix = _parse_s3_uri(path)
        return [
            f"s3://{bucket_name}/{obj.object_name}"
            for obj in self._client.list_objects(
                bucket_name=bucket_name, prefix=prefix, recursive=True
            )
            if not obj.object_name.endswith("/")
        ]

    def get_object(self, path: str) -> bytes:
        if not is_s3_path(path):
            return self._local_client.get_object(path)

        bucket_name, object_key = _parse_s3_uri(path)
        response = self._client.get_object(
            bucket_name=bucket_name, object_name=object_key
        )
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def put_object(self, path: str, data: bytes) -> None:
        if not is_s3_path(path):
            self._local_client.put_object(path, data)
            return

        bucket_name, object_key = _parse_s3_uri(path)
        payload = io.BytesIO(data)
        self._client.put_object(
            bucket_name=bucket_name,
            object_name=object_key,
            data=payload,
            length=len(data),
        )

    def delete_object(self, path: str) -> None:
        if not is_s3_path(path):
            self._local_client.delete_object(path)
            return

        bucket_name, object_key = _parse_s3_uri(path)
        self._client.remove_object(bucket_name=bucket_name, object_name=object_key)


def _parse_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Invalid s3 path: {uri}")

    without_scheme = uri[len("s3://") :]
    if "/" not in without_scheme:
        return without_scheme, ""
    bucket_name, object_key = without_scheme.split("/", 1)
    return bucket_name, object_key
