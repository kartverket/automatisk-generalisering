from dataclasses import dataclass
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
    type: IOType
    path: str


@dataclass(frozen=True)
class OutputEntry:
    tag: str
    path: str


@dataclass
class PartitionInputConfig:
    inputs: Dict[str, InputEntry]


@dataclass
class PartitionOutputConfig:
    outputs: Dict[str, OutputEntry]


@dataclass
class PartitionIOConfig:
    input_config: PartitionInputConfig
    output_config: PartitionOutputConfig
    dictionary_documentation_path: Optional[str] = None


test_input = PartitionInputConfig(
    inputs={
        "road": InputEntry(
            type=IOType.INPUT,
            path="test_input_path",
        ),
        "building": InputEntry(
            type=IOType.CONTEXT,
            path="test_input_path",
        ),
    }
)

test_output = PartitionOutputConfig(
    outputs={
        "road": OutputEntry(
            tag="merge_output",
            path="output_path",
        )
    }
)

partition_io_config = PartitionIOConfig(
    input_config=test_input,
    output_config=test_output,
)

partition_io_2 = PartitionIOConfig(
    input_config=PartitionInputConfig(
        inputs={
            "railroad": InputEntry(
                type=IOType.INPUT,
                path="some_path",
            )
        }
    ),
    output_config=PartitionOutputConfig(
        {
            "railroad": OutputEntry(
                tag="some_output",
                path="some_path",
            )
        }
    ),
)

input_2 = PartitionInputConfig(
    inputs={
        "some_object": InputEntry(
            type=IOType.INPUT,
            path="some_path",
        )
    }
)

output_2 = PartitionOutputConfig(
    outputs={
        "some_object": OutputEntry(
            tag="some_output",
            path="some_path",
        )
    }
)

test_io_config_2 = PartitionIOConfig(
    input_config=input_2,
    output_config=output_2,
)


@dataclass
class TempPartConfig:
    alias_path_data: Dict[str, Tuple[Literal["input", "context", "reference"], str]]
    alias_path_outputs: Dict[str, Tuple[str, str]]
    custom_functions: Optional[List] = None
    dictionary_documentation_path: Optional[str] = None
