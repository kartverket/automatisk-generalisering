import os
import shutil
import arcpy
from typing import Dict, Literal, List, Any, Optional, Tuple, Iterator
import time
import traceback
import inspect
from datetime import datetime
import pprint
import copy
from dataclasses import replace, fields, is_dataclass, asdict
from pathlib import Path
from datetime import timedelta

from composition_configs import core_config
from composition_configs import type_defs
from custom_tools.general_tools import param_utils
from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy, file_utilities
from custom_tools.decorators.timing_decorator import timing_decorator

from file_manager.work_file_manager import PartitionWorkFileManager


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
      - `input_catalog`: per *object* (dataset name) stores metadata and the global input
        paths; populated from `PartitionIOConfig`.
      - `output_catalog`: per object stores final output paths; populated from
        `PartitionIOConfig`.
      - `iteration_catalog`: per partition, per object, stores iteration-specific paths
        (e.g., the selected subset path, produced outputs) and counts.

    The following keys are used inside catalogs:
      - `INPUT_TYPE_KEY` / `DATA_TYPE_KEY`: metadata about each object’s role and data type.
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
        `iteration_catalog[obj][some_tag]`. Your injected method is expected to write to it.
    - You may introduce **new tags for an existing object** (e.g., `"buffer"`, `"cleaned"`)
        or even **new objects** via `InjectIO(new_object, new_tag)`. The iterator will allocate
        paths and track them in `iteration_catalog` as those tags/objects appear in params.

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

    INPUT_TYPE_KEY = "input_type"
    DATA_TYPE_KEY = "data_type"
    INPUT_KEY = "input"
    DUMMY = "dummy"
    COUNT = "count"
    PRE_OPTIMIZATION_COUNT = "pre_optimization_count"
    REDUCED_COUNT = "reduced_count"
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

        self.input_catalog: Dict[str, Dict[str, Any]] = {}
        self.output_catalog: Dict[str, Dict[str, Any]] = {}
        self.iteration_catalog: Dict[str, Dict[str, Any]] = {}

        input_entries_resolved = [
            core_config.ResolvedInputEntry(
                object=e.object,
                tag=e.tag,
                path=e.path,
                input_type=e.input_type.value,
                data_type=e.data_type.value,
            )
            for e in partition_io_config.input_config.entries
        ]

        output_entries_resolved = [
            core_config.ResolvedOutputEntry(
                object=e.object,
                tag=e.tag,
                path=e.path,
                data_type=e.data_type.value,
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
        self.partition_method: Literal["FEATURES", "VERTICES"] = (
            partition_iterator_run_config.partition_method.value
        )

        self.max_partition_count: int = 1
        self.final_partition_feature_count: int
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

        self.partition_feature = (
            self.work_file_manager_partition_feature.generate_partition_path(
                object_name="partition_feature",
            )
        )

        self.total_start_time: float
        self.iteration_times_with_input = []
        self.iteration_start_time: float
        self._last_injected_log = None

    def resolve_partition_input_config(
        self,
        entries: List[core_config.ResolvedInputEntry],
        target_dict: Dict[str, Dict[str, str]],
    ) -> None:
        """
        Add resolved input entries to `target_dict`.

        Ensures each object appears only once; raises on duplicates.
        """
        seen_objects = set()
        for entry in entries:
            if entry.object in seen_objects or entry.object in target_dict:
                raise ValueError(
                    f"Duplicate input object: '{entry.object}' is not supported"
                )
            entry_dict = target_dict.setdefault(entry.object, {})
            entry_dict[self.INPUT_TYPE_KEY] = entry.input_type
            entry_dict[self.DATA_TYPE_KEY] = entry.data_type
            entry_dict[entry.tag] = entry.path
            seen_objects.add(entry.object)

    def resolve_partition_output_config(
        self,
        entries: List[core_config.ResolvedOutputEntry],
        target_dict: Dict[str, Dict[str, str]],
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

    def _create_cartographic_partitions(self, element_limit: int) -> None:
        """
        Creates cartographic partitions based on the given element_limit.
        Overwrites any existing partition feature.
        """
        self.work_file_manager_partition_feature.delete_created_files()
        VALID_TAGS = {self.INPUT_KEY}

        in_features = [
            path
            for object_, tag_dict in self.input_catalog.items()
            for tag, path in tag_dict.items()
            if tag in VALID_TAGS and path is not None
        ]

        if not in_features:
            print("No input features available for creating partitions.")
            return

        arcpy.cartography.CreateCartographicPartitions(
            in_features=in_features,
            out_features=self.partition_feature,
            feature_count=element_limit,
            partition_method=self.partition_method,
        )
        print(f"Created partition feature: {self.partition_feature}")

    def _count_maximum_objects_in_partition(self) -> int:
        """
        What:
            Iterates over all partitions and determines the highest number of total processed
            input features (processing + context) found in any single partition.

        How:
            For each partition:
            - Select the partition geometry.
            - Run processing and context selection logic.
            - Track total processed objects.
            - Cleanup intermediate files.

        Returns:
            int: Maximum number of features found in a partition across all iterations.
        """
        self.update_max_partition_count()
        max_partition_load = 0

        for partition_id in range(1, self.max_partition_count + 1):
            self.iteration_catalog = {}
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

            total_objects = sum(
                row.get(self.COUNT, 0) for row in self.iteration_catalog.values()
            )
            max_partition_load = max(max_partition_load, total_objects)

            print(
                f"\nCounting objects for Partition: {partition_id}\n"
                f"Current total found: {total_objects}\n"
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

    def create_dummy_features(self, tag: str) -> None:
        """
        Create dummy feature classes for all objects that have a valid path
        under the given tag. Used to provide stable placeholder inputs when
        a partition produces no features.
        """
        for object_key, tag_dict in self.input_catalog.items():
            template_path = tag_dict.get(tag)
            if not template_path:
                continue

            dummy_feature_path = (
                self.work_file_manager_persistent_files.generate_partition_path(
                    object_name=object_key,
                    tag="dummy_feature",
                )
            )

            file_utilities.create_feature_class(
                template_feature=template_path, new_feature=dummy_feature_path
            )
            self.input_catalog[object_key][self.DUMMY] = dummy_feature_path

    def update_empty_object_tag_with_dummy_file(
        self, object_key: str, tag: str
    ) -> None:
        """
        Replaces the value for the given tag with the dummy path if available for the object_key.
        """
        tag_dict = self.input_catalog.get(object_key)
        if tag_dict is None:
            return

        dummy_path = tag_dict.get(self.DUMMY)
        if dummy_path is None:
            return

        if tag not in tag_dict:
            return

        self.iteration_catalog[object_key][tag] = dummy_path

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
        self, name: str, dict_data: dict, sub_dir: Optional[str] = None
    ) -> None:
        """
        Writes a JSON file to documentation_directory or its subdirectory.
        Ensures the destination directory exists.
        """
        base_dir = self.documentation_directory
        out_dir = os.path.join(base_dir, sub_dir) if sub_dir else base_dir
        os.makedirs(out_dir, exist_ok=True)

        json_path = os.path.join(out_dir, f"{name}.json")
        file_utilities.write_dict_to_json(path=json_path, dict_data=dict_data)

    def _jsonify(self, obj: Any) -> Any:
        """
        Make params JSON-safe:
        - dataclasses -> asdict
        - Path -> str
        - sets -> lists
        - dict/list/tuple -> recurse
        - otherwise return as-is
        """
        if is_dataclass(obj) and not isinstance(obj, type):
            return self._jsonify(asdict(obj))
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

    def _is_vector_of_type(
        self, tag_dict: dict, input_type: core_config.InputType
    ) -> bool:
        """
        Return True iff `tag_dict` represents a vector dataset of the given `input_type`
        (PROCESSING or CONTEXT) and has an active `INPUT_KEY` path.
        """
        return (
            tag_dict.get(self.INPUT_TYPE_KEY) == input_type.value
            and tag_dict.get(self.DATA_TYPE_KEY) == core_config.DataType.VECTOR.value
            and self.INPUT_KEY in tag_dict
        )

    def _processing_items(self) -> Iterator[Tuple[str, str]]:
        """
        Yield (object_key, input_path) for all PROCESSING vector inputs present in `input_catalog`.
        """
        for object_key, tag in self.input_catalog.items():
            if self._is_vector_of_type(
                tag_dict=tag, input_type=core_config.InputType.PROCESSING
            ):
                yield object_key, tag[self.INPUT_KEY]

    def _context_items(self) -> Iterator[Tuple[str, str]]:
        """
        Yield (object_key, input_path) for all CONTEXT vector inputs present in `input_catalog`.
        """
        for object_key, tag in self.input_catalog.items():
            if self._is_vector_of_type(
                tag_dict=tag, input_type=core_config.InputType.CONTEXT
            ):
                yield object_key, tag[self.INPUT_KEY]

    def _output_vector_items(self) -> Iterator[Tuple[str, str, str]]:
        """
        Yield (object_key, tag, final_output_path) for vector outputs only.
        Mirrors _processing_items/_context_items for consistency.
        """
        for object_key, tag_dict in self.output_catalog.items():
            if tag_dict.get(self.DATA_TYPE_KEY) != core_config.DataType.VECTOR.value:
                continue
            for tag, final_output_path in tag_dict.items():
                if tag == self.DATA_TYPE_KEY:
                    continue
                yield object_key, tag, final_output_path

    def prepare_input_data(self):
        """
        Prepare all inputs for partitioning.

        - Processing inputs: counted and tagged with a `PARTITION_FIELD`.
        - Context inputs: either counted directly (if search_distance <= 0)
        or filtered to features within the search radius of processing inputs.
        """
        for object_key, input_path in self._processing_items():
            self._prepare_processing_input(object_key=object_key, input_path=input_path)

        for object_key, input_path in self._context_items():
            self._prepare_context_input(object_key=object_key, input_path=input_path)

    def _prepare_processing_input(self, object_key: str, input_path: str) -> None:
        """
        Initialize a processing input for partitioning.

        - Registers the input path and feature count in `input_catalog`.
        - Deletes `PARTITION_FIELD` if it exists, then creates the field.
        - This helper field is required during partitioning and will later
        be removed by `cleanup_partition_fields` to restore clean inputs.
        """
        self.input_catalog[object_key][self.INPUT_KEY] = input_path
        self.input_catalog[object_key][self.COUNT] = file_utilities.count_objects(
            input_layer=input_path
        )

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

    def _prepare_context_input(self, object_key: str, input_path: str) -> None:
        """
        Initialize a context input for partitioning.

        - If `search_distance <= 0`: registers the raw input and its feature count.
        - Otherwise:
            * Creates a filtered copy of the input,
            * Selects features within `search_distance` of each processing input,
            * Appends them into the filtered dataset,
            * Registers the filtered dataset and its feature count in `input_catalog`.
        """
        self.input_catalog[object_key][self.PRE_OPTIMIZATION_COUNT] = (
            file_utilities.count_objects(input_layer=input_path)
        )
        if self.search_distance <= 0:
            self.input_catalog[object_key][self.INPUT_KEY] = input_path
            self.input_catalog[object_key][self.COUNT] = file_utilities.count_objects(
                input_layer=input_path
            )
            return

        processing_input_objects: List[Tuple[str, str]] = list(self._processing_items())

        filtered_context_path = (
            self.work_file_manager_persistent_files.generate_partition_path(
                object_name=object_key, tag="input_contex_filtered"
            )
        )

        file_utilities.create_feature_class(
            template_feature=input_path, new_feature=filtered_context_path
        )
        for processing_object, path in processing_input_objects:
            memory_layer = self.work_file_manager_temp_files.generate_partition_path(
                object_name=object_key, tag=f"near_{processing_object}_selection"
            )
            custom_arcpy.select_location_and_make_feature_layer(
                input_layer=input_path,
                overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
                select_features=path,
                output_name=memory_layer,
                search_distance=self.search_distance,
            )

            arcpy.management.Append(
                inputs=memory_layer,
                target=filtered_context_path,
                schema_type="NO_TEST",
            )
            self.work_file_manager_temp_files.delete_created_files()

        self.input_catalog[object_key][self.INPUT_KEY] = filtered_context_path
        self.input_catalog[object_key][self.COUNT] = file_utilities.count_objects(
            input_layer=filtered_context_path
        )
        self.input_catalog[object_key][self.REDUCED_COUNT] = (
            self.input_catalog[object_key][self.PRE_OPTIMIZATION_COUNT]
            - self.input_catalog[object_key][self.COUNT]
        )

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
        - Updates `iteration_catalog` with path and feature count.
        - Creates a dummy feature if no features are found.

        Returns:
            bool: True if the partition contains any features for this object,
            False otherwise.
        """
        iteration_entry = self.iteration_catalog.setdefault(object_key, {})

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
            iteration_entry[self.COUNT] = center_count
            self.update_empty_object_tag_with_dummy_file(
                object_key=object_key, tag=self.INPUT_KEY
            )
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

        iteration_entry[self.COUNT] = (
            file_utilities.count_objects(input_layer=output_path)
            if self.search_distance > 0
            else center_count
        )
        iteration_entry[self.INPUT_KEY] = output_path
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

        for object_key, input_path in self._processing_items():
            result = self.process_single_processing_input(
                object_key=object_key,
                input_path=input_path,
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
        - Updates `iteration_catalog` with feature count and path.
        - If no features are found, assigns a dummy feature path.

        Side effects:
            Creates/deletes temporary feature classes and updates `iteration_catalog`.
        """
        iteration_entry = self.iteration_catalog.setdefault(object_key, {})
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
            iteration_entry[self.INPUT_KEY] = output_path

        else:
            self.update_empty_object_tag_with_dummy_file(
                object_key=object_key, tag=self.INPUT_KEY
            )
        iteration_entry[self.COUNT] = count

    def process_all_context_inputs(
        self,
        iteration_partition: str,
        partition_id: int,
    ) -> None:
        """
        Process all configured context inputs for one partition.

        Calls `process_single_context_input` for each context object
        and records results in `iteration_catalog`.
        """
        for object_key, input_path in self._context_items():
            self.process_single_context_input(
                object_key=object_key,
                input_path=input_path,
                iteration_partition=iteration_partition,
                partition_id=partition_id,
            )

    def track_iteration_time(self, object_id: int, inputs_present: bool) -> None:
        """
        Tracks runtime and estimates remaining time based on iterations with inputs.
        Prints current time, elapsed runtime, and estimated remaining runtime.
        """
        iteration_time = time.time() - self.iteration_start_time
        if inputs_present:
            self.iteration_times_with_input.append(iteration_time)

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
            return self.iteration_catalog[inject.object][inject.tag]

        path = self.work_file_manager_resolved_files.generate_partition_path(
            object_name=inject.object,
            tag=inject.tag,
            partition_id=partition_id,
        )
        self.iteration_catalog.setdefault(inject.object, {})[inject.tag] = path

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
                    dict_data=self._jsonify(execution_log),
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
                    dict_data=self._jsonify(attempt_log),
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

    def _append_partition_selected_features(
        self,
        object_key: str,
        tag: str,
        iteration_path: Any,
        final_output_path: str,
        partition_id: int,
    ) -> None:
        """
        Checks whether the intermediate result for the given object and tag is valid,
        and appends it to the final output if so.

        Args:
            object_key (str): The object identifier (e.g. 'building_polygons').
            tag (str): The processing tag (e.g. 'some_logic').
            final_output_path (str): Destination output path.
            partition_id (int): Current partition identifier.
        """
        if not file_utilities.feature_has_rows(feature=iteration_path):
            return

        partition_selection_path = (
            self.work_file_manager_temp_files.generate_partition_path(
                object_name=object_key,
                tag=tag,
                partition_id=partition_id,
                suffix="partition_final_output_append_selection",
            )
        )

        custom_arcpy.select_attribute_and_make_feature_layer(
            input_layer=iteration_path,
            expression=f"{self.PARTITION_FIELD} = 1",
            output_name=partition_selection_path,
        )

        try:
            if not file_utilities.feature_has_rows(feature=partition_selection_path):
                return
            if not arcpy.Exists(final_output_path):
                arcpy.management.CopyFeatures(
                    in_features=partition_selection_path,
                    out_feature_class=final_output_path,
                )
                print(f"Created final output for {object_key}:{tag}")
            else:
                arcpy.management.Append(
                    inputs=partition_selection_path,
                    target=final_output_path,
                    schema_type="NO_TEST",
                )
                print(f"Appended to final output for {object_key}:{tag}")

        finally:
            self.work_file_manager_temp_files.delete_created_files()

    def append_iteration_outputs_to_final(self, partition_id: int) -> None:
        """
        Appends all valid outputs for the current iteration to their final output paths.

        Skips any objects marked as dummy and ensures only non-empty, valid inputs are appended.
        """
        for object_key, tag, final_output_path in self._output_vector_items():
            iteration_entry = self.iteration_catalog.get(object_key)
            if not iteration_entry:
                continue

            iteration_paths = iteration_entry.get(tag)
            self._append_partition_selected_features(
                object_key=object_key,
                tag=tag,
                iteration_path=iteration_paths,
                final_output_path=final_output_path,
                partition_id=partition_id,
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

        for object_key, input_path in self._processing_items():
            print(f"Cleaning fields in processing input: {input_path}")
            file_utilities.delete_fields_if_exist(input_path, fields_to_delete)

    def _reset_iteration_state(self, partition_id: int) -> None:
        print(
            f"\nProcessing Partition: {partition_id} out of {self.max_partition_count}"
        )
        self.iteration_start_time = time.time()
        self.iteration_catalog = {}

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

            try:
                inputs_present_in_partition = self.process_all_processing_inputs(
                    iteration_partition=iteration_partition,
                    partition_id=partition_id,
                )
                if not inputs_present_in_partition:
                    continue

                self.process_all_context_inputs(
                    iteration_partition=iteration_partition, partition_id=partition_id
                )

                self.execute_injected_methods_with_retry(partition_id=partition_id)
                self.write_documentation(
                    name=f"catalog_{partition_id}",
                    dict_data=self.iteration_catalog,
                    sub_dir="iteration_catalog",
                )
                self.append_iteration_outputs_to_final(partition_id=partition_id)

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
        self.create_dummy_features(tag=self.INPUT_KEY)
        self.write_documentation(name="input_catalog", dict_data=self.input_catalog)

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

        self.cleanup_helper_fields()
        self.work_file_manager_persistent_files.delete_created_files()
        self.write_documentation(name="error_log", dict_data=self.error_log)


if __name__ == "__main__":
    environment_setup.main()
