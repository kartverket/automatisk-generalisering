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


class IOType(Enum):
    INPUT = "input"
    CONTEXT = "context"
    REFERENCE = "reference"


@dataclass(frozen=True)
class InputEntry:
    tag: str
    input_type: IOType
    path: str


@dataclass(frozen=True)
class OutputEntry:
    tag: str
    path: str


@dataclass
class PartitionInputConfig:
    entries: List[InputEntry] = field(default_factory=list)

    def __post_init__(self):
        self._inputs: Dict[str, InputEntry] = {
            entry.tag: entry for entry in self.entries
        }

    @property
    def inputs(self) -> Dict[str, InputEntry]:
        return self._inputs


@dataclass
class PartitionOutputConfig:
    entries: List[OutputEntry] = field(default_factory=list)

    def __post_init__(self):
        self._outputs: Dict[str, OutputEntry] = {
            entry.tag: entry for entry in self.entries
        }

    @property
    def outputs(self) -> Dict[str, OutputEntry]:
        return self._outputs


@dataclass
class PartitionIOConfig:
    input_config: PartitionInputConfig
    output_config: PartitionOutputConfig
    dictionary_documentation_path: Optional[str] = None


input_config = PartitionInputConfig(
    entries=[
        InputEntry(
            tag="building",
            input_type=IOType.INPUT,
            path="some_path",
        )
    ]
)

output_config = PartitionOutputConfig(
    entries=[
        OutputEntry(
            tag="building",
            path="some_path",
        ),
    ]
)
partitio_io_config = PartitionIOConfig(
    input_config=input_config, output_config=output_config
)


@dataclass
class TempPartConfig:
    alias_path_data: Dict[str, Tuple[Literal["input", "context", "reference"], str]]
    alias_path_outputs: Dict[str, Tuple[str, str]]
    custom_functions: Optional[List] = None
    dictionary_documentation_path: Optional[str] = None
