from dataclasses import dataclass
from enum import Enum
from typing import (
    Any,
    Callable,
    List,
    Literal,
    Optional,
    Sequence,
    Union,
)

from composition_configs import type_defs
from paths import require


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


class OutputExtractionMethod(Enum):
    """
    How each partition's output is extracted before appending to the final output.

    SELECTION: keep whole features owned by the partition (PARTITION_FIELD = 1, i.e.
        features whose center lies in the partition). Avoids duplication via center-in
        ownership.
    CLIP: clip each iteration output by the partition polygon and append the result.
        Cuts features at partition boundaries; non-overlapping partitions prevent
        duplication. Does not rely on PARTITION_FIELD.
    """

    SELECTION = "selection"
    CLIP = "clip"


@dataclass(frozen=True)
class OutputEntry:
    object: str
    data_type: DataType
    tag: str
    path: str
    extraction_method: OutputExtractionMethod = OutputExtractionMethod.SELECTION
    """
    Represents a single output feature to be produced in partitioned processing.

    Users should prefer the factory method `vector_output()` for correct setup,
    and to allow future support for other data types (e.g., raster).

    Attributes:
        object: Unique identifier used across the partitioning logic.
        data_type: Describes the data format (e.g., vector).
        tag: Identifier for the output version (e.g., 'after_rbc').
        path: Path where the output dataset will be written.
        extraction_method: How this output's per-partition slice is produced before
            being appended to the final output. Only meaningful for vector outputs.
    """

    @classmethod
    def vector_output(
        cls,
        object: str,
        tag: str,
        path: str,
        extraction_method: OutputExtractionMethod = OutputExtractionMethod.SELECTION,
    ) -> "OutputEntry":
        """Create a vector output entry."""
        return cls(
            object=object,
            data_type=DataType.VECTOR,
            tag=tag,
            path=path,
            extraction_method=extraction_method,
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
    input_type: InputType
    data_type: DataType


@dataclass(frozen=True)
class ResolvedOutputEntry:
    object: str
    tag: str
    path: str
    data_type: DataType
    extraction_method: OutputExtractionMethod


@dataclass(frozen=True)
class PartitionInputConfig:
    entries: List[InputEntry]


@dataclass(frozen=True)
class PartitionOutputConfig:
    entries: List[OutputEntry]


@dataclass
class PartitionIOConfig:
    """
    Declares the input/output datasets and documentation location for a partition run.

    Attributes:
        input_config: Processing and context input entries.
        output_config: Output entries to be produced.
        documentation_directory: Where per-run JSON logs are written.
        custom_partition_feature: Optional path to a user-supplied partition polygon
            feature class. When set, the iterator does NOT generate cartographic
            partitions and uses this feature directly. The caller is responsible for
            providing a valid, topologically correct polygon feature class with
            contiguous OBJECTIDs (1..N); only the geometry type (polygon) is validated.
            Incompatible with run_partition_optimization=True.
    """

    input_config: PartitionInputConfig
    output_config: PartitionOutputConfig
    documentation_directory: type_defs.SubdirectoryPath
    custom_partition_feature: Optional[str] = None


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
    run_partition_optimization: bool = require("SELECT_STUDY_AREA")
    partition_method: PartitionMethod = PartitionMethod.FEATURES
    object_id_column: str = "OBJECTID"
