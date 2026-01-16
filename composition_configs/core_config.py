from dataclasses import dataclass, field
from typing import (
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
    Any,
    Callable,
    Mapping,
    Sequence,
)
from enum import Enum

from composition_configs import type_defs
import config


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


class DataType(Enum):
    VECTOR = "vector"
    # Future: RASTER = "raster"


@dataclass(frozen=True)
class InputEntry:
    object: str
    input_type: InputType
    data_type: DataType
    tag: Literal["input"]
    path: str
    """
    Represents a single input feature used in partitioned processing.

    Users should prefer the factory methods `processing_input()` or `context_input()`
    over manual initialization to ensure correct and future-proof configuration.

    Attributes:
        object: Unique identifier used across the partitioning logic.
        input_type: Indicates whether the input is for processing or context.
        data_type: Describes the data format (e.g., vector).
        tag: Should always be 'input' for now. Set automatically by factory methods.
        path: Path to the input dataset.
    """

    @classmethod
    def processing_input(cls, object: str, path: str) -> "InputEntry":
        """Create a processing input (vector) entry with default tag."""
        return cls(
            object=object,
            input_type=InputType.PROCESSING,
            data_type=DataType.VECTOR,
            tag="input",
            path=path,
        )

    @classmethod
    def context_input(cls, object: str, path: str) -> "InputEntry":
        """Create a context input (vector) entry with default tag."""
        return cls(
            object=object,
            input_type=InputType.CONTEXT,
            data_type=DataType.VECTOR,
            tag="input",
            path=path,
        )


@dataclass(frozen=True)
class OutputEntry:
    object: str
    data_type: DataType
    tag: str
    path: str
    """
    Represents a single output feature to be produced in partitioned processing.

    Users should prefer the factory method `vector_output()` for correct setup,
    and to allow future support for other data types (e.g., raster).

    Attributes:
        object: Unique identifier used across the partitioning logic.
        data_type: Describes the data format (e.g., vector).
        tag: Identifier for the output version (e.g., 'after_rbc').
        path: Path where the output dataset will be written.
    """

    @classmethod
    def vector_output(cls, object: str, tag: str, path: str) -> "OutputEntry":
        """Create a vector output entry."""
        return cls(
            object=object,
            data_type=DataType.VECTOR,
            tag=tag,
            path=path,
        )


@dataclass(frozen=True)
class InjectIO:
    object: str
    tag: str


@dataclass(frozen=True)
class ResolvedInputEntry:
    object: str
    tag: str
    path: str
    input_type: str
    data_type: str


@dataclass(frozen=True)
class ResolvedOutputEntry:
    object: str
    tag: str
    path: str
    data_type: str


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
    documentation_directory: type_defs.SubdirectoryPath


class PartitionMethod(Enum):
    FEATURES = "FEATURES"
    VERTICES = "VERTICES"


ParamPayload = Optional[Union[Any, Sequence[Any]]]


@dataclass
class FuncMethodEntryConfig:
    func: Callable[..., Any]
    params: ParamPayload = None


@dataclass
class ClassMethodEntryConfig:
    class_: type
    method: Callable[..., Any]
    init_params: ParamPayload = None
    method_params: ParamPayload = None


@dataclass
class MethodEntriesConfig:
    entries: list[Union[FuncMethodEntryConfig, ClassMethodEntryConfig]]


@dataclass
class PartitionRunConfig:
    max_elements_per_partition: int
    context_radius_meters: int
    run_partition_optimization: bool = config.select_study_area
    partition_method: PartitionMethod = PartitionMethod.FEATURES
    object_id_column: str = "OBJECTID"
