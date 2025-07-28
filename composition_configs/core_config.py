from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple, Union
from enum import Enum


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


class InputType(Enum):
    PROCESSING = "processing"
    CONTEXT = "context"
    REFERENCE = "reference"


@dataclass(frozen=True)
class InputEntry:
    object: str
    input_type: InputType
    tag: Literal["input"]
    path: str


@dataclass(frozen=True)
class OutputEntry:
    object: str
    tag: str
    path: str


@dataclass(frozen=True)
class InjectIO:
    object: str
    tag: str


@dataclass(frozen=True)
class ResolvedEntry:
    object: str
    tag: str
    path: str
    input_type: Optional[str] = None


@dataclass(frozen=True)
class PartitionInputConfig:
    entries: List[InputEntry]


@dataclass(frozen=True)
class PartitionOutputConfig:
    entries: List[OutputEntry]


@dataclass
class PartitionIOConfig:
    input_config: PartitionInputConfig
    output_config: PartitionOutputConfig
    dictionary_documentation_path: Optional[str] = None


class PartitionMethod(Enum):
    FEATURES = "FEATURES"
    VERTICES = "VERTICES"


@dataclass
class PartitionRunConfig:
    max_elements_per_partition: int
    context_radius_meters: int
    run_partition_optimization: bool = True
    partition_method: PartitionMethod = PartitionMethod.FEATURES
    object_id_column: str = "OBJECTID"


input_config = PartitionInputConfig(
    entries=[
        InputEntry(
            object="building_points",
            input_type=InputType.PROCESSING,
            tag="input",
            path="some_path",
        ),
        InputEntry(
            object="building_polygons",
            input_type=InputType.PROCESSING,
            tag="input",
            path="some_path",
        ),
        InputEntry(
            object="road",
            input_type=InputType.CONTEXT,
            tag="input",
            path="some_path",
        ),
    ]
)

output_config = PartitionOutputConfig(
    entries=[
        OutputEntry(
            object="building_points",
            tag="some_logic",
            path="some_path",
        ),
        OutputEntry(
            object="building_polygons",
            tag="some_logic",
            path="some_path",
        ),
    ]
)
partitio_io_config = PartitionIOConfig(
    input_config=input_config,
    output_config=output_config,
)
