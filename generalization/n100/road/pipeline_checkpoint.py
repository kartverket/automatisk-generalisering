import io
import logging
import shutil
import tempfile
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)

_LOG_OBJECT = "checkpoints/n100_road/log.txt"
_STATE_OBJECT = "checkpoints/n100_road/state.gdb.zip"


def _zip_gdb(gdb_path: Path) -> Path:
    tmp_dir = Path(tempfile.mkdtemp())
    zip_base = tmp_dir / gdb_path.name
    zip_path = Path(
        shutil.make_archive(
            base_name=str(zip_base),
            format="zip",
            root_dir=gdb_path.parent,
            base_dir=gdb_path.name,
        )
    )
    return zip_path


def _unzip_gdb(zip_path: Path, target_parent: Path) -> None:
    gdb_name = zip_path.stem  # e.g. "road.gdb"
    existing = target_parent / gdb_name
    if existing.exists():
        shutil.rmtree(existing)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(target_parent)


class PipelineCheckpoint(ABC):
    @abstractmethod
    def save(self, step_name: str) -> None:
        """Upload log.txt (step name) and zipped GDB to the bucket."""

    @abstractmethod
    def load(self) -> str | None:
        """
        Download and restore GDB from bucket if a checkpoint exists.
        Returns the last completed step name, or None for a clean start.
        """

    @abstractmethod
    def delete(self) -> None:
        """Remove log.txt and state.gdb.zip from the bucket."""


class GCSPipelineCheckpoint(PipelineCheckpoint):
    def __init__(self, bucket_name: str, gdb_path: Path) -> None:
        self._bucket_name = bucket_name
        self._gdb_path = gdb_path

    def _bucket(self):
        from google.cloud import storage

        return storage.Client().bucket(self._bucket_name)

    def save(self, step_name: str) -> None:
        bucket = self._bucket()
        zip_path = _zip_gdb(self._gdb_path)
        try:
            bucket.blob(_STATE_OBJECT).upload_from_filename(str(zip_path))
            bucket.blob(_LOG_OBJECT).upload_from_string(step_name, content_type="text/plain")
            logger.info("Checkpoint saved after step: %s", step_name)
        finally:
            shutil.rmtree(zip_path.parent, ignore_errors=True)

    def load(self) -> str | None:
        from google.cloud.exceptions import NotFound

        bucket = self._bucket()
        log_blob = bucket.blob(_LOG_OBJECT)
        try:
            step_name = log_blob.download_as_text().strip()
        except NotFound:
            return None

        logger.info("Checkpoint found — last completed step: %s", step_name)
        tmp_zip = Path(tempfile.mkdtemp()) / "state.gdb.zip"
        try:
            bucket.blob(_STATE_OBJECT).download_to_filename(str(tmp_zip))
            _unzip_gdb(tmp_zip, self._gdb_path.parent)
            logger.info("GDB state restored from checkpoint")
        finally:
            shutil.rmtree(tmp_zip.parent, ignore_errors=True)
        return step_name

    def delete(self) -> None:
        from google.cloud.exceptions import NotFound

        bucket = self._bucket()
        for obj in (_LOG_OBJECT, _STATE_OBJECT):
            try:
                bucket.blob(obj).delete()
            except NotFound:
                pass
        logger.info("Checkpoint deleted")


class ScalityPipelineCheckpoint(PipelineCheckpoint):
    def __init__(self, client, bucket_name: str, gdb_path: Path) -> None:
        self._client = client
        self._bucket_name = bucket_name
        self._gdb_path = gdb_path

    def save(self, step_name: str) -> None:
        zip_path = _zip_gdb(self._gdb_path)
        try:
            self._client.fput_object(
                bucket_name=self._bucket_name,
                object_name=_STATE_OBJECT,
                file_path=str(zip_path),
                content_type="application/zip",
            )
            encoded = step_name.encode()
            self._client.put_object(
                bucket_name=self._bucket_name,
                object_name=_LOG_OBJECT,
                data=io.BytesIO(encoded),
                length=len(encoded),
                content_type="text/plain",
            )
            logger.info("Checkpoint saved after step: %s", step_name)
        finally:
            shutil.rmtree(zip_path.parent, ignore_errors=True)

    def load(self) -> str | None:
        from minio.error import S3Error

        try:
            response = self._client.get_object(self._bucket_name, _LOG_OBJECT)
            step_name = response.read().decode().strip()
            response.close()
            response.release_conn()
        except S3Error as exc:
            if exc.code == "NoSuchKey":
                return None
            raise

        logger.info("Checkpoint found — last completed step: %s", step_name)
        tmp_zip = Path(tempfile.mkdtemp()) / "state.gdb.zip"
        try:
            self._client.fget_object(
                bucket_name=self._bucket_name,
                object_name=_STATE_OBJECT,
                file_path=str(tmp_zip),
            )
            _unzip_gdb(tmp_zip, self._gdb_path.parent)
            logger.info("GDB state restored from checkpoint")
        finally:
            shutil.rmtree(tmp_zip.parent, ignore_errors=True)
        return step_name

    def delete(self) -> None:
        from minio.error import S3Error

        for obj in (_LOG_OBJECT, _STATE_OBJECT):
            try:
                self._client.remove_object(self._bucket_name, obj)
            except S3Error as exc:
                if exc.code != "NoSuchKey":
                    raise
        logger.info("Checkpoint deleted")
