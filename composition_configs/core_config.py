from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union
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


class InputTag(Enum):
    PROCESSING = "processing"
    CONTEXT = "context"
    REFERENCE = "reference"


@dataclass(frozen=True)
class InputEntry:
    object: str
    tag: InputTag
    path: str


@dataclass(frozen=True)
class OutputEntry:
    object: str
    tag: str
    path: str


@dataclass
class PartitionInputConfig:
    entries: List[InputEntry] = field(default_factory=list)

    def __post_init__(self):
        self._inputs: Dict[str, InputEntry] = {
            entry.object: entry for entry in self.entries
        }

    @property
    def inputs(self) -> Dict[str, InputEntry]:
        return self._inputs


@dataclass
class PartitionOutputConfig:
    entries: List[OutputEntry] = field(default_factory=list)

    def __post_init__(self):
        self._outputs: Dict[str, OutputEntry] = {
            entry.object: entry for entry in self.entries
        }

    @property
    def outputs(self) -> Dict[str, OutputEntry]:
        return self._outputs


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
            tag=InputTag.PROCESSING,
            path="some_path",
        ),
        InputEntry(
            object="building_polygons",
            tag=InputTag.PROCESSING,
            path="some_path",
        ),
        InputEntry(
            object="road",
            tag=InputTag.CONTEXT,
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

input_config = PartitionInputConfig(
    entries=[
        InputEntry(
            object="",
            tag=InputTag.PROCESSING,
            path="",
        )
    ]
)
partition_io_2 = PartitionIOConfig()


@dataclass
class TempPartConfig:
    alias_path_data: Dict[str, Tuple[Literal["input", "context", "reference"], str]]
    alias_path_outputs: Dict[str, Tuple[str, str]]
    custom_functions: Optional[List] = None
    dictionary_documentation_path: Optional[str] = None
