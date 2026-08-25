from __future__ import annotations

import logging
import shutil
from pathlib import Path

from composition_configs.logic_config import DataRef

from .interface import ArchiveClient

logger = logging.getLogger(__name__)


class LocalArchiveClient(ArchiveClient):
    def __init__(
        self,
        *,
        local_input_path: str = "/tmp/input.gdb",
        local_output_path: str = "/tmp/output.gdb",
    ) -> None:
        self.local_input_path = local_input_path
        self.local_output_path = local_output_path

    def read(self, remote: DataRef) -> DataRef:
        logger.info("[LocalArchiveClient] Reading local path: %s", remote.path)
        _copy_path(remote.path, self.local_input_path)
        return DataRef(path=self.local_input_path, tag=remote.tag)

    def write(self, local: DataRef, remote: DataRef) -> None:
        logger.info(
            "[LocalArchiveClient] Writing local path: %s -> %s",
            local.path,
            remote.path,
        )
        _copy_path(local.path, remote.path)

    def list_objects(self, path: str) -> list[str]:
        candidate = Path(path)
        if not candidate.exists():
            return []
        if candidate.is_file():
            return [str(candidate)]
        return [str(p) for p in candidate.rglob("*") if p.is_file()]

    def get_object(self, path: str) -> bytes:
        with open(path, "rb") as source:
            return source.read()

    def put_object(self, path: str, data: bytes) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with open(destination, "wb") as target:
            target.write(data)

    def delete_object(self, path: str) -> None:
        candidate = Path(path)
        if not candidate.exists():
            return
        if candidate.is_dir():
            shutil.rmtree(candidate)
        else:
            candidate.unlink()


def _copy_path(source_path: str, destination_path: str) -> None:
    source = Path(source_path)
    destination = Path(destination_path)

    if not source.exists():
        raise FileNotFoundError(f"Source path does not exist: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.is_dir():
            shutil.rmtree(destination)
        else:
            destination.unlink()

    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)
