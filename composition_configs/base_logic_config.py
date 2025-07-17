from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union


@dataclass
class WorkFileConfig:
    """
    Configuration object for work file management behavior.

    Args:
        root_file (str): The core file name used to generate unique file names.
        write_to_memory (bool): If True, files are written to memory, if False, written to disk.
        keep_files (bool): If True, work files are kept after execution; if False, they are deleted when done.

    """

    root_file: str
    write_to_memory: bool = False
    keep_files: bool = False
