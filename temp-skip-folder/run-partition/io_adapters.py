import logging
import os
import shutil
from collections.abc import Callable
from pathlib import Path

from composition_configs.logic_config import DataRef

ReadCallable = Callable[[DataRef], DataRef]
WriteCallable = Callable[[DataRef, DataRef], None]

logger = logging.getLogger(__name__)


def append_partition_index(path: str, partition_index: int) -> str:
    """Append partition index before the suffix (e.g. road.gdb -> road_3.gdb)."""
    candidate = Path(path)
    if candidate.suffix:
        indexed_name = f"{candidate.stem}_{partition_index}{candidate.suffix}"
    else:
        indexed_name = f"{candidate.name}_{partition_index}"
    return str(candidate.with_name(indexed_name))


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


def make_local_fs_read_write(
    *,
    adapter_name: str,
    local_input_path: str = "/tmp/input.gdb",
    local_output_path: str = "/tmp/output.gdb",
) -> tuple[ReadCallable, WriteCallable]:
    """
    Build illustrative read/write callables.

    This adapter treats DataRef paths as filesystem locations so the example can run
    end-to-end locally while preserving the same callable contract as bucket-backed IO.
    """

    def read(remote: DataRef) -> DataRef:
        logger.info("[%s] Reading remote path: %s", adapter_name, remote.path)
        _copy_path(remote.path, local_input_path)
        return DataRef(path=local_input_path)

    def write(local: DataRef, remote: DataRef) -> None:
        logger.info(
            "[%s] Writing local path: %s -> remote path: %s",
            adapter_name,
            local.path,
            remote.path,
        )
        _copy_path(local.path, remote.path)

    return read, write
