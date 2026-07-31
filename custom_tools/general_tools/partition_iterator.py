import copy
import os
import shutil
import time
import traceback
from dataclasses import asdict, dataclass, field, fields, is_dataclass, replace
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import arcpy

from composition_configs import core_config, type_defs
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy, file_utilities, param_utils
from env_setup import environment_setup
from file_manager.work_file_manager import PartitionWorkFileManager


@dataclass
class PreparedInput:
    """
    One configured input dataset, plus everything preparation learns about it.

    `source_path` is what the caller configured. `active_path` is what partition
    selection actually reads from: the same file for processing inputs, but a
    pre-filtered copy for context inputs when a search distance is set.

    `pre_optimization_count` and `reduced_count` stay None for processing inputs;
    they only describe the context pre-filtering step.
    """

    object: str
    input_type: core_config.InputType
    data_type: core_config.DataType
    source_path: str
    active_path: str
    dummy_path: Optional[str] = None
    count: int = 0
    pre_optimization_count: Optional[int] = None
    reduced_count: Optional[int] = None

    @classmethod
    def from_resolved(cls, entry: core_config.ResolvedInputEntry) -> "PreparedInput":
        """Start from a resolved config entry, with the source path active."""
        return cls(
            object=entry.object,
            input_type=entry.input_type,
            data_type=entry.data_type,
            source_path=entry.path,
            active_path=entry.path,
        )

    def is_vector_of_type(self, input_type: core_config.InputType) -> bool:
        """Return True iff this is a vector dataset of the given input type."""
        return (
            self.input_type is input_type
            and self.data_type is core_config.DataType.VECTOR
        )


@dataclass
class PartitionStats:
    """
    Per-object measurements for a single partition.

    `count` and `vertex_count` cover everything selected for the partition. The
    processing/context split below is derived from `PARTITION_FIELD` and only applies
    to processing inputs; it stays zeroed for context inputs and for partitions where
    the object had no features.
    """

    count: int = 0
    vertex_count: int = 0
    processing_object_count: int = 0
    context_object_count: int = 0
    processing_vertex_count: int = 0
    context_vertex_count: int = 0
    processing_object_percentage: float = 0
    context_object_percentage: float = 0
    processing_vertex_percentage: float = 0
    context_vertex_percentage: float = 0


@dataclass
class PeakStat:
    """A single observed extreme: the value, and the partition it came from."""

    value: Optional[float] = None
    partition_id: Optional[int] = None


@dataclass
class MinMaxStat:
    """
    Running highest and lowest value for one metric across partitions.

    Feed observations with `observe()`; the first one initializes both ends.
    """

    max: PeakStat = field(default_factory=PeakStat)
    min: PeakStat = field(default_factory=PeakStat)

    def observe(self, value: float, partition_id: int) -> None:
        if self.max.value is None or value > self.max.value:
            self.max = PeakStat(value=value, partition_id=partition_id)
        if self.min.value is None or value < self.min.value:
            self.min = PeakStat(value=value, partition_id=partition_id)


@dataclass
class OutputOverview:
    """Totals for one output tag, and how far it drifted from the input it came from."""

    output_object_count: int = 0
    output_vertex_count: int = 0
    object_count_diff_absolute: Optional[int] = None
    object_count_diff_percentage: Optional[float] = None
    vertex_count_diff_absolute: Optional[int] = None
    vertex_count_diff_percentage: Optional[float] = None


@dataclass
class PercentageAccumulator:
    """
    Running sums of the per-partition percentage splits for one processing input.

    Kept outside `ProcessingInputOverview` because these are intermediate values used
    to compute the averages, and the overview is serialized verbatim to overview.json.
    """

    processing_object_percentage: float = 0
    context_object_percentage: float = 0
    processing_vertex_percentage: float = 0
    context_vertex_percentage: float = 0


@dataclass
class ProcessingInputOverview:
    """Whole-run totals, extremes, and averages for one processing input."""

    input_object_count: int = 0
    input_vertex_count: int = 0
    partitions_with_object_present: int = 0
    processing_object_count: MinMaxStat = field(default_factory=MinMaxStat)
    processing_vertex_count: MinMaxStat = field(default_factory=MinMaxStat)
    processing_object_percentage: MinMaxStat = field(default_factory=MinMaxStat)
    context_object_percentage: MinMaxStat = field(default_factory=MinMaxStat)
    avg_processing_object_percentage: Optional[float] = None
    avg_context_object_percentage: Optional[float] = None
    avg_processing_vertex_percentage: Optional[float] = None
    avg_context_vertex_percentage: Optional[float] = None
    outputs: Dict[str, OutputOverview] = field(default_factory=dict)


@dataclass
class RunConfigOverview:
    """The settings this run was executed with."""

    partition_method: core_config.PartitionMethod
    search_distance_meters: int
    search_distance_used: bool
    max_elements_per_partition: int
    run_partition_optimization: bool
    final_partition_feature_count: Optional[int]
    custom_partition_feature_used: bool


@dataclass
class PartitionSummary:
    """How the work spread across partitions."""

    total_partitions: int = 0
    partitions_with_inputs: int = 0
    partitions_skipped: int = 0
    partition_id_highest_load: Optional[int] = None
    highest_load_value: int = 0
    average_load: Optional[float] = None


@dataclass
class RuntimeOverview:
    """Wall-clock figures for the run."""

    start_time: Optional[str] = None
    end_time: Optional[str] = None
    average_iteration_runtime_seconds: Optional[float] = None
    max_iteration_runtime_seconds: Optional[float] = None
    max_iteration_runtime_partition_id: Optional[int] = None


@dataclass
class ContextInputsSummary:
    """Context-input totals, including what the pre-filtering step saved."""

    total_processed_objects: int = 0
    total_processed_vertices: int = 0
    total_objects_saved_by_optimization: Optional[int] = None
    total_processing_input_context_objects: int = 0
    total_processing_input_context_vertices: int = 0


@dataclass
class OverviewCatalog:
    """The full run report, serialized to overview.json at the end of the run."""

    run_config: RunConfigOverview
    partition_summary: PartitionSummary = field(default_factory=PartitionSummary)
    runtime: RuntimeOverview = field(default_factory=RuntimeOverview)
    context_inputs_summary: ContextInputsSummary = field(
        default_factory=ContextInputsSummary
    )
    processing_inputs: Dict[str, ProcessingInputOverview] = field(default_factory=dict)


class PartitionIterator:
    """
    Partitioned processing pipeline for large vector datasets with context-aware selection
    and configurable, injected methods.

    # Overview
    This iterator splits work into *cartographic partitions* and processes only the
    features relevant to each partition. It distinguishes between:
      - **processing inputs**: primary datasets to process, and
      - **context inputs**: supporting datasets selected within a configurable distance
        of the processing features.

    For each partition, the iterator:
      1. Selects processing features (center-in partition, plus optional near-by radius).
      2. Selects context features (within the same radius of the partition).
      3. Resolves and executes *injected methods* (functions or class methods) whose
         parameters may include injected I/O paths.
      4. Appends the partition’s outputs to the configured final outputs.
      5. Logs iteration catalogs, method parameters, attempts, and errors to a
         documentation directory.

    # Catalogs
    The iterator maintains three dictionaries:
      - `input_catalog`: per *object* (dataset name) holds a `PreparedInput` record with
        the configured source path, the active (possibly pre-filtered) path, and counts;
        populated from `PartitionIOConfig`.
      - `output_catalog`: per object stores final output paths; populated from
        `PartitionIOConfig`. Per-output settings live on `output_entries` instead,
        since this layout only holds tag-to-path pairs.
      - `iteration_paths`: per partition, per object, the iteration-scoped paths
        (the selected subset, plus any tags injected methods allocate). Open-ended:
        injected methods may introduce new tags and new objects at runtime.
      - `iteration_stats`: per partition, per object, a `PartitionStats` record of
        counts. Fixed schema, unlike `iteration_paths`, which is why the two are
        kept apart; `_iteration_catalog_snapshot()` merges them for the JSON log.

    The following keys are used inside catalogs:
      - `DATA_TYPE_KEY`: metadata about each object’s data type.
      - `INPUT_KEY`: the canonical tag for the active input path of an object.
      - `COUNT`: number of selected features this iteration.
      - `DUMMY`: a dummy feature path used to keep downstream logic stable when a
        particular object has no features in a partition.

    # Injection & method execution
    Injected method configs (functions or class methods) may include `InjectIO(object, tag)`
    placeholders that refer to a *catalog object* (dataset key) and a *tag* (path key).

    Path resolution rules per partition:
    - `InjectIO(obj, "input")`: always resolves to the **selected features for this partition**
        (never the global dataset), ensuring your method receives only the slice relevant
        to the current partition.
    - `InjectIO(obj, some_tag)` where `some_tag != "input"` resolves to a **new, unique
        iteration-scoped path** under the iteration work directory. If no such entry exists
        yet for `(obj, some_tag)`, the iterator creates and registers it in the
        `iteration_paths[obj][some_tag]`. Your injected method is expected to write to it.
    - You may introduce **new tags for an existing object** (e.g., `"buffer"`, `"cleaned"`)
        or even **new objects** via `InjectIO(new_object, new_tag)`. The iterator will allocate
        paths and track them in `iteration_paths` as those tags/objects appear in params.

    Resolution & execution flow:
    1. `resolve_injected_io_for_methods(...)` deep-walks params (dataclasses, dicts, lists,
        tuples, sets), replacing every `InjectIO` with a concrete, partition-scoped path, and
        returns a *resolved* config.
    2. `execute_injected_methods_with_retry(...)` runs the resolved methods with retry
        semantics. For class methods, constructor vs method kwargs are split automatically
        (only names present on `__init__` are sent to the constructor).
    3. Each attempt produces JSON logs (params, status, exceptions with tracebacks). On
        success, a consolidated `method_log_{partition_id}.json` is written. On failure,
        per-attempt logs live under `error_logs/error_{partition_id}/attempt_{n}_error.json`.

    Notes:
    - The iterator does **not** implicitly copy data into non-"input" targets; it only
        allocates file paths. Your injected method is responsible for creating/writing those
        outputs.
    - Using `"input"` guarantees you receive the *current partition’s selection*, not the
        global source.

    # Partition creation & selection
    Cartographic partitions are created from all configured processing inputs.
    For each partition:
      - Processing features are selected by "center in partition" and optionally augmented
        with "near partition" features (radius = `context_radius_meters`), with a
        `PARTITION_FIELD` set to 1 (center-in) or 0 (nearby) to preserve provenance.
      - Context features are selected by distance to the same partition (using the
        configured radius).

    # Logging (documentation directory)
    At the start of `run()`, the configured `documentation_directory` is cleared and
    recreated (with safety checks). The iterator writes:
      - `input_catalog.json`, `output_catalog.json` (initial state),
      - `iteration_catalog/catalog_{partition_id}.json` (per-partition selection),
      - `method_logs/method_log_{partition_id}.json` (final success per partition),
      - `error_logs/error_{partition_id}/attempt_{n}_error.json` (per attempt, on error),
      - `error_log.json` (retry summary across partitions).

    # Args (configs)
    - `partition_io_config (core_config.PartitionIOConfig)`: Declares input objects
      (processing/context) and output objects (vector outputs) with their paths and
      data types. Also provides `documentation_directory`.
    - `partition_method_inject_config (core_config.MethodEntriesConfig)`: The list of
      injected methods (functions or class methods) with their parameter configs. Any
      `InjectIO` placeholders will be resolved per partition.
    - `partition_iterator_run_config (core_config.PartitionRunConfig)`: Runtime knobs:
      context radius (meters), max elements per partition, partition method
      ("FEATURES" or "VERTICES"), object ID field, and whether to auto-optimize the
      partition feature count.
    - `work_file_manager_config (core_config.WorkFileConfig)`: Controls where and how
      temporary/iteration/persistent paths are generated.

    # Side effects
    - Creates and deletes intermediate feature classes and layers.
    - Writes JSON logs under `documentation_directory` (safe-guarded).
    - Appends to final outputs as partitions complete.
    - Adds then removes (via cleanup) the `PARTITION_FIELD` as needed.

    # Raises
    - `ValueError` for duplicate input objects.
    - `RuntimeError` when no valid partition size can be found (if optimization is enabled).
    - Any exception thrown inside injected methods is captured, logged, and retried up to
      the configured maximum. If all retries fail, the exception is re-raised.

    # Example (high level)
        iterator = PartitionIterator(
            partition_io_config=io_config,
            partition_method_inject_config=methods_config,
            partition_iterator_run_config=run_config,
            work_file_manager_config=wm_config,
        )
        iterator.run()
    """

    DATA_TYPE_KEY = "data_type"
    INPUT_KEY = "input"
    PARTITION_ID_FIELD = "partition_id"
    PARTITION_FIELD = "partition_selection_field"

    def __init__(
        self,
        partition_io_config: core_config.PartitionIOConfig,
        partition_method_inject_config: core_config.MethodEntriesConfig,
        partition_iterator_run_config: core_config.PartitionRunConfig,
        work_file_manager_config: core_config.WorkFileConfig,
    ):
        """
        Args:
            partition_io_config: Declares input objects (processing/context) and output objects
                (vector outputs) with paths and data types; includes `documentation_directory`.
            partition_method_inject_config:
                Declares the injected methods (functions or class methods) with their parameter configs.
                These configs are expected to include `InjectIO(object, tag)` placeholders that resolve
                to partition-scoped paths at runtime. Without `InjectIO`, the iterator cannot pass
                partition selections or allocate iteration outputs, making the class effectively useless.
                See class docstring section *Injection & method execution* for details.
            partition_iterator_run_config: Runtime settings (context radius in meters, max
                elements per partition, partition method "FEATURES"/"VERTICES", object ID
                field, whether to optimize partition size).
            work_file_manager_config: Controls generation of temp/iteration/persistent paths.
        """

        self.input_catalog: Dict[str, PreparedInput] = {}
        self.output_catalog: Dict[str, Dict[str, Any]] = {}
        self.iteration_paths: Dict[str, Dict[str, str]] = {}
        self.iteration_stats: Dict[str, PartitionStats] = {}

        input_entries_resolved = [
            core_config.ResolvedInputEntry(
                object=e.object,
                tag=e.tag,
                path=e.path,
                input_type=e.input_type,
                data_type=e.data_type,
            )
            for e in partition_io_config.input_config.entries
        ]

        output_entries_resolved = [
            core_config.ResolvedOutputEntry(
                object=e.object,
                tag=e.tag,
                path=e.path,
                data_type=e.data_type,
                extraction_method=e.extraction_method,
            )
            for e in partition_io_config.output_config.entries
        ]

        self.resolve_partition_input_config(
            entries=input_entries_resolved,
            target_dict=self.input_catalog,
        )

        self.resolve_partition_output_config(
            entries=output_entries_resolved,
            target_dict=self.output_catalog,
        )
        self.output_entries = output_entries_resolved

        self.documentation_directory = partition_io_config.documentation_directory

        self.list_of_methods = partition_method_inject_config

        self.search_distance = partition_iterator_run_config.context_radius_meters
        self.max_elements_per_partition = (
            partition_iterator_run_config.max_elements_per_partition
        )

        self.object_id_field = partition_iterator_run_config.object_id_column
        self.run_partition_optimization = (
            partition_iterator_run_config.run_partition_optimization
        )
        self.partition_method: core_config.PartitionMethod = (
            partition_iterator_run_config.partition_method
        )
        self.custom_partition_feature = partition_io_config.custom_partition_feature
        self.use_custom_partition_feature = self.custom_partition_feature is not None
        if self.use_custom_partition_feature and self.run_partition_optimization:
            raise ValueError(
                "run_partition_optimization=True is incompatible with a custom "
                "partition feature; optimization only exists to generate partitions."
            )

        self.max_partition_count: int = 1
        self.final_partition_feature_count: Optional[int] = None
        self.error_log = {}

        # PartitionIterator currently needs particular configuration for work files, at some steps
        temp_config = replace(
            work_file_manager_config, write_to_memory=True, keep_files=False
        )
        iteration_config = replace(
            work_file_manager_config, write_to_memory=False, keep_files=False
        )
        persistent_config = replace(work_file_manager_config, write_to_memory=False)

        self.work_file_manager_temp_files = PartitionWorkFileManager(config=temp_config)
        self.work_file_manager_iteration_files = PartitionWorkFileManager(
            config=iteration_config
        )
        self.work_file_manager_resolved_files = PartitionWorkFileManager(
            config=iteration_config
        )
        self.work_file_manager_persistent_files = PartitionWorkFileManager(
            config=persistent_config
        )
        self.work_file_manager_partition_feature = PartitionWorkFileManager(
            config=iteration_config
        )

        custom_path = self.custom_partition_feature
        if custom_path is not None:
            self._validate_custom_partition_feature(custom_path)
            self.partition_feature = custom_path
        else:
            self.partition_feature = (
                self.work_file_manager_partition_feature.generate_partition_path(
                    object_name="partition_feature",
                )
            )
        self.partition_features_all = (
            self.work_file_manager_partition_feature.generate_partition_path(
                object_name="partition_features_all",
            )
        )

        self.total_start_time: float
        self.iteration_times_with_input = []
        self.iteration_start_time: float
        self._last_injected_log = None

        self._overview_partition_loads: List[float] = []
        self._overview_pct_accumulators: Dict[str, PercentageAccumulator] = {}
        # Built here so the catalog is never None; partition_iteration rebuilds it once
        # the partition counts it reports are actually known.
        self._initialize_overview_catalog()

    def resolve_partition_input_config(
        self,
        entries: List[core_config.ResolvedInputEntry],
        target_dict: Dict[str, PreparedInput],
    ) -> None:
        """
        Add resolved input entries to `target_dict` as `PreparedInput` records.

        Ensures each object appears only once; raises on duplicates.
        """
        for entry in entries:
            if entry.object in target_dict:
                raise ValueError(
                    f"Duplicate input object: '{entry.object}' is not supported"
                )
            target_dict[entry.object] = PreparedInput.from_resolved(entry)

    def resolve_partition_output_config(
        self,
        entries: List[core_config.ResolvedOutputEntry],
        target_dict: Dict[str, Dict[str, Any]],
    ) -> None:
        """
        Add resolved output entries to `target_dict`.

        Ensures each (object, tag) pair is unique; raises on duplicate tags
        within the same object.
        """
        for entry in entries:
            entry_dict = target_dict.setdefault(entry.object, {})
            if entry.tag in entry_dict:
                raise ValueError(
                    f"Duplicate output tag '{entry.tag}' detected for object '{entry.object}'"
                )
            entry_dict[self.DATA_TYPE_KEY] = entry.data_type
            entry_dict[entry.tag] = entry.path

    def _validate_custom_partition_feature(self, path: str) -> None:
        """
        Validate that a user-supplied custom partition feature is a polygon.

        Only the geometry type is checked. The caller is responsible for providing a
        topologically correct feature class with contiguous OBJECTIDs (1..N), since the
        iteration loop selects partitions by `object_id_field = partition_id` over
        `range(1, count + 1)`. Feature count, overlaps, and topology are not validated.
        """
        if not arcpy.Exists(path):
            raise ValueError(f"Custom partition feature does not exist: {path}")
        shape_type = arcpy.Describe(path).shapeType
        if shape_type != "Polygon":
            raise ValueError(
                f"Custom partition feature must be a polygon, got '{shape_type}': {path}"
            )

    def _create_cartographic_partitions(self, element_limit: int) -> None:
        """
        Creates cartographic partitions based on the given element_limit.
        Overwrites any existing partition feature.
        """
        # generate_partition_path returns a plain str; the manager wants one of the
        # type_defs path types. Local narrowing until that return type is tightened.
        self.work_file_manager_partition_feature.delete_created_files(
            exceptions=[type_defs.GdbFilePath(self.partition_features_all)]
        )
        in_features = [
            prepared.active_path
            for prepared in self.input_catalog.values()
            if prepared.active_path is not None
        ]

        if not in_features:
            print("No input features available for creating partitions.")
            return

        arcpy.cartography.CreateCartographicPartitions(
            in_features=in_features,
            out_features=self.partition_feature,
            feature_count=element_limit,
            partition_method=self.partition_method.value,
        )
        print(f"Created partition feature: {self.partition_feature}")

    def _total_partition_load(self) -> int:
        """
        Returns the total load for the current partition based on partition_method.

        FEATURES: sum of feature counts across all catalog entries.
        VERTICES: sum of vertex counts across all catalog entries.
        """
        if self.partition_method is core_config.PartitionMethod.VERTICES:
            return sum(stats.vertex_count for stats in self.iteration_stats.values())
        return sum(stats.count for stats in self.iteration_stats.values())

    def _count_maximum_objects_in_partition(self) -> int:
        """
        What:
            Iterates over all partitions and determines the highest load (features or
            vertices depending on partition_method) found in any single partition.

        How:
            For each partition:
            - Select the partition geometry.
            - Run processing and context selection logic.
            - Track total load via _total_partition_load.
            - Cleanup intermediate files.

        Returns:
            int: Maximum partition load across all iterations.
        """
        self.update_max_partition_count()
        max_partition_load = 0

        for partition_id in range(1, self.max_partition_count + 1):
            self._reset_iteration_catalogs()
            iteration_partition = (
                self.work_file_manager_iteration_files.generate_partition_path(
                    object_name="partition_feature_iteration_selection",
                    partition_id=partition_id,
                )
            )

            self.select_partition_feature(
                iteration_partition=iteration_partition, object_id=partition_id
            )

            has_inputs = self.process_all_processing_inputs(
                iteration_partition=iteration_partition,
                partition_id=partition_id,
            )
            if not has_inputs:
                self.work_file_manager_iteration_files.delete_created_files()
                continue

            self.process_all_context_inputs(
                iteration_partition=iteration_partition,
                partition_id=partition_id,
            )

            total_load = self._total_partition_load()
            max_partition_load = max(max_partition_load, total_load)

            print(
                f"\nCounting objects for Partition: {partition_id}\n"
                f"Current total found: {total_load}\n"
                f"Current maximum found: {max_partition_load}"
            )

            self.work_file_manager_iteration_files.delete_created_files()

        return max_partition_load

    def _find_partition_size(self) -> int:
        """
        What:
            Searches for the optimal `feature_count` that ensures partitioned processing does not exceed
            the allowed maximum number of features in any single partition.

        How:
            Starts at the configured feature_count and decreases in steps until a valid configuration is found.
            Validity is determined by calling _count_maximum_objects_in_partition.

        Returns:
            int: A valid feature_count value that respects object limits.

        Raises:
            RuntimeError: If no valid feature_count is found.
        """
        candidate = int(self.max_elements_per_partition)
        max_allowed = candidate
        previous_partitions = 0
        attempts = 0

        def _calculate_decrement(current: int) -> int:
            base = int(max_allowed * 0.01)
            diff = max(1, int((current - max_allowed) * 0.5))
            return max(base, diff)

        while True:
            attempts += 1
            print(
                f"\n\nAttempt {attempts}: Testing candidate feature_count = {candidate}"
            )
            self._create_cartographic_partitions(element_limit=candidate)
            self.update_max_partition_count()

            if self.max_partition_count == previous_partitions:
                candidate -= int(max_allowed * 0.01)
                print(f"Stable partition count. Reducing candidate to {candidate}")
                continue

            previous_partitions = self.max_partition_count
            max_objects_found = self._count_maximum_objects_in_partition()

            print(f" -> Max objects found in a partition: {max_objects_found}")
            if max_objects_found <= max_allowed:
                print(f"Selected feature_count: {candidate}")
                self.final_partition_feature_count = candidate
                return candidate

            decrement = _calculate_decrement(max_objects_found)
            candidate -= decrement

            if candidate < 1:
                break

        raise RuntimeError(
            f"No valid feature count found under limit={max_allowed}. "
            f"Minimum candidate tested: {candidate}."
        )

    def delete_final_outputs(self):
        """Deletes all final output feature classes if they exist."""
        skip_keys = {self.DATA_TYPE_KEY}

        for object_key, tag_dict in self.output_catalog.items():
            for tag, final_output_path in tag_dict.items():
                if tag in skip_keys:
                    continue
                file_utilities.delete_feature(input_feature=final_output_path)

    def delete_iteration_files(self, *file_paths):
        """Deletes multiple feature classes or files from a list."""
        for file_path in file_paths:
            file_utilities.delete_feature(input_feature=file_path)
            print(f"Deleted file: {file_path}")

    def create_dummy_features(self) -> None:
        """
        Create an empty dummy feature class per input, matching its active path's schema.
        Used to provide stable placeholder inputs when a partition produces no features.
        """
        for object_key, prepared in self.input_catalog.items():
            if not prepared.active_path:
                continue

            dummy_feature_path = (
                self.work_file_manager_persistent_files.generate_partition_path(
                    object_name=object_key,
                    tag="dummy_feature",
                )
            )

            file_utilities.create_feature_class(
                template_feature=prepared.active_path, new_feature=dummy_feature_path
            )
            prepared.dummy_path = dummy_feature_path

    def update_empty_object_tag_with_dummy_file(
        self, object_key: str, tag: str
    ) -> None:
        """
        Replaces the value for the given tag with the dummy path if available for the object_key.
        """
        prepared = self.input_catalog.get(object_key)
        if prepared is None or prepared.dummy_path is None:
            return

        self.iteration_paths[object_key][tag] = prepared.dummy_path

    def _reset_documentation_dir(self) -> None:
        """
        Ensure documentation_directory is ready for this run.
        Deletes the whole directory if it exists, then recreates it.
        """
        docu_dir = self.documentation_directory
        if not isinstance(docu_dir, type_defs.SubdirectoryPath):
            raise TypeError(
                f"documentation_directory must be SubdirectoryPath, got {type(docu_dir).__name__}"
            )
        docu_dir_path = Path(docu_dir).resolve()
        if docu_dir_path.parent == docu_dir_path:
            raise ValueError(f"Refusing to delete root directory: {docu_dir_path}")

        if docu_dir_path.exists():
            shutil.rmtree(docu_dir_path, ignore_errors=True)
        docu_dir_path.mkdir(parents=True, exist_ok=True)

    def write_documentation(
        self, name: str, dict_data: Any, sub_dir: Optional[str] = None
    ) -> None:
        """
        Writes a JSON file to documentation_directory or its subdirectory.
        Ensures the destination directory exists.

        The payload is passed through `_jsonify`, so callers may hand over dataclass
        records (or catalogs holding them) rather than pre-flattened dicts.
        """
        base_dir = self.documentation_directory
        out_dir = os.path.join(base_dir, sub_dir) if sub_dir else base_dir
        os.makedirs(out_dir, exist_ok=True)

        json_path = os.path.join(out_dir, f"{name}.json")
        file_utilities.write_dict_to_json(
            path=json_path, dict_data=self._jsonify(dict_data)
        )

    def _jsonify(self, obj: Any) -> Any:
        """
        Make params JSON-safe:
        - dataclasses -> asdict
        - enums -> their value
        - Path -> str
        - sets -> lists
        - dict/list/tuple -> recurse
        - otherwise return as-is
        """
        if is_dataclass(obj) and not isinstance(obj, type):
            return self._jsonify(asdict(obj))
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, dict):
            return {str(key): self._jsonify(value) for key, value in obj.items()}
        if isinstance(obj, (list, tuple)):
            t = [self._jsonify(x) for x in obj]
            return t if isinstance(obj, list) else tuple(t)
        if isinstance(obj, set):
            return [self._jsonify(x) for x in obj]
        return obj

    def update_max_partition_count(self) -> None:
        """
        Determine the maximum OBJECTID for partitioning.
        """
        self.max_partition_count = file_utilities.count_objects(self.partition_feature)

    def _reset_iteration_catalogs(self) -> None:
        """Drop all per-partition paths and stats before starting a partition."""
        self.iteration_paths = {}
        self.iteration_stats = {}

    def _iteration_catalog_snapshot(self) -> Dict[str, Dict[str, Any]]:
        """
        Merge `iteration_paths` and `iteration_stats` into one per-object view.

        Only used for the `catalog_{partition_id}.json` log, which reads better as a
        single record per object than as two parallel structures.
        """
        snapshot: Dict[str, Dict[str, Any]] = {}
        for object_key in {*self.iteration_paths, *self.iteration_stats}:
            entry: Dict[str, Any] = dict(self.iteration_paths.get(object_key, {}))
            stats = self.iteration_stats.get(object_key)
            if stats is not None:
                entry.update(asdict(stats))
            snapshot[object_key] = entry
        return snapshot

    def _processing_items(self) -> Iterator[PreparedInput]:
        """
        Yield every PROCESSING vector input in `input_catalog`.
        """
        for prepared in self.input_catalog.values():
            if prepared.is_vector_of_type(core_config.InputType.PROCESSING):
                yield prepared

    def _context_items(self) -> Iterator[PreparedInput]:
        """
        Yield every CONTEXT vector input in `input_catalog`.
        """
        for prepared in self.input_catalog.values():
            if prepared.is_vector_of_type(core_config.InputType.CONTEXT):
                yield prepared

    def _output_vector_items(self) -> Iterator[core_config.ResolvedOutputEntry]:
        """
        Yield the resolved entry for vector outputs only.
        Mirrors _processing_items/_context_items for consistency.

        Iterates `output_entries` rather than `output_catalog`, since per-output
        settings (like `extraction_method`) have no place in the catalog's
        tag-to-path layout.
        """
        for entry in self.output_entries:
            if entry.data_type is not core_config.DataType.VECTOR:
                continue
            yield entry

    def prepare_input_data(self):
        """
        Prepare all inputs for partitioning.

        - Processing inputs: counted and tagged with a `PARTITION_FIELD`.
        - Context inputs: either counted directly (if search_distance <= 0)
        or filtered to features within the search radius of processing inputs.
        """
        for prepared in self._processing_items():
            self._prepare_processing_input(prepared=prepared)

        for prepared in self._context_items():
            self._prepare_context_input(prepared=prepared)

    def _prepare_processing_input(self, prepared: PreparedInput) -> None:
        """
        Initialize a processing input for partitioning.

        - Records the feature count.
        - Deletes `PARTITION_FIELD` if it exists, then creates the field.
        - This helper field is required during partitioning and will later
        be removed by `cleanup_partition_fields` to restore clean inputs.
        """
        input_path = prepared.active_path
        prepared.count = file_utilities.count_objects(input_layer=input_path)

        existing_fields = {field.name for field in arcpy.ListFields(input_path)}
        if self.PARTITION_FIELD in existing_fields:
            arcpy.management.DeleteField(
                in_table=input_path,
                drop_field=self.PARTITION_FIELD,
            )
        arcpy.AddField_management(
            in_table=input_path,
            field_name=self.PARTITION_FIELD,
            field_type="LONG",
        )

    def _prepare_context_input(self, prepared: PreparedInput) -> None:
        """
        Initialize a context input for partitioning.

        - If `search_distance <= 0`: keeps the raw input active and records its count.
        - Otherwise:
            * Creates a filtered copy of the input,
            * Selects features within `search_distance` of each processing input,
            * Appends them into the filtered dataset,
            * Makes the filtered dataset the active path and records how much it saved.
        """
        input_path = prepared.source_path
        prepared.pre_optimization_count = file_utilities.count_objects(
            input_layer=input_path
        )
        if self.search_distance <= 0:
            prepared.count = file_utilities.count_objects(input_layer=input_path)
            return

        processing_inputs = list(self._processing_items())

        filtered_context_path = (
            self.work_file_manager_persistent_files.generate_partition_path(
                object_name=prepared.object, tag="input_contex_filtered"
            )
        )

        file_utilities.create_feature_class(
            template_feature=input_path, new_feature=filtered_context_path
        )
        for processing_input in processing_inputs:
            memory_layer = self.work_file_manager_temp_files.generate_partition_path(
                object_name=prepared.object,
                tag=f"near_{processing_input.object}_selection",
            )
            custom_arcpy.select_location_and_make_feature_layer(
                input_layer=input_path,
                overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
                select_features=processing_input.active_path,
                output_name=memory_layer,
                search_distance=self.search_distance,
            )

            arcpy.management.Append(
                inputs=memory_layer,
                target=filtered_context_path,
                schema_type="NO_TEST",
            )
            self.work_file_manager_temp_files.delete_created_files()

        prepared.active_path = filtered_context_path
        prepared.count = file_utilities.count_objects(input_layer=filtered_context_path)
        prepared.reduced_count = prepared.pre_optimization_count - prepared.count

    def select_partition_feature(self, iteration_partition, object_id):
        """
        Selects partition feature based on OBJECTID.
        """
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.partition_feature,
            expression=f"{self.object_id_field} = {object_id}",
            output_name=iteration_partition,
        )

    def process_single_processing_input(
        self,
        object_key: str,
        input_path: str,
        iteration_partition: str,
        partition_id: int,
    ) -> bool:
        """
        Select and prepare a single processing input for one partition.

        How:
        - Selects features whose center lies within the partition.
        - Marks them with `PARTITION_FIELD = 1` and copies to an iteration-scoped dataset.
        - If `search_distance > 0`, also selects nearby features:
            * Includes features within the search radius but not center-in,
            * Marks them with `PARTITION_FIELD = 0`,
            * Appends them to the same iteration dataset.
        - Updates `iteration_paths` and `iteration_stats` with path and feature count.
        - Creates a dummy feature if no features are found.

        Returns:
            bool: True if the partition contains any features for this object,
            False otherwise.
        """
        self.iteration_paths.setdefault(object_key, {})
        stats = self.iteration_stats.setdefault(object_key, PartitionStats())

        selection_memory_path = (
            self.work_file_manager_temp_files.generate_partition_path(
                object_name=object_key,
                partition_id=partition_id,
                suffix="centerpoint_in_partition",
            )
        )

        custom_arcpy.select_location_and_make_feature_layer(
            input_layer=input_path,
            overlap_type=custom_arcpy.OverlapType.HAVE_THEIR_CENTER_IN,
            select_features=iteration_partition,
            output_name=selection_memory_path,
        )

        center_count = file_utilities.count_objects(selection_memory_path)

        if center_count == 0:
            stats.count = center_count
            stats.vertex_count = 0
            self.update_empty_object_tag_with_dummy_file(
                object_key=object_key, tag=self.INPUT_KEY
            )
            self.work_file_manager_temp_files.delete_created_files()
            return False

        arcpy.CalculateField_management(
            in_table=selection_memory_path, field=self.PARTITION_FIELD, expression="1"
        )

        output_path = self.work_file_manager_iteration_files.generate_partition_path(
            object_name=object_key,
            partition_id=partition_id,
            suffix="iteration_selection",
        )

        file_utilities.create_feature_class(
            template_feature=selection_memory_path, new_feature=output_path
        )
        arcpy.management.Append(
            inputs=selection_memory_path,
            target=output_path,
            schema_type="NO_TEST",
        )

        if self.search_distance > 0:
            nearby_selection = (
                self.work_file_manager_temp_files.generate_partition_path(
                    object_name=object_key,
                    partition_id=partition_id,
                    suffix="near_partiton_selection",
                )
            )

            custom_arcpy.select_location_and_make_feature_layer(
                input_layer=input_path,
                overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
                select_features=iteration_partition,
                output_name=nearby_selection,
                selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
                search_distance=self.search_distance,
            )

            arcpy.management.SelectLayerByLocation(
                in_layer=nearby_selection,
                overlap_type="HAVE_THEIR_CENTER_IN",
                select_features=iteration_partition,
                selection_type="REMOVE_FROM_SELECTION",
            )

            arcpy.CalculateField_management(
                in_table=nearby_selection,
                field=self.PARTITION_FIELD,
                expression="0",
            )
            arcpy.management.Append(
                inputs=nearby_selection,
                target=output_path,
                schema_type="NO_TEST",
            )

        stats.count = (
            file_utilities.count_objects(input_layer=output_path)
            if self.search_distance > 0
            else center_count
        )
        stats.vertex_count = file_utilities.count_vertices(output_path)
        self.iteration_paths[object_key][self.INPUT_KEY] = output_path
        self.work_file_manager_temp_files.delete_created_files()
        return True

    def process_all_processing_inputs(
        self,
        iteration_partition: str,
        partition_id: int,
    ) -> bool:
        has_inputs = False
        """
        Process all configured processing inputs for one partition.
    
        - Calls `process_single_processing_input` for each processing object.
        - Aggregates results to track whether any inputs produced features.
    
        Returns:
            bool: True if at least one processing input had features,
            False if all were empty.
        """

        for prepared in self._processing_items():
            result = self.process_single_processing_input(
                object_key=prepared.object,
                input_path=prepared.active_path,
                iteration_partition=iteration_partition,
                partition_id=partition_id,
            )

            has_inputs = has_inputs or result

        return has_inputs

    def process_single_context_input(
        self,
        object_key: str,
        input_path: str,
        iteration_partition: str,
        partition_id: int,
    ) -> None:
        """
        Select and prepare a single context input for one partition.

        How:
        - Selects features within `search_distance` of the partition geometry.
        - Writes the selection to an iteration-scoped dataset.
        - Updates `iteration_paths` and `iteration_stats` with path and feature count.
        - If no features are found, assigns a dummy feature path.

        Side effects:
            Creates/deletes temporary feature classes and updates the iteration catalogs.
        """
        self.iteration_paths.setdefault(object_key, {})
        stats = self.iteration_stats.setdefault(object_key, PartitionStats())
        output_path = self.work_file_manager_iteration_files.generate_partition_path(
            object_name=object_key,
            partition_id=partition_id,
            suffix="iteration_selection",
        )

        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=input_path,
            overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
            select_features=iteration_partition,
            output_name=output_path,
            selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
            search_distance=self.search_distance,
        )

        count = file_utilities.count_objects(output_path)

        if count > 0:
            self.iteration_paths[object_key][self.INPUT_KEY] = output_path
            stats.vertex_count = file_utilities.count_vertices(output_path)
        else:
            self.update_empty_object_tag_with_dummy_file(
                object_key=object_key, tag=self.INPUT_KEY
            )
            stats.vertex_count = 0
        stats.count = count

    def process_all_context_inputs(
        self,
        iteration_partition: str,
        partition_id: int,
    ) -> None:
        """
        Process all configured context inputs for one partition.

        Calls `process_single_context_input` for each context object
        and records results in the iteration catalogs.
        """
        for prepared in self._context_items():
            self.process_single_context_input(
                object_key=prepared.object,
                input_path=prepared.active_path,
                iteration_partition=iteration_partition,
                partition_id=partition_id,
            )

    def _collect_single_processing_input_metadata(
        self, object_key: str, partition_id: int
    ) -> None:
        """
        Compute and store processing/context split metadata for one processing input.

        Uses PARTITION_FIELD (1 = processing, 0 = context) to make two attribute
        selections on the iteration path, then counts objects and vertices for each.
        Results are written into iteration_stats for the given object_key.

        A partition where the object had no features keeps the zeroed defaults.
        """
        stats = self.iteration_stats.get(object_key)

        if stats is None or stats.count == 0:
            return

        iteration_path = self.iteration_paths[object_key][self.INPUT_KEY]
        total_count = stats.count

        processing_layer = f"partition_{partition_id}_{object_key}_processing_lyr"
        context_layer = f"partition_{partition_id}_{object_key}_context_lyr"

        custom_arcpy.select_attribute_and_make_feature_layer(
            input_layer=iteration_path,
            expression=f"{self.PARTITION_FIELD} = 1",
            output_name=processing_layer,
        )
        custom_arcpy.select_attribute_and_make_feature_layer(
            input_layer=iteration_path,
            expression=f"{self.PARTITION_FIELD} = 0",
            output_name=context_layer,
        )

        processing_count = file_utilities.count_objects(processing_layer)
        context_count = file_utilities.count_objects(context_layer)
        processing_vertices = file_utilities.count_vertices(processing_layer)
        context_vertices = file_utilities.count_vertices(context_layer)

        arcpy.Delete_management(processing_layer)
        arcpy.Delete_management(context_layer)

        stats.processing_object_count = processing_count
        stats.context_object_count = context_count
        stats.processing_vertex_count = processing_vertices
        stats.context_vertex_count = context_vertices
        total_vertices = processing_vertices + context_vertices

        stats.processing_object_percentage = round(
            processing_count / total_count * 100, 2
        )
        stats.context_object_percentage = round(context_count / total_count * 100, 2)
        stats.processing_vertex_percentage = (
            round(processing_vertices / total_vertices * 100, 2)
            if total_vertices > 0
            else 0
        )
        stats.context_vertex_percentage = (
            round(context_vertices / total_vertices * 100, 2)
            if total_vertices > 0
            else 0
        )

    def _collect_processing_input_metadata(self, partition_id: int) -> None:
        """
        Collect processing/context split metadata for all processing inputs.

        Calls _collect_single_processing_input_metadata for each processing object
        in the iteration catalogs. Mirrors the process_single_X / process_all_X pattern.
        """
        for prepared in self._processing_items():
            self._collect_single_processing_input_metadata(
                object_key=prepared.object,
                partition_id=partition_id,
            )

    def _initialize_overview_catalog(self) -> None:
        """
        Set up the overview_catalog structure and accumulators before the partition loop.

        Builds one entry per processing input (with per-tag output sub-entries) and
        top-level sections for run_config, partition_summary, and runtime.
        Accumulators for averages are kept as instance variables, not in the JSON structure.
        """
        processing_inputs = {
            prepared.object: ProcessingInputOverview(
                outputs={
                    entry.tag: OutputOverview()
                    for entry in self._output_vector_items()
                    if entry.object == prepared.object
                }
            )
            for prepared in self._processing_items()
        }

        self.overview_catalog = OverviewCatalog(
            run_config=RunConfigOverview(
                partition_method=self.partition_method,
                search_distance_meters=self.search_distance,
                search_distance_used=self.search_distance > 0,
                max_elements_per_partition=self.max_elements_per_partition,
                run_partition_optimization=self.run_partition_optimization,
                final_partition_feature_count=self.final_partition_feature_count,
                custom_partition_feature_used=self.use_custom_partition_feature,
            ),
            partition_summary=PartitionSummary(
                total_partitions=self.max_partition_count
            ),
            runtime=RuntimeOverview(start_time=datetime.now().isoformat()),
            processing_inputs=processing_inputs,
        )

        self._overview_partition_loads = []
        self._overview_pct_accumulators = {
            object_key: PercentageAccumulator() for object_key in processing_inputs
        }

    def _update_partition_load_overview(self, partition_id: int) -> None:
        """Track partition load and update highest load in partition_summary."""
        partition_summary = self.overview_catalog.partition_summary
        partition_summary.partitions_with_inputs += 1

        current_load = self._total_partition_load()
        self._overview_partition_loads.append(current_load)
        if current_load > partition_summary.highest_load_value:
            partition_summary.highest_load_value = current_load
            partition_summary.partition_id_highest_load = partition_id

    def _update_processing_inputs_overview(self, partition_id: int) -> None:
        """Accumulate per-object counts, max/min stats, percentage accumulators,
        and processing-input context totals from the current iteration_stats."""
        context_summary = self.overview_catalog.context_inputs_summary

        for prepared in self._processing_items():
            object_key = prepared.object
            stats = self.iteration_stats.get(object_key)
            if stats is None or stats.count == 0:
                continue

            obj_overview = self.overview_catalog.processing_inputs[object_key]
            obj_overview.partitions_with_object_present += 1
            obj_overview.input_object_count += stats.processing_object_count
            obj_overview.input_vertex_count += stats.processing_vertex_count

            acc = self._overview_pct_accumulators[object_key]
            acc.processing_object_percentage += stats.processing_object_percentage
            acc.context_object_percentage += stats.context_object_percentage
            acc.processing_vertex_percentage += stats.processing_vertex_percentage
            acc.context_vertex_percentage += stats.context_vertex_percentage

            obj_overview.processing_object_count.observe(
                stats.processing_object_count, partition_id
            )
            obj_overview.processing_vertex_count.observe(
                stats.processing_vertex_count, partition_id
            )

            if self.search_distance > 0:
                obj_overview.processing_object_percentage.observe(
                    stats.processing_object_percentage, partition_id
                )
                obj_overview.context_object_percentage.observe(
                    stats.context_object_percentage, partition_id
                )

            context_summary.total_processing_input_context_objects += (
                stats.context_object_count
            )
            context_summary.total_processing_input_context_vertices += (
                stats.context_vertex_count
            )

    def _update_context_inputs_overview(self) -> None:
        """Accumulate object and vertex totals for context input datasets
        from the current iteration_stats."""
        context_summary = self.overview_catalog.context_inputs_summary
        for prepared in self._context_items():
            stats = self.iteration_stats.get(prepared.object)
            if stats is None:
                continue
            context_summary.total_processed_objects += stats.count
            context_summary.total_processed_vertices += stats.vertex_count

    def _update_overview_from_partition(self, partition_id: int) -> None:
        """
        Accumulate all per-partition data from iteration_stats into overview_catalog.

        Called after _collect_processing_input_metadata so all metadata is populated.
        """
        self._update_partition_load_overview(partition_id)
        self._update_processing_inputs_overview(partition_id)
        self._update_context_inputs_overview()

    def _finalize_runtime_overview(self) -> None:
        """Set end_time and compute average iteration runtime."""
        runtime = self.overview_catalog.runtime
        runtime.end_time = datetime.now().isoformat()
        if self.iteration_times_with_input:
            runtime.average_iteration_runtime_seconds = round(
                sum(self.iteration_times_with_input)
                / len(self.iteration_times_with_input),
                3,
            )

    def _finalize_partition_summary_overview(self) -> None:
        """Compute average partition load."""
        if self._overview_partition_loads:
            self.overview_catalog.partition_summary.average_load = round(
                sum(self._overview_partition_loads)
                / len(self._overview_partition_loads),
                2,
            )

    def _finalize_context_inputs_overview(self) -> None:
        """Sum per-context-input reductions into total_objects_saved_by_optimization."""
        self.overview_catalog.context_inputs_summary.total_objects_saved_by_optimization = sum(
            prepared.reduced_count or 0 for prepared in self._context_items()
        )

    def _finalize_processing_inputs_overview(self) -> None:
        """Compute per-object averages and output diffs."""
        for object_key, obj_overview in self.overview_catalog.processing_inputs.items():
            n = obj_overview.partitions_with_object_present
            acc = self._overview_pct_accumulators.get(
                object_key, PercentageAccumulator()
            )

            obj_overview.avg_processing_object_percentage = (
                round(acc.processing_object_percentage / n, 2) if n > 0 else None
            )
            obj_overview.avg_context_object_percentage = (
                round(acc.context_object_percentage / n, 2) if n > 0 else None
            )
            obj_overview.avg_processing_vertex_percentage = (
                round(acc.processing_vertex_percentage / n, 2) if n > 0 else None
            )
            obj_overview.avg_context_vertex_percentage = (
                round(acc.context_vertex_percentage / n, 2) if n > 0 else None
            )

            input_obj = obj_overview.input_object_count
            input_vtx = obj_overview.input_vertex_count

            for tag_entry in obj_overview.outputs.values():
                out_obj = tag_entry.output_object_count
                out_vtx = tag_entry.output_vertex_count
                tag_entry.object_count_diff_absolute = out_obj - input_obj
                tag_entry.object_count_diff_percentage = (
                    round((out_obj - input_obj) / input_obj * 100, 2)
                    if input_obj > 0
                    else None
                )
                tag_entry.vertex_count_diff_absolute = out_vtx - input_vtx
                tag_entry.vertex_count_diff_percentage = (
                    round((out_vtx - input_vtx) / input_vtx * 100, 2)
                    if input_vtx > 0
                    else None
                )

    def _finalize_and_write_overview_catalog(self) -> None:
        """
        Compute all derived values and write overview.json to documentation_directory root.

        Called once at the end of the full run after all partitions are processed.
        """
        self._finalize_runtime_overview()
        self._finalize_partition_summary_overview()
        self._finalize_context_inputs_overview()
        self._finalize_processing_inputs_overview()
        self.write_documentation(name="overview", dict_data=self.overview_catalog)

    def track_iteration_time(self, object_id: int, inputs_present: bool) -> None:
        """
        Tracks runtime and estimates remaining time based on iterations with inputs.
        Prints current time, elapsed runtime, and estimated remaining runtime.
        """
        iteration_time = time.time() - self.iteration_start_time
        if inputs_present:
            self.iteration_times_with_input.append(iteration_time)
            runtime = self.overview_catalog.runtime
            if (
                runtime.max_iteration_runtime_seconds is None
                or iteration_time > runtime.max_iteration_runtime_seconds
            ):
                runtime.max_iteration_runtime_seconds = round(iteration_time, 3)
                runtime.max_iteration_runtime_partition_id = object_id
        else:
            self.overview_catalog.partition_summary.partitions_skipped += 1

        avg_runtime = (
            sum(self.iteration_times_with_input) / len(self.iteration_times_with_input)
            if self.iteration_times_with_input
            else 0
        )

        total_runtime = time.time() - self.total_start_time
        remaining_iterations = self.max_partition_count - object_id
        estimate_remaining = remaining_iterations * avg_runtime

        now_str = datetime.now().strftime("%d-%m %H:%M:%S")
        total_str = str(timedelta(seconds=int(total_runtime)))
        estimate_str = str(timedelta(seconds=int(estimate_remaining)))

        print(f"\n[{now_str}] " f"Runtime: {total_str} | " f"Remaining: {estimate_str}")

    def resolve_injected_io_for_methods(
        self,
        method_entries_config: core_config.MethodEntriesConfig,
        partition_id: int,
    ) -> core_config.MethodEntriesConfig:
        """
        Inject concrete paths into each method entry by resolving InjectIO objects.
        Returns a new MethodEntriesConfig with fully resolved params.
        """
        resolved_configs = []

        for entry in method_entries_config.entries:
            if isinstance(entry, core_config.FuncMethodEntryConfig):
                resolved_params = self.resolve_param_injections(
                    method_config=copy.deepcopy(entry.params),
                    partition_id=partition_id,
                )
                resolved_configs.append(
                    core_config.FuncMethodEntryConfig(
                        func=entry.func, params=resolved_params
                    )
                )

            elif isinstance(entry, core_config.ClassMethodEntryConfig):
                resolved_init = (
                    self.resolve_param_injections(
                        copy.deepcopy(entry.init_params), partition_id
                    )
                    if entry.init_params is not None
                    else None
                )
                resolved_method = (
                    self.resolve_param_injections(
                        copy.deepcopy(entry.method_params), partition_id
                    )
                    if entry.method_params is not None
                    else None
                )
                resolved_configs.append(
                    core_config.ClassMethodEntryConfig(
                        class_=entry.class_,
                        method=entry.method,
                        init_params=resolved_init,
                        method_params=resolved_method,
                    )
                )
            else:
                raise TypeError(f"Unsupported method entry type: {type(entry)}")

        return core_config.MethodEntriesConfig(entries=resolved_configs)

    def resolve_param_injections(self, method_config: Any, partition_id: int) -> Any:
        """
        Recursively resolve InjectIO instances in any nested structure.
        Supports dicts, lists, tuples, and sets.
        """
        if isinstance(method_config, core_config.InjectIO):
            return self.resolve_inject_entry(
                inject=method_config, partition_id=partition_id
            )

        elif is_dataclass(method_config) and not isinstance(method_config, type):
            resolved_values = {
                f.name: self.resolve_param_injections(
                    getattr(method_config, f.name), partition_id
                )
                for f in fields(method_config)
            }
            return replace(method_config, **resolved_values)

        elif isinstance(method_config, dict):
            return {
                key: self.resolve_param_injections(value, partition_id)
                for key, value in method_config.items()
            }

        elif isinstance(method_config, list):
            return [
                self.resolve_param_injections(item, partition_id)
                for item in method_config
            ]

        elif isinstance(method_config, tuple):
            return tuple(
                self.resolve_param_injections(item, partition_id)
                for item in method_config
            )

        elif isinstance(method_config, set):
            return {
                self.resolve_param_injections(item, partition_id)
                for item in method_config
            }

        else:
            return method_config

    def resolve_inject_entry(
        self, inject: core_config.InjectIO, partition_id: int
    ) -> str:
        """Resolve a single `InjectIO` placeholder to a concrete path for this partition."""
        if inject.tag == self.INPUT_KEY and inject.object in self.input_catalog:
            return self.iteration_paths[inject.object][inject.tag]

        path = self.work_file_manager_resolved_files.generate_partition_path(
            object_name=inject.object,
            tag=inject.tag,
            partition_id=partition_id,
        )
        self.iteration_paths.setdefault(inject.object, {})[inject.tag] = path

        return path

    def _format_exception(self, exc: BaseException) -> Dict[str, Any]:
        """
        Return a JSON-safe dict with exception type, message, and full formatted traceback.
        """
        tb = traceback.TracebackException.from_exception(exc)
        return {
            "type": getattr(type(exc), "__name__", str(type(exc))),
            "message": str(exc),
            "traceback": list(tb.format()),
        }

    def execute_injected_methods(
        self,
        method_entries_config: core_config.MethodEntriesConfig,
        partition_id: int,
        attempt: int,
    ) -> Dict[str, Any]:
        """
        Execute a fully *resolved* set of injected methods for one partition/attempt.

        For each entry:
        - If it's a class method: split kwargs into constructor vs. method args,
            instantiate the class, then call the method.
        - If it's a function: call it with the provided kwargs.

        Logging:
        - Builds an in-memory `execution_log` with:
            - per-entry raw params (JSON-safe), split class/method params (for classes),
            - status ("ok" or "error"), and full exception info (type/message/traceback) on error.
        - On any exception, stores the partial log in `self._last_injected_log` and re-raises;
            the retry layer is responsible for persisting per-attempt error logs.

        Args:
            method_entries_config: The *resolved* (no remaining InjectIO) method entries.
            partition_id: Current partition identifier (for log context).
            attempt: 1-based attempt number (for log context).

        Returns:
            Dict[str, Any]: The complete per-attempt execution log when all entries succeed.

        Raises:
            Exception: Re-raises the first failure after recording it in `self._last_injected_log`.
        """
        execution_log: Dict[str, Any] = {
            "partition_id": partition_id,
            "stage": "execute",
            "attempt": attempt,
            "entries": [],
        }

        for index, entry in enumerate(method_entries_config.entries):
            record: Dict[str, Any] = {"index": index}
            try:
                if isinstance(entry, core_config.ClassMethodEntryConfig):
                    cls = entry.class_

                    # Resolve method (string or callable)
                    if isinstance(entry.method, str):
                        method_callable = getattr(cls, entry.method)
                        method_name = entry.method
                    else:
                        method_callable = entry.method
                        method_name = getattr(
                            method_callable, "__name__", str(method_callable)
                        )

                    # Enforce positional dataclass-only for ctor + method
                    ctor_args = param_utils.ensure_dataclass_list(entry.init_params)
                    call_args = param_utils.ensure_dataclass_list(entry.method_params)

                    param_utils.validate_positional_arity(cls.__init__, len(ctor_args))
                    param_utils.validate_positional_arity(
                        method_callable, len(call_args)
                    )

                    record.update(
                        {
                            "type": "class",
                            "class": cls.__name__,
                            "method": method_name,
                            "init_params": param_utils.payload_log(
                                entry.init_params, self._jsonify
                            ),
                            "method_params": param_utils.payload_log(
                                entry.method_params, self._jsonify
                            ),
                            "init_positional": len(ctor_args),
                            "call_positional": len(call_args),
                        }
                    )

                    instance = cls(*ctor_args)
                    method_callable(instance, *call_args)

                    record["status"] = "ok"
                    execution_log["entries"].append(record)

                elif isinstance(entry, core_config.FuncMethodEntryConfig):
                    func = entry.func
                    func_args = param_utils.ensure_dataclass_list(entry.params)
                    param_utils.validate_positional_arity(func, len(func_args))

                    record.update(
                        {
                            "type": "function",
                            "function": func.__name__,
                            "func_params": param_utils.payload_log(
                                entry.params, self._jsonify
                            ),
                            "func_positional": len(func_args),
                        }
                    )

                    func(*func_args)

                    record["status"] = "ok"
                    execution_log["entries"].append(record)

                else:
                    raise TypeError(f"Unsupported method entry type: {type(entry)}")

            except Exception as e:
                record["status"] = "error"
                record["error"] = str(e)
                record["exception"] = self._format_exception(e)
                execution_log["entries"].append(record)
                self._last_injected_log = self._jsonify(execution_log)
                raise

        self._last_injected_log = self._jsonify(execution_log)
        return execution_log

    def execute_injected_methods_with_retry(self, partition_id: int):
        """
        Execute injected methods for a partition with retries and structured logging.

        Flow per attempt:
        1) Reset `self._last_injected_log` to ensure clean state.
        2) Resolve InjectIO placeholders to concrete, partition-scoped paths.
            - If resolution fails, write an error attempt log with stage="resolve".
        3) Run `execute_injected_methods(...)`.
            - On success: write `method_logs/method_log_{partition_id}.json` and return.
            - On failure: write `error_logs/error_{partition_id}/attempt_{n}_error.json`,
            increment `self.error_log[partition_id]`, and retry until max_retries.

        Args:
            partition_id: Current partition identifier.

        Raises:
            Exception: Re-raises the last error after exhausting retries; also writes
            `error_log.json` and the final per-attempt error snapshot.
        """
        max_retries = 50

        for attempt in range(1, max_retries + 1):
            self._last_injected_log = None

            try:
                self.work_file_manager_resolved_files.delete_created_files()

                resolved = self.resolve_injected_io_for_methods(
                    method_entries_config=self.list_of_methods,
                    partition_id=partition_id,
                )
                execution_log = self.execute_injected_methods(
                    method_entries_config=resolved,
                    partition_id=partition_id,
                    attempt=attempt,
                )

                self.write_documentation(
                    name=f"method_log_{partition_id}",
                    dict_data=execution_log,
                    sub_dir=os.path.join("method_logs"),
                )
                return

            except Exception as e:
                attempt_log = getattr(self, "_last_injected_log", None)
                if attempt_log is None:
                    attempt_log = {
                        "partition_id": partition_id,
                        "attempt": attempt,
                        "stage": "resolve",
                        "entries": [],
                        "exception": self._format_exception(e),
                    }

                self.write_documentation(
                    name=f"attempt_{attempt}_error",
                    dict_data=attempt_log,
                    sub_dir=os.path.join("error_logs", f"error_{partition_id}"),
                )

                error_message = str(e)
                print(f"Attempt {attempt} failed with error: {error_message}")

                if partition_id not in self.error_log:
                    self.error_log[partition_id] = {
                        "Number of retries": 0,
                        "Error Messages": {},
                    }

                self.error_log[partition_id]["Number of retries"] += 1
                self.error_log[partition_id]["Error Messages"][attempt] = error_message

                if attempt == max_retries:
                    print("Max retries reached.")
                    self.write_documentation(name="error_log", dict_data=self.error_log)

                    raise

    def _append_iteration_partition_to_output(
        self, iteration_partition: str, partition_id: int
    ) -> None:
        """
        Append the current partition geometry to the accumulated partition features output.

        Adds a partition_id field to the iteration_partition feature, then appends it
        to self.partition_features_all (creating it on the first call).
        """
        arcpy.AddField_management(
            in_table=iteration_partition,
            field_name=self.PARTITION_ID_FIELD,
            field_type="LONG",
        )
        arcpy.CalculateField_management(
            in_table=iteration_partition,
            field=self.PARTITION_ID_FIELD,
            expression=str(partition_id),
        )
        if not arcpy.Exists(self.partition_features_all):
            arcpy.management.CopyFeatures(
                in_features=iteration_partition,
                out_feature_class=self.partition_features_all,
            )
        else:
            arcpy.management.Append(
                inputs=iteration_partition,
                target=self.partition_features_all,
                schema_type="NO_TEST",
            )

    def _extract_partition_output(
        self,
        object_key: str,
        tag: str,
        iteration_path: Any,
        iteration_partition: str,
        partition_id: int,
        extraction_method: core_config.OutputExtractionMethod,
    ) -> str:
        """
        Produce the per-partition slice of an iteration output to append to the final output.

        The slice is built according to the output's own `extraction_method`:
        - "selection": select whole features owned by this partition (PARTITION_FIELD = 1).
        - "clip": clip the iteration output by the partition polygon (PairwiseClip). The full
          iteration output is clipped; this does not depend on PARTITION_FIELD. Correctness
          relies on the partition polygons not overlapping: generated cartographic partitions
          satisfy this, a `custom_partition_feature` is only validated for geometry type.

        Returns the path to a temporary (work-managed) feature holding the slice. The caller
        is responsible for deleting temp files via the temp work file manager.
        """
        if extraction_method is core_config.OutputExtractionMethod.CLIP:
            extracted_path = self.work_file_manager_temp_files.generate_partition_path(
                object_name=object_key,
                tag=tag,
                partition_id=partition_id,
                suffix="partition_final_output_append_clip",
            )
            arcpy.analysis.PairwiseClip(
                in_features=iteration_path,
                clip_features=iteration_partition,
                out_feature_class=extracted_path,
            )
            return extracted_path

        extracted_path = self.work_file_manager_temp_files.generate_partition_path(
            object_name=object_key,
            tag=tag,
            partition_id=partition_id,
            suffix="partition_final_output_append_selection",
        )
        custom_arcpy.select_attribute_and_make_feature_layer(
            input_layer=iteration_path,
            expression=f"{self.PARTITION_FIELD} = 1",
            output_name=extracted_path,
        )
        return extracted_path

    def _extract_and_append_partition_output(
        self,
        object_key: str,
        tag: str,
        iteration_path: Any,
        iteration_partition: str,
        final_output_path: str,
        partition_id: int,
        extraction_method: core_config.OutputExtractionMethod,
    ) -> None:
        """
        Checks whether the intermediate result for the given object and tag is valid,
        extracts this partition's slice (selection or clip), and appends it to the final
        output if so.

        Args:
            object_key (str): The object identifier (e.g. 'building_polygons').
            tag (str): The processing tag (e.g. 'some_logic').
            iteration_path (Any): The iteration output for this object/tag.
            iteration_partition (str): The current partition polygon (used by clip).
            final_output_path (str): Destination output path.
            partition_id (int): Current partition identifier.
            extraction_method: How to slice this output (SELECTION or CLIP).
        """
        if not file_utilities.feature_has_rows(feature=iteration_path):
            return

        extracted_path = self._extract_partition_output(
            object_key=object_key,
            tag=tag,
            iteration_path=iteration_path,
            iteration_partition=iteration_partition,
            partition_id=partition_id,
            extraction_method=extraction_method,
        )

        try:
            if not file_utilities.feature_has_rows(feature=extracted_path):
                return

            obj_overview = self.overview_catalog.processing_inputs.get(object_key)
            output_entry = obj_overview.outputs.get(tag) if obj_overview else None
            if output_entry is not None:
                output_entry.output_object_count += file_utilities.count_objects(
                    extracted_path
                )
                output_entry.output_vertex_count += file_utilities.count_vertices(
                    extracted_path
                )

            if not arcpy.Exists(final_output_path):
                arcpy.management.CopyFeatures(
                    in_features=extracted_path,
                    out_feature_class=final_output_path,
                )
                print(f"Created final output for {object_key}:{tag}")
            else:
                arcpy.management.Append(
                    inputs=extracted_path,
                    target=final_output_path,
                    schema_type="NO_TEST",
                )
                print(f"Appended to final output for {object_key}:{tag}")

        finally:
            self.work_file_manager_temp_files.delete_created_files()

    def append_iteration_outputs_to_final(
        self, partition_id: int, iteration_partition: str
    ) -> None:
        """
        Appends all valid outputs for the current iteration to their final output paths.

        Skips any objects marked as dummy and ensures only non-empty, valid inputs are appended.
        """
        for entry in self._output_vector_items():
            object_paths = self.iteration_paths.get(entry.object)
            if not object_paths:
                continue

            self._extract_and_append_partition_output(
                object_key=entry.object,
                tag=entry.tag,
                iteration_path=object_paths.get(entry.tag),
                iteration_partition=iteration_partition,
                final_output_path=entry.path,
                partition_id=partition_id,
                extraction_method=entry.extraction_method,
            )

    def cleanup_helper_fields(self) -> None:
        """
        Delete the helper field `PARTITION_FIELD` from:
        - All final output feature classes.
        - All processing input feature classes (since it was injected for partitioning).

        Ensures that only clean data structures remain after the workflow.
        """
        fields_to_delete = [self.PARTITION_FIELD]

        for object_key, tag_dict in self.output_catalog.items():
            for tag, final_output_path in tag_dict.items():
                print(f"Cleaning fields in: {final_output_path}")
                file_utilities.delete_fields_if_exist(
                    final_output_path, fields_to_delete
                )

        for prepared in self._processing_items():
            print(f"Cleaning fields in processing input: {prepared.active_path}")
            file_utilities.delete_fields_if_exist(
                prepared.active_path, fields_to_delete
            )

    def _reset_iteration_state(self, partition_id: int) -> None:
        print(
            f"\nProcessing Partition: {partition_id} out of {self.max_partition_count}"
        )
        self.iteration_start_time = time.time()
        self._reset_iteration_catalogs()

    def partition_iteration(self):
        """
        Process every cartographic partition end-to-end.

        Workflow (per partition):
        1) Reset iteration state and select the partition geometry.
        2) Select processing inputs (center-in; optionally add near-by features).
            - If no processing features are present, skip this partition.
        3) Select context inputs within the configured search radius.
        4) Execute injected methods with retry and structured logging.
        5) Persist the iteration catalog and append valid outputs to final outputs.

        Raises:
        - Propagates any unhandled exception from injected methods after retries are exhausted.
        """

        self.update_max_partition_count()
        self.work_file_manager_iteration_files.delete_created_files()
        self.work_file_manager_temp_files.delete_created_files()
        self._initialize_overview_catalog()
        file_utilities.delete_feature(self.partition_features_all)

        for partition_id in range(1, self.max_partition_count + 1):
            self._reset_iteration_state(partition_id=partition_id)

            iteration_partition = (
                self.work_file_manager_iteration_files.generate_partition_path(
                    object_name="partition_feature_iteration_selection",
                    partition_id=partition_id,
                )
            )
            self.select_partition_feature(
                iteration_partition=iteration_partition, object_id=partition_id
            )

            inputs_present_in_partition = False

            try:
                self._append_iteration_partition_to_output(
                    iteration_partition=iteration_partition, partition_id=partition_id
                )
                inputs_present_in_partition = self.process_all_processing_inputs(
                    iteration_partition=iteration_partition,
                    partition_id=partition_id,
                )
                if not inputs_present_in_partition:
                    continue

                self.process_all_context_inputs(
                    iteration_partition=iteration_partition, partition_id=partition_id
                )

                self._collect_processing_input_metadata(partition_id=partition_id)
                self._update_overview_from_partition(partition_id=partition_id)

                self.execute_injected_methods_with_retry(partition_id=partition_id)
                self.write_documentation(
                    name=f"catalog_{partition_id}",
                    dict_data=self._iteration_catalog_snapshot(),
                    sub_dir="iteration_catalog",
                )
                self.append_iteration_outputs_to_final(
                    partition_id=partition_id,
                    iteration_partition=iteration_partition,
                )

            finally:
                self.work_file_manager_iteration_files.delete_created_files()
                self.work_file_manager_resolved_files.delete_created_files()
                self.track_iteration_time(partition_id, inputs_present_in_partition)

    @timing_decorator
    def run(self):
        """
        Orchestrate the full pipeline: preparation → partitioning → iteration → cleanup.

        Steps:
        1) Reset the documentation directory (with safety checks) and write `output_catalog.json`.
        2) Data preparation:
            - Optionally delete existing final outputs.
            - Prepare processing and context inputs (add PARTITION_FIELD, pre-filter context).
            - Create per-object dummy features.
            - Write `input_catalog.json`.
        3) Partitioning:
            - Determine feature count (optimize if enabled) and create cartographic partitions.
        4) Iteration:
            - Call `partition_iteration()` to process all partitions, execute injected methods,
            and append per-partition results to final outputs.
        5) Cleanup & logs:
            - Remove helper fields from final outputs (e.g., PARTITION_FIELD).
            - Delete persistent temp files.
            - Write aggregated `error_log.json`.
        """
        self.total_start_time = time.time()
        self._reset_documentation_dir()
        self.write_documentation(name="output_catalog", dict_data=self.output_catalog)

        print("\nStarting Data Preparation...")
        self.delete_final_outputs()
        self.prepare_input_data()
        self.create_dummy_features()
        self.write_documentation(name="input_catalog", dict_data=self.input_catalog)

        if self.use_custom_partition_feature:
            print("\nUsing custom partition feature; skipping partition creation...")
        else:
            print("\nCreating Cartographic Partitions...")
            self.final_partition_feature_count = (
                self._find_partition_size()
                if self.run_partition_optimization
                else int(self.max_elements_per_partition)
            )
            self._create_cartographic_partitions(
                element_limit=self.final_partition_feature_count
            )

        print("\nStarting on Partition Iteration...")
        self.partition_iteration()
        self._finalize_and_write_overview_catalog()

        self.cleanup_helper_fields()
        self.work_file_manager_persistent_files.delete_created_files()
        self.write_documentation(name="error_log", dict_data=self.error_log)


if __name__ == "__main__":
    environment_setup.main()
