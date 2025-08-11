from re import search
import arcpy
import os
from typing import Dict, Literal, List, Any
import time
from datetime import datetime
import pprint
import copy
from dataclasses import replace, fields, is_dataclass, asdict

from composition_configs import core_config
from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy, file_utilities
from custom_tools.decorators.timing_decorator import timing_decorator

from file_manager.work_file_manager import PartitionWorkFileManager


class PartitionIterator:
    """
    This class handles processing of processing intense operations for large data sources using partitions.
    Differentiating between which data is important and which are needed for context it processes as little
    data as possible saving time. It then iterates over the partitions selecting data, and doing any amount
    of logic on the selections, finally appending the defined result to an output file.

    **Alias and Type Terminology:**

    - **Alias:** A named reference to a dataset. Each alias represents a specific dataset that will be used
      as an input during partitioning. Aliases allow the class to organize and reference datasets
      consistently across different logics.

    - **Type:** Each alias can have multiple types, indicating different versions the dataset can be accessed during
      partitioning process. A type holds a path. This makes it so that if you run multiple logics in partition iterator
      you can still access any of the outputs at any point for each alias.

    **Setting Up `alias_path_data` and `alias_path_outputs`:**

    - **`alias_path_data`**: A dictionary used to define the input datasets for the class. Each key is an alias,
      and its value is a list of tuples where the first element is a type, and the second element is the path to the dataset.
      The type of must be either 'input', 'context', 'reference' in `alias_path_data`. In a sense alias_path_data
      works to load in all the data you are going to use in an instance of partition iterator.
      So if you have different logics using inputs all the data used by all logics are entered in alias_path_data.


    - **`alias_path_outputs`**: A dictionary used to define the output datasets for the class. Each key is an alias,
      and its value is a list of tuples where the first element is the output type (e.g., 'processed_output') and
      the second element is the path where the output should be saved. This means that you can have multiple outputs
      for each alias.

    **Important: Reserved Types for Alias:**

    The following types are reserved for use by the class and should not be used to create new output types in logic configs:
      - **"input"**:
        Used for input datasets provided to the class. Is the focus of the processing. If you in a config want to use
        the partition selection of the original input data as an input this is the type which should be used.
      - **"context"**:
        Represents context data used during processing. This data is not central and will be selected based on proximity
        to input data. If you in a config want to use the partition selection of the original context data as an input
        this is the type which should be used.
      - **"reference"**:
        Represents reference datasets that are completely static and will not be processed in any way.
        An example could be a lyrx file.
      - **"input_copy"**:
        Internal type used to hold a copy of the global input data. Should not be used in configs.
      - **"context_copy"**:
        Internal type used to hold a copy of the global context data. Should not be used in configs.

    New types should only be created during the outputs from configs in custom_functions, and they should not use any
    of the reserved types listed above if you intend it to be a new output. So for instance an operation doing a buffer
    on the "input" type of alias should not have an output using the "input" type, but for instance "buffer". If you
    in the next config want to use the buffer output, use the "buffer" type for the alias as an input for the next config.

    **Custom Function Configuration:**

    - The `custom_functions` parameter is a list of function configurations, where each configuration describes
      a custom function (standalone or a method of a class) to be executed during the partitioning process.
    - The input and output parameters needs to be defined using the partition_io_decorator. A logic can have multiple
      input and output parameter. for each function are defined as tuples of `(alias, type)`. The alias refers
      to a named dataset, while the type specifies whether the dataset is used as an input or an output.
    - Custom functions must be decorated with the `partition_io_decorator` to mark which parameters are inputs
      and which are outputs. Only parameters marked as inputs or outputs will be managed by this system.
    - Outputs can create new types associated with an alias, and these new types will have paths dynamically
      generated by the class. These new types can then be used as inputs for other functions in subsequent
      iterations.
    - The class itself can write any existing alias to its final output, but it cannot create new types for
      the alias.

    **Important Notes:**

    - Any function (or class method) included in `custom_functions` must be decorated with the `partition_io_decorator`.
      For class methods, this means the method being used in `custom_functions`, not the entire class, must be decorated.
    - During processing, the class dynamically resolves the paths for both input and output datasets based on the
      `(alias, type)` tuples. New paths for outputs will be created automatically, and these outputs can then be used
      in future iterations as inputs with the corresponding alias and type.
    - Multiple outputs for a single alias can exist, but only previously defined types can be used as inputs for
      the class’s output.

    Args:
        alias_path_data (Dict[str, Tuple[str, str]]):
            A dictionary where the key is an alias (representing a dataset), and the value is a tuple containing
            the type of data (e.g., 'input', 'context') and the path to the dataset.
        alias_path_outputs (Dict[str, Tuple[str, str]]):
            A dictionary where the key is an alias (representing a dataset), and the value is a tuple containing
            the type of output and the path where the results should be saved.
        root_file_partition_iterator (str):
            The base path for intermediate outputs generated during the partitioning process.
        custom_functions (list, optional):
            A list of configurations for the custom functions that will be executed during the partitioning process.
            Each function must be configured with the `partition_io_decorator` and have its input/output parameters
            specified.
        dictionary_documentation_path (str, optional):
            The path where documentation related to the partitioning process (e.g., JSON logs) will be stored.
        feature_count (str, optional):
            The maximum number of features allowed in each partition. Default is "15000".
        partition_method (Literal['FEATURES', 'VERTICES'], optional):
            The method used to create partitions, either by the number of features ('FEATURES') or vertices ('VERTICES').
            Default is 'FEATURES'.
        search_distance (str, optional):
            The distance within which context features are selected relative to input features. Default is '500 Meters'.
        context_selection (bool, optional):
            Whether to enable context feature selection based on proximity to input features. Default is True.
        delete_final_outputs (bool, optional):
            Whether to delete existing final outputs before starting the partitioning process. Default is True.
        safe_output_final_cleanup (bool, optional):
            Whether to enable safe deletion of outputs during cleanup. Default is True.
        object_id_field (str, optional):
            The field representing the object ID used during partitioning. Default is "OBJECTID".
    """

    # Class-level constants
    INPUT_TYPE_KEY = "input_type"
    DATA_TYPE_KEY = "data_type"
    INPUT_TAG_KEY = "input"
    INJECTABLE_INPUT_TAG_KEY = INPUT_TAG_KEY
    DUMMY = "dummy"
    COUNT = "count"
    DUMMY_USED = "dummy_used"
    RAW_INPUT_TAG = "raw_input"
    PARTITION_FIELD = "partition_selection_field"
    ORIGINAL_ID_FIELD = "original_id_field"

    def __init__(
        self,
        partition_io_config: core_config.PartitionIOConfig,
        partition_method_inject_config: core_config.MethodEntriesConfig,
        partition_iterator_run_config: core_config.PartitionRunConfig,
        work_file_manager_config: core_config.WorkFileConfig,
    ):
        """
        Initializes the PartitionIterator with input and output datasets, custom functions, and configuration
        for partitioning and processing.

        Args:
            See class docstring.
        """

        # Raw inputs and initial setup
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

        ##
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

    def resolve_partition_input_config(
        self,
        entries: List[core_config.ResolvedInputEntry],
        target_dict: Dict[str, Dict[str, str]],
    ) -> None:
        for entry in entries:
            entry_dict = target_dict.setdefault(entry.object, {})
            entry_dict[self.INPUT_TYPE_KEY] = entry.input_type
            entry_dict[self.DATA_TYPE_KEY] = entry.data_type
            entry_dict[entry.tag] = entry.path

    def resolve_partition_output_config(
        self,
        entries: List[core_config.ResolvedOutputEntry],
        target_dict: Dict[str, Dict[str, str]],
    ) -> None:
        for entry in entries:
            entry_dict = target_dict.setdefault(entry.object, {})
            entry_dict[self.DATA_TYPE_KEY] = entry.data_type
            entry_dict[entry.tag] = entry.path

    def _create_cartographic_partitions(self, element_limit: int) -> None:
        """
        What:
            Creates cartographic partitions based on the given element_limit.
            Overwrites any existing partition feature.

        Args:
            feature_count (int): The feature count used to limit partition size.
        """
        self.work_file_manager_partition_feature.delete_created_files()
        VALID_TAGS = {self.RAW_INPUT_TAG}

        in_features = [
            path
            for object_, tag_dict in self.input_catalog.items()
            for tag, path in tag_dict.items()
            if tag in VALID_TAGS and path is not None
        ]

        if not in_features:
            print("No input or context features available for creating partitions.")
            return

        print(f"Creating cartographic partitions from features: {in_features}")

        arcpy.cartography.CreateCartographicPartitions(
            in_features=in_features,
            out_features=self.partition_feature,
            feature_count=element_limit,
            partition_method=self.partition_method,
        )
        print(f"Created partitions in {self.partition_feature}")

    def _count_maximum_objects_in_partition(self) -> int:
        """
        What:
            Iterates over all partitions and determines the highest number of total processed features
            (processing + context) found in any single partition.

        How:
            For each partition:
            - Select the partition geometry.
            - Run processing and context logic.
            - Track total processed objects.
            - Cleanup intermediate files.

        Returns:
            int: Maximum number of features found in a partition across all iterations.
        """
        self.update_max_partition_count()
        max_partition_load = 0

        for partition_id in range(1, self.max_partition_count + 1):
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
                self.input_catalog[obj_key].get(self.COUNT, 0)
                for obj_key in self.input_catalog
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

            # Prevent retry loops on stable output
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
        """
        Deletes all final output feature classes if they exist.

        How:
            - Iterates over all object/tag pairs in `nested_output_object_tag`.
            - Deletes each final output path using the shared utility.
        """
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
        What:
            Creates a dummy feature class for each object that contains a valid path for the given tag.

        How:
            For each object in nested_input_object_tag:
            - If the given tag exists and has a valid path, use it as a template to create a dummy feature.
            - The dummy path is stored under the 'dummy' key in the object's tag dictionary.

        Args:
            tag (str): The inner key (e.g. "raw_input") to check and use as template.
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

    def reset_dummy_used(self):
        """Sets the dummy_used to false"""
        for object in self.input_catalog:
            self.input_catalog[object][self.DUMMY_USED] = False

    def ensure_dummy_flag_for_all_objects(self):
        for object_key in self.input_catalog:
            if self.DUMMY_USED not in self.input_catalog[object_key]:
                self.input_catalog.setdefault(object_key, {})[self.DUMMY_USED] = False

    def update_empty_object_tag_with_dummy_file(
        self, object_key: str, tag: str
    ) -> None:
        """
        Replaces the value for the given tag with the dummy path if available for the object_key.
        Marks 'dummy_used' as True for traceability.
        """
        tag_dict = self.input_catalog.get(object_key)
        if tag_dict is None:
            return

        dummy_path = tag_dict.get(self.DUMMY)
        if dummy_path is None:
            return

        if tag not in tag_dict:
            return

        self.input_catalog[object_key][tag] = [dummy_path]
        self.input_catalog[object_key][self.DUMMY_USED] = True

        print(f"Dummy path for tag '{tag}' on '{object_key}' set to: {dummy_path}")

    def write_documentation(self, name: str, dict_data: dict) -> None:
        """
        Writes a documentation JSON file to the configured documentation directory.

        Args:
            name (str): File name, e.g., 'error_log'
            data (dict): Dictionary to serialize into JSON.
        """
        file_utilities.write_dict_to_json(
            path=rf"{self.documentation_directory}\{name}.json",
            dict_data=dict_data,
        )

    def update_max_partition_count(self) -> None:
        """
        Determine the maximum OBJECTID for partitioning.
        """
        try:
            # Use a search cursor to find the maximum OBJECTID
            with arcpy.da.SearchCursor(
                in_table=self.partition_feature,
                field_names=self.object_id_field,
                sql_clause=(None, f"ORDER BY {self.object_id_field} DESC"),
            ) as cursor:
                self.max_partition_count = next(cursor)[0]

            print(f"Maximum {self.object_id_field} found: {self.max_partition_count}")

        except Exception as e:
            print(f"Error in finding max {self.object_id_field}: {e}")

    def prepare_input_data(self):
        for object_key, tag_dict in self.input_catalog.items():
            input_type = tag_dict.get(self.INPUT_TYPE_KEY)
            input_path = tag_dict[self.INPUT_TAG_KEY]

            if input_type == core_config.InputType.PROCESSING.value:
                self._prepare_processing_input(
                    object_key=object_key, input_path=input_path
                )

            elif input_type == core_config.InputType.CONTEXT.value:
                self._prepare_context_input(
                    object_key=object_key, input_path=input_path
                )

    def _prepare_processing_input(self, object_key: str, input_path: str) -> None:
        print(f"Copied processing input for: {object_key}")
        copy_path = self.work_file_manager_persistent_files.generate_partition_path(
            object_name=object_key, tag="raw_input"
        )
        arcpy.management.Copy(in_data=input_path, out_data=copy_path)

        self.input_catalog[object_key][self.RAW_INPUT_TAG] = copy_path

        arcpy.AddField_management(
            in_table=copy_path,
            field_name=self.PARTITION_FIELD,
            field_type="LONG",
        )

    def _prepare_context_input(self, object_key: str, input_path: str) -> None:
        copy_path = self.work_file_manager_persistent_files.generate_partition_path(
            object_name=object_key, tag="input_contex_filtered"
        )

        if self.search_distance > 0:
            file_utilities.create_feature_class(
                template_feature=input_path, new_feature=copy_path
            )
            for object, tag in self.input_catalog.items():
                if (
                    tag.get(self.INPUT_TYPE_KEY)
                    == core_config.InputType.PROCESSING.value
                    and self.RAW_INPUT_TAG in tag
                ):
                    input_copy_path = tag[self.RAW_INPUT_TAG]
                    memory_layer = (
                        self.work_file_manager_temp_files.generate_partition_path(
                            object_name=object_key, tag=f"near_{object}_selection"
                        )
                    )
                    custom_arcpy.select_location_and_make_feature_layer(
                        input_layer=input_path,
                        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
                        select_features=input_copy_path,
                        output_name=memory_layer,
                        search_distance=self.search_distance,
                    )

                    arcpy.management.Append(
                        inputs=memory_layer,
                        target=copy_path,
                        schema_type="NO_TEST",
                    )
                    self.work_file_manager_temp_files.delete_created_files()

            print(f"Processed selected context features for: {object_key}")

        else:
            arcpy.management.Copy(in_data=input_path, out_data=copy_path)
            print(f"Copied full context data for: {object_key}")

        self.input_catalog[object_key][self.RAW_INPUT_TAG] = copy_path

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
        selection_memory_path = (
            self.work_file_manager_temp_files.generate_partition_path(
                object_name=object_key,
                partition_id=partition_id,
                suffix="centerpoint_in_partition",
            )
        )

        # Select features whose center is in partition
        custom_arcpy.select_location_and_make_feature_layer(
            input_layer=input_path,
            overlap_type=custom_arcpy.OverlapType.HAVE_THEIR_CENTER_IN,
            select_features=iteration_partition,
            output_name=selection_memory_path,
        )

        count_center = file_utilities.count_objects(selection_memory_path)
        if count_center == 0:
            self.update_empty_object_tag_with_dummy_file(
                object_key=object_key, tag=self.INJECTABLE_INPUT_TAG_KEY
            )
            self.input_catalog[object_key][self.COUNT] = count_center
            return False

        print(f"{object_key} has {count_center} features in {iteration_partition}")
        arcpy.CalculateField_management(
            selection_memory_path, self.PARTITION_FIELD, "1"
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
            count = file_utilities.count_objects(input_layer=output_path)
            self.input_catalog[object_key][self.COUNT] = count

        if self.search_distance <= 0:
            self.input_catalog[object_key][self.COUNT] = count_center

        self.input_catalog[object_key][self.INJECTABLE_INPUT_TAG_KEY] = output_path
        self.work_file_manager_temp_files.delete_created_files()
        return True

    def process_all_processing_inputs(
        self,
        iteration_partition: str,
        partition_id: int,
    ) -> bool:
        has_inputs = False

        for object_key, tag_dict in self.input_catalog.items():
            if (
                tag_dict.get(self.INPUT_TYPE_KEY)
                != core_config.InputType.PROCESSING.value
            ):
                continue
            if self.RAW_INPUT_TAG not in tag_dict:
                continue

            input_path = tag_dict[self.RAW_INPUT_TAG]

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
            print(f"{object_key} has {count} context features in {iteration_partition}")
            self.input_catalog[object_key][self.INJECTABLE_INPUT_TAG_KEY] = output_path

        else:
            self.update_empty_object_tag_with_dummy_file(
                object_key=object_key, tag=self.INJECTABLE_INPUT_TAG_KEY
            )
            print(
                f"iteration partition {partition_id} has no context features for {object_key}"
            )
        self.input_catalog[object_key][self.COUNT] = count

    def process_all_context_inputs(
        self,
        iteration_partition: str,
        partition_id: int,
    ) -> None:
        for object_key, tag_dict in self.input_catalog.items():
            if tag_dict.get(self.INPUT_TYPE_KEY) != core_config.InputType.CONTEXT.value:
                continue
            if self.RAW_INPUT_TAG not in tag_dict:
                continue

            input_path = tag_dict[self.RAW_INPUT_TAG]
            self.process_single_context_input(
                object_key=object_key,
                input_path=input_path,
                iteration_partition=iteration_partition,
                partition_id=partition_id,
            )

    @staticmethod
    def format_time(seconds) -> str:
        """
        What:
            Converts seconds to a formatted string: HH:MM:SS.

        Args:
            seconds (float): Time in seconds.

        Returns:
            str: Formatted time string.
        """
        seconds = int(seconds)  # Convert to integer for rounding
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours} hours, {minutes} minutes, {seconds} seconds"

    def track_iteration_time(self, object_id, inputs_present_in_partition):
        """
        What:
            Tracks the iteration time and estimate the remaining time. It adds the time of iterations
            with input features to a list, using the average time of this list as baseline for remaining time.

        Args:
            object_id (int): The ID of the current partition iteration.
            inputs_present_in_partition (bool): Flag indicating if there were input features in the iteration.
        """
        iteration_time = time.time() - self.iteration_start_time
        if inputs_present_in_partition:
            self.iteration_times_with_input.append(iteration_time)
            average_runtime_per_iteration = sum(self.iteration_times_with_input) / len(
                self.iteration_times_with_input
            )
        else:
            average_runtime_per_iteration = (
                sum(self.iteration_times_with_input)
                / len(self.iteration_times_with_input)
                if self.iteration_times_with_input
                else 0
            )

        total_runtime = time.time() - self.total_start_time
        remaining_iterations = self.max_partition_count - object_id
        estimated_remaining_time = remaining_iterations * average_runtime_per_iteration

        formatted_total_runtime = self.format_time(total_runtime)
        formatted_estimated_remaining_time = self.format_time(estimated_remaining_time)

        current_time_date = datetime.now().strftime("%m-%d %H:%M:%S")

        print(f"\nCurrent time: {current_time_date}")
        print(f"Current runtime: {formatted_total_runtime}")
        print(f"Estimated remaining time: {formatted_estimated_remaining_time}")

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
            resolved_params = self.resolve_param_injections(
                method_config=copy.deepcopy(entry.params),
                partition_id=partition_id,
            )

            if isinstance(entry, core_config.FuncMethodEntryConfig):
                resolved_configs.append(
                    core_config.FuncMethodEntryConfig(
                        func=entry.func, params=resolved_params
                    )
                )
            elif isinstance(entry, core_config.ClassMethodEntryConfig):
                resolved_configs.append(
                    core_config.ClassMethodEntryConfig(
                        class_=entry.class_,
                        method=entry.method,
                        params=resolved_params,
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
        if inject.tag == self.INJECTABLE_INPUT_TAG_KEY:
            return self.input_catalog[inject.object][inject.tag]

        path = self.construct_partition_path_for_object_tag(
            object=inject.object,
            tag=inject.tag,
            partition_id=partition_id,
        )
        self.input_catalog.setdefault(inject.object, {})[inject.tag] = path

        return path

    def construct_partition_path_for_object_tag(self, object, tag, partition_id) -> str:
        """
        Construct a new path for a given alias and type specific to the current iteration.
        """
        return self.work_file_manager_iteration_files.generate_partition_path(
            object_name=object,
            tag=tag,
            partition_id=partition_id,
        )

    def execute_injected_methods(
        self, method_entries_config: core_config.MethodEntriesConfig
    ) -> None:
        """
        What:
            Execute injected methods whose parameter paths have already been resolved.

        How:
            For class-based methods:
                - Instantiate the class using constructor parameters.
                - Call the specified method with the remaining parameters.
            For function-based methods:
                - Call the function with all parameters.
        """
        for entry in method_entries_config.entries:
            if isinstance(entry, core_config.ClassMethodEntryConfig):
                cls = entry.class_
                method_name = entry.method
                method = getattr(cls, method_name)

                class_params = {}
                method_params = {}

                init_params = cls.__init__.__code__.co_varnames

                if is_dataclass(entry.params) and not isinstance(entry.params, type):
                    param_dict = asdict(entry.params)
                else:
                    assert isinstance(entry.params, dict)
                    param_dict = entry.params

                for param, value in param_dict.items():
                    if param in init_params:
                        class_params[param] = value
                    else:
                        method_params[param] = value

                print(f"Class parameters for {cls.__name__}:")
                pprint.pprint(class_params, indent=4)

                print(f"Method parameters for {method_name}:")
                pprint.pprint(method_params, indent=4)

                instance = cls(**class_params)
                method(instance, **method_params)

            elif isinstance(entry, core_config.FuncMethodEntryConfig):
                func = entry.func
                print(f"Function parameters for {func.__name__}:")
                pprint.pprint(entry.params, indent=4)
                func(**entry.params)

            else:
                raise TypeError(f"Unsupported method entry type: {type(entry)}")

    def execute_injected_methods_with_retry(self, object_id: int):
        """
        What:
            Helper function to execute custom functions with retry logic to handle potential failures
            caused by unreliable 3rd party logic.

        Args:
            object_id (int): The current object_id being processed (for logging).
        """
        max_retries = 50

        for attempt in range(max_retries):
            try:
                resolved_injection_method_configs = (
                    self.resolve_injected_io_for_methods(
                        method_entries_config=self.list_of_methods,
                        partition_id=object_id,
                    )
                )
                self.execute_injected_methods(
                    method_entries_config=resolved_injection_method_configs
                )
                break  # If successful, exit the retry loop
            except Exception as e:
                error_message = str(e)
                print(f"Attempt {attempt + 1} failed with error: {error_message}")

                # Initialize the log for this iteration if not already done
                if object_id not in self.error_log:
                    self.error_log[object_id] = {
                        "Number of retries": 0,
                        "Error Messages": {},
                    }

                # Update the log with the retry attempt and error message
                self.error_log[object_id]["Number of retries"] += 1
                self.error_log[object_id]["Error Messages"][attempt + 1] = error_message

                if attempt + 1 == max_retries:
                    print("Max retries reached.")
                    self.write_documentation(name="error_log", dict_data=self.error_log)
                    raise Exception(error_message)

    def _append_tag_output_if_valid(
        self, object_key: str, tag: str, final_output_path: str, partition_id: int
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
        input_tag_data = self.input_catalog.get(object_key, {})
        input_feature_path = input_tag_data.get(tag)

        if not input_feature_path:
            return

        if (
            not arcpy.Exists(input_feature_path)
            or int(arcpy.GetCount_management(input_feature_path).getOutput(0)) <= 0
        ):
            print(f"Skipping empty or missing path for {object_key}:{tag}")
            return

        partition_selection_path = (
            self.work_file_manager_temp_files.generate_partition_path(
                object_name=object_key,
                tag=tag,
                partition_id=partition_id,
                suffix="partition_target_selection",
            )
        )

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=input_feature_path,
            expression=f"{self.PARTITION_FIELD} = 1",
            output_name=partition_selection_path,
        )

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
        self.work_file_manager_temp_files.delete_created_files()

    def append_iteration_outputs_to_final(self, partition_id: int) -> None:
        """
        Appends all valid outputs for the current iteration to their final output paths.

        Skips any objects marked as dummy and ensures only non-empty, valid inputs are appended.
        """
        for object_key, tag_dict in self.output_catalog.items():
            if self.input_catalog.get(object_key, {}).get("dummy_used"):
                continue

            for tag, final_output_path in tag_dict.items():
                self._append_tag_output_if_valid(
                    object_key=object_key,
                    tag=tag,
                    final_output_path=final_output_path,
                    partition_id=partition_id,
                )

    def cleanup_final_outputs(self):
        """
        Cleanup function to delete unnecessary fields from final output feature classes.
        """
        fields_to_delete = [self.PARTITION_FIELD]
        # delete fields moved to custom utils

        for object_key, tag_dict in self.output_catalog.items():
            for tag, final_output_path in tag_dict.items():
                print(f"Cleaning fields in: {final_output_path}")
                file_utilities.delete_fields_if_exist(
                    final_output_path, fields_to_delete
                )

    def partition_iteration(self):
        """
        What:
            Processes each data partition in multiple iterations.

        How:
            - Iterates over partitions based on `object_id`, from 1 to `max_object_id`.
            - For each iteration:
                - Creates and resets dummy features.
                - Deletes files from the previous iteration and clears the file path list.
                - Backs up the original parameters for custom functions.
                - Selects a partition feature and processes the inputs for that partition.
                - If inputs are present:
                    - Processes context features.
                    - Finds input/output parameters for custom logic.
                    - Exports data from the iteration to JSON.
                    - Executes custom functions.
                    - Appends the output of the current iteration to the final outputs.
        """

        self.update_max_partition_count()

        self.reset_dummy_used()

        self.work_file_manager_iteration_files.delete_created_files()

        for partition_id in range(1, self.max_partition_count + 1):
            self.iteration_start_time = time.time()
            print(
                f"\nProcessing Partition: {partition_id} out of {self.max_partition_count}"
            )
            self.reset_dummy_used()

            iteration_partition = (
                self.work_file_manager_iteration_files.generate_partition_path(
                    object_name="partition_feature_iteration_selection",
                    partition_id=partition_id,
                )
            )
            self.select_partition_feature(
                iteration_partition=iteration_partition, object_id=partition_id
            )

            inputs_present_in_partition = self.process_all_processing_inputs(
                iteration_partition=iteration_partition,
                partition_id=partition_id,
            )

            if inputs_present_in_partition:
                self.process_all_context_inputs(
                    iteration_partition=iteration_partition, partition_id=partition_id
                )
                self.write_documentation(
                    name=f"iteration_{partition_id}",
                    dict_data=self.input_catalog,
                )

                self.execute_injected_methods_with_retry(partition_id)
                self.ensure_dummy_flag_for_all_objects()
                self.append_iteration_outputs_to_final(partition_id=partition_id)
                self.work_file_manager_iteration_files.delete_created_files()
            else:
                self.work_file_manager_iteration_files.delete_created_files()
            self.track_iteration_time(partition_id, inputs_present_in_partition)

    @timing_decorator
    def run(self):
        """
        What:
            Orchestrates the entire workflow for the class, from data preparation to final output generation.

        How:
            - Initializes by unpacking input and output paths into `nested_alias_type_data` and `nested_final_outputs`.
            - Exports the initialized dictionaries to JSON for future reference.
            - Prepares the input data, including deleting old final outputs and processing the raw input data.
            - Creates cartographic partitions to organize the data.
            - Runs the partition iteration process by calling `partition_iteration`.
            - Once iterations are complete, it cleans up final outputs, and logs any errors that occurred.
        """

        self.total_start_time = time.time()

        self.write_documentation(name="post_init", dict_data=self.input_catalog)
        self.write_documentation(name="output_dict", dict_data=self.output_catalog)

        print("\nStarting Data Preparation...")
        self.delete_final_outputs()
        self.prepare_input_data()
        self.create_dummy_features(tag=self.RAW_INPUT_TAG)

        self.write_documentation(name="post_data_prep", dict_data=self.input_catalog)
        if self.run_partition_optimization:
            self._find_partition_size()

        print("\nCreating Cartographic Partitions...")
        if not self.run_partition_optimization:
            self.final_partition_feature_count = self.max_elements_per_partition
        self._create_cartographic_partitions(
            element_limit=self.final_partition_feature_count
        )

        print("\nStarting on Partition Iteration...")
        self.partition_iteration()

        self.write_documentation(name="post_runtime", dict_data=self.input_catalog)
        self.cleanup_final_outputs()
        self.work_file_manager_persistent_files.delete_created_files()
        self.write_documentation(name="error_log", dict_data=self.error_log)


if __name__ == "__main__":
    environment_setup.main()
