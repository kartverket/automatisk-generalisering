import os
from pathlib import Path


def make_local_output_path(remote_output_path: str) -> str:
    """
    Create a local output path based on the remote output path
    """
    local_output_path = os.path.join("/tmp", os.path.basename(remote_output_path))
    return local_output_path


def append_partition_index(path: str, partition_index: int) -> str:
    """Append partition index before the suffix (e.g. road.gdb -> road_3.gdb)."""
    candidate = Path(path)
    if candidate.suffix:
        indexed_name = f"{candidate.stem}_{partition_index}{candidate.suffix}"
    else:
        indexed_name = f"{candidate.name}_{partition_index}"
    return str(candidate.with_name(indexed_name))
