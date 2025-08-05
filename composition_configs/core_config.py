from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple, Union, Any, Callable
from enum import Enum

from composition_configs import types


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


class outputType(Enum):
    VECTOR = "vector"


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
class ResolvedInputEntry:
    object: str
    tag: str
    path: str
    input_type: str


@dataclass(frozen=True)
class ResolvedOutputEntry:
    object: str
    tag: str
    path: str


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
    dictionary_documentation_path: types.SubdirectoryPath


class PartitionMethod(Enum):
    FEATURES = "FEATURES"
    VERTICES = "VERTICES"


@dataclass
class FuncMethodEntryConfig:
    func: Callable
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClassMethodEntryConfig:
    class_: type
    method: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class MethodEntriesConfig:
    entries: list[Union[FuncMethodEntryConfig, ClassMethodEntryConfig]]


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
partition_method_config = MethodEntriesConfig(entries=[ClassMethodEntryConfig(class_=some_class, method="run", params={"some_param:" InjectIO(object="some_object", tag="some_logic2")})])
