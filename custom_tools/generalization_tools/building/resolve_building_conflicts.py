# Importing modules
import arcpy

# Importing custom files
import config
import constants.n100_constants
from custom_tools.general_tools import custom_arcpy
from input_data import input_n100
from typing import Union, List, Dict, Tuple
import input_data.input_n50
import input_data.input_n100

from input_data.input_symbology import SymbologyN100
from file_manager.n100.file_manager_buildings import Building_N100
from file_manager.base_file_manager import BaseFileManager
from custom_tools.general_tools.file_utilities import WorkFileManager
from constants.n100_constants import N100_Symbology, N100_Values
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from env_setup import environment_setup
from input_data import input_symbology

# Importing timing decorator

from custom_tools.decorators.partition_io_decorator import partition_io_decorator


class ResolveBuildingConflictsPoints:
    """

    What:
        This class handles the resolution of building conflicts based on specified symbology, gap distances,
        and input barriers. The workflow involves multiple steps, including symbology application, conflict resolution,
        and transformation of invisible building polygons to squares for further analysis.

    How:
        Symbology Application: This function applies symbology to layers such as building points,
        building polygons, and barriers to standardize visualization and prepare for conflict resolution.

        Conflict Resolution (RBC Stages): Building conflicts are resolved in two stages.

        RBC 1: This stage processes building polygons and squares, resolving conflicts with respect
        to road and rail barriers.

        RBC 2: This stage refines the results from RBC 1, adjusting for any unresolved conflicts.

        Invisible Polygons: Any invisible polygons resulting from the conflict resolution process
        are transformed into points and then converted to squares, ensuring that all relevant features
        are considered in further analysis.

    Why:
        Resolve building conflicts for a cleaner map look.

    Args:
        building_inputs (Dict[str, str]):
            Dictionary containing paths to building points and polygons.
        building_gap_distance (int):
            The gap distance (in meters) used for resolving building conflicts.
        barrier_inputs (Dict[str, str]):
            Dictionary containing paths to various barrier inputs such as roads and railways.
        barrier_gap_distances (Dict[str, int]):
            Dictionary containing gap distances for each barrier type (e.g., road, railway).
        building_symbol_dimension (Dict[int, tuple]):
            Dictionary mapping building symbols to their respective dimensions.
        lyrx_files (Dict[str, str]):
            Dictionary containing paths to lyrx files used for applying symbology to the features.
        base_path_for_lyrx (str):
            The base path for storing lyrx files for the processing workflow.
        base_path_for_features (str):
            The base path for storing feature files during processing.
        output_files (Dict[str, str]):
            Dictionary containing paths for storing the final output of  building points and polygons.
        write_work_files_to_memory (bool, optional):
            If True, work files are written to memory during the process. Default is False.
        keep_work_files (bool, optional):
            If True, work files are retained after processing is complete. Default is False.
    """

    def __init__(
        self,
        input_list_of_dicts_data_structure,
        building_inputs: Dict[str, str],
        building_gap_distance: int,
        barrier_inputs: Dict[str, str],
        barrier_gap_distances: Dict[str, int],
        building_symbol_dimension: Dict[int, tuple],
        lyrx_files: Dict[str, str],
        base_path_for_lyrx: str,
        root_path: str,
        map_scale: str,
        output_files: Dict[str, str],
        write_work_files_to_memory: bool = False,
        keep_work_files: bool = False,
    ):
        # ========================================
        #                              INITIALIZING VARIABLES
        # ========================================

        #  Building inputs
        self.input_building_points = building_inputs["building_points"]
        self.input_building_polygons = building_inputs["building_polygons"]

        # Building symbol dimension
        self.building_symbol_dimension = building_symbol_dimension

        # Building gap distance
        self.building_gap = building_gap_distance

        self.map_scale = map_scale

        # Barrier inputs
        self.input_road_barrier = barrier_inputs["road"]
        self.input_railway_barrier = barrier_inputs["railway"]
        self.input_railway_station_barrier = barrier_inputs["railway_station"]
        self.input_begrensningskurve_barrier = barrier_inputs["begrensningskurve"]
        self.input_power_grid_lines_barrier = barrier_inputs["power_grid_lines"]

        # Lyrx-files
        self.building_squares_lyrx = lyrx_files["building_squares"]
        self.building_polygons_lyrx = lyrx_files["building_polygons"]
        self.road_barrier_lyrx = lyrx_files["road"]
        self.railway_barrier_lyrx = lyrx_files["railway"]
        self.railway_station_barrier_lyrx = lyrx_files["railway_station"]
        self.begrensningskurve_barrier_lyrx = lyrx_files["begrensningskurve"]

        # Barrier gap distance
        self.road_barrier_gap = barrier_gap_distances["road"]
        self.railway_barrier_gap = barrier_gap_distances["railway"]
        self.railway_station_barrier_gap = barrier_gap_distances["railway_station"]
        self.begrensningskurve_barrier_gap = barrier_gap_distances["begrensningskurve"]
        self.power_grid_lines_barrier_gap = barrier_gap_distances["power_grid_lines"]

        # Output files
        self.output_points = output_files["building_points"]
        self.output_polygons = output_files["building_polygons"]

        self.input_list_of_dicts_data_structure = input_list_of_dicts_data_structure

        self.work_file_manager = WorkFileManager(
            unique_id=id(self),
            root_file=root_path,
            write_to_memory=write_work_files_to_memory,
            keep_files=keep_work_files,
        )

        self.feature_copy = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.input_list_of_dicts_data_structure,
            add_key="feature_copy",
        )

        self.output_lyrx_features = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.feature_copy,
            add_key="lyrx_output",
            file_type="lyrx",
        )

        self.work_file_manager_lyrx = WorkFileManager(
            unique_id=id(self),
            root_file=base_path_for_lyrx,
            write_to_memory=write_work_files_to_memory,
            keep_files=keep_work_files,
        )

        self.result_rbc_1_squares = "result_rbc_1_squares"

        self.gdb_files_list = [
            self.result_rbc_1_squares,
        ]

        self.gdb_files_list = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.gdb_files_list,
        )

        # GDB Work Files
        self.results_rbc_1_squares = "results_rbc_1_squares"
        self.results_rbc_1_polygons = "results_rbc_1_polygons"
        self.invisible_polygons_after_rbc_1 = "invisible_polygons_after_rbc_1"
        self.invisible_polygons_to_points_after_rbc_1 = (
            "invisible_polygons_to_points_after_rbc_1"
        )
        self.building_polygons_to_points_and_then_squares_rbc_1 = (
            "building_polygons_to_points_and_then_squares_rbc_1"
        )
        self.merged_squares_rbc1 = "merged_squares_rbc1"
        self.squares_after_rbc2 = "squares_after_rbc2"
        self.polygons_after_rbc2 = "polygons_after_rbc2"
        self.squares_back_to_points_after_rbc2 = "squares_back_to_points_after_rbc2"

        self.working_files_list_gdb = [
            self.results_rbc_1_squares,
            self.results_rbc_1_polygons,
            self.invisible_polygons_after_rbc_1,
            self.invisible_polygons_to_points_after_rbc_1,
            self.building_polygons_to_points_and_then_squares_rbc_1,
            self.merged_squares_rbc1,
            self.squares_after_rbc2,
            self.polygons_after_rbc2,
            self.squares_back_to_points_after_rbc2,
        ]

        # Lyrx Work FIles
        self.building_squares_with_lyrx = "building_squares_with_lyrx"
        self.polygons_with_lyrx = "polygons_with_lyrx"
        self.roads_with_lyrx = "roads_with_lyrx"
        self.begrensningskurve_with_lyrx = "begrensningskurve_with_lyrx"
        self.railway_with_lyrx = "railway_with_lyrx"
        self.railway_stations_with_lyrx = "railway_stations_with_lyrx"
        self.power_grid_lines_stations_with_lyrx = "power_grid_lines_stations_with_lyrx"
        self.adding_symbology_to_squares_going_into_rbc2 = (
            "adding_symbology_to_squares_going_into_rbc2"
        )
        self.adding_symbology_to_polygons_going_into_rbc2 = (
            "adding_symbology_to_polygons_going_into_rbc2"
        )

        self.working_files_list_lyrx = [
            self.building_squares_with_lyrx,
            self.polygons_with_lyrx,
            self.roads_with_lyrx,
            self.begrensningskurve_with_lyrx,
            self.railway_with_lyrx,
            self.railway_stations_with_lyrx,
            self.power_grid_lines_stations_with_lyrx,
            self.adding_symbology_to_squares_going_into_rbc2,
            self.adding_symbology_to_polygons_going_into_rbc2,
        ]

        self.working_files_list = []

        # Feature base path
        self.base_path_for_features = root_path

        # Lyrx base path
        self.lyrx_base_path = base_path_for_lyrx

        # ========================================
        #                                       LOGICS
        # ========================================

    def copy_input_layers(self):
        def copy_input(
            input_feature: str = None,
            copied_feature: str = None,
        ):
            arcpy.management.CopyFeatures(
                in_features=input_feature,
                out_feature_class=copied_feature,
            )

        self.work_file_manager.apply_to_structure(
            data=self.output_lyrx_features,
            func=copy_input,
            input_feature="input_feature",
            copied_feature="feature_copy",
        )

    def apply_symbology(self):
        def apply_symbology(
            input_feature: str = None,
            input_lyrx_feature: str = None,
            output_name: str = None,
            grouped_lyrx: bool = False,
            target_layer_name: str = None,
        ):
            if grouped_lyrx:
                custom_arcpy.apply_symbology(
                    input_layer=input_feature,
                    in_symbology_layer=input_lyrx_feature,
                    output_name=output_name,
                    grouped_lyrx=grouped_lyrx,
                    target_layer_name=target_layer_name,
                )
            if not grouped_lyrx:
                custom_arcpy.apply_symbology(
                    input_layer=input_feature,
                    in_symbology_layer=input_lyrx_feature,
                    output_name=output_name,
                )

        self.work_file_manager.apply_to_structure(
            data=self.output_lyrx_features,
            func=apply_symbology,
            input_feature="feature_copy",
            input_lyrx_feature="lyrx_file",
            output_name="lyrx_output",
            grouped_lyrx="grouped_lyrx",
            target_layer_name="target_layer_name",
        )

    def apply_symbology_to_the_layers(self):
        """
        Applies symbology to various input layers by looping through the dictionary and using different using lyrx_files
        """
        print("Now starting to apply symbology to layers")

        features_for_apply_symbology = [
            {
                "input_layer": self.input_building_points,
                "in_symbology_layer": self.building_squares_lyrx,
                "output_name": self.building_squares_with_lyrx,
            },
            {
                "input_layer": self.input_building_polygons,
                "in_symbology_layer": self.building_polygons_lyrx,
                "output_name": self.polygons_with_lyrx,
            },
            {
                "input_layer": self.input_road_barrier,
                "in_symbology_layer": self.road_barrier_lyrx,
                "output_name": self.roads_with_lyrx,
            },
            {
                "input_layer": self.input_begrensningskurve_barrier,
                "in_symbology_layer": self.begrensningskurve_barrier_lyrx,
                "output_name": self.begrensningskurve_with_lyrx,
            },
            {
                "input_layer": self.input_railway_barrier,
                "in_symbology_layer": self.railway_barrier_lyrx,
                "output_name": self.railway_with_lyrx,
            },
            {
                "input_layer": self.input_railway_station_barrier,
                "in_symbology_layer": self.railway_station_barrier_lyrx,
                "output_name": self.railway_stations_with_lyrx,
            },
            {
                "input_layer": self.input_power_grid_lines_barrier,
                "in_symbology_layer": self.railway_barrier_lyrx,
                "output_name": self.power_grid_lines_stations_with_lyrx,
            },
        ]
        print(f"Features for applying symbology: {features_for_apply_symbology}\n")

        # Loop over the symbology configurations and apply the function
        for symbology_config in features_for_apply_symbology:
            custom_arcpy.apply_symbology(
                input_layer=symbology_config["input_layer"],
                in_symbology_layer=symbology_config["in_symbology_layer"],
                output_name=symbology_config["output_name"],
            )

    def barriers_for_rbc_2(self):
        """
        Prepares and returns a list of barrier features being used in RBC
        """
        input_barriers_for_rbc = [
            [
                self.work_file_manager.extract_key_by_alias(
                    data=self.output_lyrx_features,
                    unique_alias="begrensningskurve",
                    key="lyrx_output",
                ),
                "false",
                f"{self.begrensningskurve_barrier_gap} Meters",
            ],
            [
                self.work_file_manager.extract_key_by_alias(
                    data=self.output_lyrx_features,
                    unique_alias="railroad_station",
                    key="lyrx_output",
                ),
                "false",
                f"{self.railway_station_barrier_gap} Meters",
            ],
            [
                self.work_file_manager.extract_key_by_alias(
                    data=self.output_lyrx_features,
                    unique_alias="railroad",
                    key="lyrx_output",
                ),
                "false",
                f"{self.railway_barrier_gap} Meters",
            ],
            [
                self.work_file_manager.extract_key_by_alias(
                    data=self.output_lyrx_features,
                    unique_alias="power_grid_lines",
                    key="lyrx_output",
                ),
                "false",
                f"{self.railway_barrier_gap} Meters",
            ],
            [
                self.work_file_manager.extract_key_by_alias(
                    data=self.output_lyrx_features,
                    unique_alias="road",
                    key="lyrx_output",
                ),
                "false",
                f"{self.road_barrier_gap} Meters",
            ],
        ]
        print(f"Input barriers for RBC: {input_barriers_for_rbc}\n")

        return input_barriers_for_rbc

    def barriers_for_rbc(self):
        """
        Prepares and returns a list of barrier features being used in RBC
        """
        input_barriers_for_rbc = [
            [
                self.begrensningskurve_with_lyrx,
                "false",
                f"{self.begrensningskurve_barrier_gap} Meters",
            ],
            [
                self.railway_stations_with_lyrx,
                "false",
                f"{self.railway_station_barrier_gap} Meters",
            ],
            [
                self.railway_with_lyrx,
                "false",
                f"{self.railway_barrier_gap} Meters",
            ],
            [
                self.power_grid_lines_stations_with_lyrx,
                "false",
                f"{self.power_grid_lines_barrier_gap} Meters",
            ],
            # [
            #     self.road_barrier_lyrx,
            #     "false",
            #     f"{self.road_barrier_gap} Meters",
            # ],
        ]
        print(f"Input barriers for RBC: {input_barriers_for_rbc}\n")

        return input_barriers_for_rbc

    def resolve_building_conflicts_1(self):
        """
        What:
            Resolves building conflicts using specified building and barrier features.
        """
        try:
            arcpy.env.referenceScale = "100000"
            input_buildings_rbc_1_new = [
                self.work_file_manager.extract_key_by_alias(
                    data=self.output_lyrx_features,
                    unique_alias="building_points",
                    key="lyrx_output",
                ),
                self.work_file_manager.extract_key_by_alias(
                    data=self.output_lyrx_features,
                    unique_alias="building_polygons",
                    key="lyrx_output",
                ),
            ]

            input_buildings_rbc_1 = [
                self.polygons_with_lyrx,
                self.building_squares_with_lyrx,
            ]

            print(f"Input buildings for RBC 1: {input_buildings_rbc_1}\n")
            arcpy.cartography.ResolveBuildingConflicts(
                in_buildings=input_buildings_rbc_1,
                invisibility_field="invisibility",
                in_barriers=self.barriers_for_rbc(),
                building_gap=f"{self.building_gap} Meters",
                minimum_size="1 Meters",
                hierarchy_field="hierarchy",
            )
        except Exception as e:
            print(f"Error in resolve_building_conflicts_1: {e}")
            raise

    def building_squares_and_polygons_to_keep_after_rbc_1(self):
        """
        Selects and retains building squares and polygons that are visible or hospital, churches or tourist cabins
        """

        self.work_file_manager.set_key_by_alias(
            data=self.output_lyrx_features,
            unique_alias="building_points",
            key="results_rbc_1",
            new_value=self.results_rbc_1_squares,
        )

        # Sql expression to select building squares that are visible + church, hospital, tourist cabin points
        sql_expression_resolve_building_conflicts_squares = (
            "(invisibility = 0) OR (symbol_val IN (1, 2, 3)) OR (byggtyp_nbr = 956)"
        )

        # Selecting building squares that are visible OR are hospitals/churches/touristcabins
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.input_building_points,
            expression=sql_expression_resolve_building_conflicts_squares,
            output_name=self.results_rbc_1_squares,
        )

        # Sql expression to keep only building polygons that are visible (0) after the tool has run
        sql_expression_resolve_building_conflicts_polygon = "invisibility = 0"

        # Selecting building polygons that are visible
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.input_building_polygons,
            expression=sql_expression_resolve_building_conflicts_polygon,
            output_name=self.results_rbc_1_polygons,
        )

    def transforming_invisible_polygons_to_points_and_then_to_squares(self):
        """
        What:
            Transforms invisible building polygons to points and then to squares.

        How:
            The invisible polygons are picked out using an expression. Then they are transformed to points
            using "Feature To Point". Polygon Processor is then used to transform the points to squares.
            These new squares are in the end merged with the squares (made from building points) from the
            RBC 1 result.

        Why:
            The polygons that are set invisible by Resolve Building Conflicts are in conflict with other building points and barriers,
            this means that even though they can be resized, there still is no space for them. Therefore, they are transformed to
            points to try to fit them in to the area they are in without having to remove them completely. These points (now squares)  later goes
            into a second round of RBC.
        """
        # Sql expression to keep only building polygons that have invisbility value 1 after the tool has run
        sql_expression_find_invisible_polygons = "invisibility = 1"

        # Selecting building polygons that are invisible
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.input_building_polygons,
            expression=sql_expression_find_invisible_polygons,
            output_name=self.invisible_polygons_after_rbc_1,
        )

        # Invisible building polygons are then transformed to points
        arcpy.management.FeatureToPoint(
            in_features=self.invisible_polygons_after_rbc_1,
            out_feature_class=self.invisible_polygons_to_points_after_rbc_1,
            point_location="INSIDE",
        )

        # Transforms all the building points to squares
        polygon_processor = PolygonProcessor(
            input_building_points=self.invisible_polygons_to_points_after_rbc_1,
            output_polygon_feature_class=self.building_polygons_to_points_and_then_squares_rbc_1,
            building_symbol_dimensions=self.building_symbol_dimension,
            symbol_field_name="symbol_val",
            index_field_name="OBJECTID",
        )
        polygon_processor.run()

        # Merging squares and polygons made to points, and then squares
        arcpy.management.Merge(
            inputs=[
                self.results_rbc_1_squares,
                self.building_polygons_to_points_and_then_squares_rbc_1,
            ],
            output=self.merged_squares_rbc1,
        )

    def calculating_symbol_val_and_nbr_for_squares(self):
        """
        What:
            Calculates and updates the `byggtyp_nbr` and `symbol_val` fields for squares

        How:
            Using Calculate Field with Python-expressions to update the fields.

        Why:
            The fields are updated because Polygon Processor does not work with the number -99,
            it is out of range.
        """
        # Features with symbol_val -99 get byggtyp_nbr 729
        code_block_symbol_val_to_nbr = (
            "def symbol_val_to_nbr(symbol_val, byggtyp_nbr):\n"
            "    if symbol_val == -99:\n"
            "        return 729\n"
            "    return byggtyp_nbr"
        )

        # Code block to update the symbol_val to reflect the new byggtyp_nbr
        code_block_update_symbol_val = (
            "def update_symbol_val(symbol_val):\n"
            "    if symbol_val == -99:\n"
            "        return 8\n"
            "    return symbol_val"
        )

        # Applying the symbol_val_to_nbr logic
        arcpy.CalculateField_management(
            in_table=self.merged_squares_rbc1,
            field="byggtyp_nbr",
            expression="symbol_val_to_nbr(!symbol_val!, !byggtyp_nbr!)",
            expression_type="PYTHON3",
            code_block=code_block_symbol_val_to_nbr,
        )

        # Applying the update_symbol_val logic
        arcpy.CalculateField_management(
            in_table=self.merged_squares_rbc1,
            field="symbol_val",
            expression="update_symbol_val(!symbol_val!)",
            expression_type="PYTHON3",
            code_block=code_block_update_symbol_val,
        )

    def adding_symbology_to_layers_being_used_for_rbc_2(self):
        """
        Applies symbology to building squares and polygons for use in RBC 2 processing.
        """
        # Building squares (from points, transformed to squares in the first function) that are kept after rbc 1
        custom_arcpy.apply_symbology(
            input_layer=self.merged_squares_rbc1,
            in_symbology_layer=self.building_squares_lyrx,
            output_name=self.adding_symbology_to_squares_going_into_rbc2,
        )

        # Building polygons kept after rbc 1
        custom_arcpy.apply_symbology(
            input_layer=self.results_rbc_1_polygons,
            in_symbology_layer=self.building_polygons_lyrx,
            output_name=self.adding_symbology_to_polygons_going_into_rbc2,
        )

    def resolve_building_conflicts_2(self):
        """
        Resolves building conflicts for the second RBC processing stage using specified building and barrier features.
        """
        print("Starting resolve building conflicts 2")

        input_buildings_rbc_2 = [
            self.adding_symbology_to_squares_going_into_rbc2,
            self.adding_symbology_to_polygons_going_into_rbc2,
        ]

        arcpy.cartography.ResolveBuildingConflicts(
            in_buildings=input_buildings_rbc_2,
            invisibility_field="invisibility",
            in_barriers=self.barriers_for_rbc(),
            building_gap=self.building_gap,
            minimum_size="1 meters",
            hierarchy_field="hierarchy",
        )

    def selecting_features_to_be_kept_after_rbc_2(self):
        """
        Selects and retains building squares and polygons based on visibility and symbol value criteria after the second RBC processing stage.
        """
        sql_expression_squares = (
            "(invisibility = 0) OR (symbol_val IN (1, 2, 3)) OR (byggtyp_nbr = 956)"
        )

        sql_expression_polygons = "invisibility = 0"

        # Selecting squares that should be kept after rbc 2
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.merged_squares_rbc1,
            expression=sql_expression_squares,
            output_name=self.squares_after_rbc2,
        )

        # Selecting polygons that should be kept after rbc 2
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.results_rbc_1_polygons,
            expression=sql_expression_polygons,
            output_name=self.polygons_after_rbc2,
        )

    def transforming_squares_back_to_points(self):
        """
        Transforms squares back into points.
        """
        # Squares from points are transformed back to points
        arcpy.management.FeatureToPoint(
            in_features=self.squares_after_rbc2,
            out_feature_class=self.squares_back_to_points_after_rbc2,
            point_location="INSIDE",
        )

    def assigning_final_names(self):
        """
        Copies the final squares and polygons to their respective output feature classes.
        """
        # Squares
        arcpy.management.CopyFeatures(
            self.squares_back_to_points_after_rbc2,
            self.output_points,
        )
        # Polygons
        arcpy.management.CopyFeatures(
            self.polygons_after_rbc2,
            self.output_polygons,
        )

    @partition_io_decorator(
        input_param_names=[
            "building_inputs",
            "barrier_inputs",
            "lyrx_files",
        ],
        output_param_names=["output_files"],
    )
    def run(self):
        arcpy.env.referenceScale = self.map_scale
        environment_setup.main()

        self.working_files_list_gdb = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.working_files_list_gdb,
        )

        self.working_files_list_lyrx = (
            self.work_file_manager_lyrx.setup_work_file_paths(
                instance=self,
                file_structure=self.working_files_list_lyrx,
                file_type="lyrx",
            )
        )

        # self.apply_symbology()
        self.apply_symbology_to_the_layers()
        self.resolve_building_conflicts_1()
        self.building_squares_and_polygons_to_keep_after_rbc_1()
        self.transforming_invisible_polygons_to_points_and_then_to_squares()
        self.calculating_symbol_val_and_nbr_for_squares()
        self.adding_symbology_to_layers_being_used_for_rbc_2()
        self.resolve_building_conflicts_2()
        self.selecting_features_to_be_kept_after_rbc_2()
        self.transforming_squares_back_to_points()
        self.assigning_final_names()

        self.work_file_manager.delete_created_files()


class ResolveBuildingConflictsPolygon:
    def __init__(
        self,
        input_list_of_dicts_data_structure: list[dict[str, str]] = None,
        root_file: str = None,
        output_building_polygons: str = None,
        # output_building_points: str = None,
        write_work_files_to_memory: bool = False,
        keep_work_files: bool = False,
    ):
        self.input_data = input_list_of_dicts_data_structure
        self.root_path = root_file
        self.output_building_polygons = output_building_polygons
        # self.output_building_points = output_building_points

        self.work_file_manager = WorkFileManager(
            unique_id=id(self),
            root_file=root_file,
            write_to_memory=write_work_files_to_memory,
            keep_files=keep_work_files,
        )

        self.feature_copies = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.input_data,
            add_key="feature_copy",
        )

        self.lyrx_outputs = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.feature_copies,
            add_key="lyrx_output",
            file_type="lyrx",
        )

        self.building_polygon_rbc_output = "building_polygon_rbc_output"
        self.invisible_polygons = "invisible_polygons"
        self.feature_to_points = "feature_to_points"

        self.gdb_files_list = [
            self.building_polygon_rbc_output,
            self.invisible_polygons,
            self.feature_to_points,
        ]

        self.gdb_files_list = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.gdb_files_list,
        )

    def copy_input_layers(self):
        def copy_input(
            input_feature: str = None,
            feature_copy: str = None,
        ):
            arcpy.management.CopyFeatures(
                in_features=input_feature,
                out_feature_class=feature_copy,
            )

        self.work_file_manager.list_contents(
            data=self.lyrx_outputs, title="Pre CopyFeatures"
        )
        self.work_file_manager.apply_to_structure(
            data=self.feature_copies,
            func=copy_input,
            input_feature="input_layer",
            feature_copy="feature_copy",
        )
        print("Copy Done")

    def apply_symbology(self):
        def apply_symbology(
            feature_copy: str = None,
            lyrx_file: str = None,
            output_name: str = None,
            grouped_lyrx: bool = False,
            target_layer_name: str = None,
        ):
            if grouped_lyrx:
                custom_arcpy.apply_symbology(
                    input_layer=feature_copy,
                    in_symbology_layer=lyrx_file,
                    output_name=output_name,
                    grouped_lyrx=True,
                    target_layer_name=target_layer_name,
                )
            else:
                custom_arcpy.apply_symbology(
                    input_layer=feature_copy,
                    in_symbology_layer=lyrx_file,
                    output_name=output_name,
                )

        self.work_file_manager.list_contents(
            data=self.lyrx_outputs, title="Pre Apply Symbology"
        )
        self.work_file_manager.apply_to_structure(
            data=self.lyrx_outputs,
            func=apply_symbology,
            feature_copy="feature_copy",
            lyrx_file="input_lyrx_feature",
            output_name="lyrx_output",
            grouped_lyrx="grouped_lyrx",
            target_layer_name="target_layer_name",
        )

    def resolve_building_conflicts(self):
        self.work_file_manager.list_contents(data=self.lyrx_outputs, title="Pre RBC")
        building_layer = self.work_file_manager.extract_key_by_alias(
            data=self.lyrx_outputs,
            unique_alias="building",
            key="lyrx_output",
        )

        barriers = [
            ["begrensningskurve", "false", "30 Meters"],
            ["railroad", "false", "30 Meters"],
            ["hospital_churches", "false", "30 Meters"],
            ["railroad_station", "false", "30 Meters"],
            ["power_grid_lines", "false", "30 Meters"],
            ["building", "false", "30 Meters"],
        ]

        resolved_barriers = [
            [
                self.work_file_manager.extract_key_by_alias(
                    data=self.lyrx_outputs,
                    unique_alias=alias,
                    key="lyrx_output",
                ),
                flag,
                gap,
            ]
            for alias, flag, gap in barriers
        ]

        arcpy.cartography.ResolveBuildingConflicts(
            in_buildings=building_layer,
            invisibility_field="invisibility",
            in_barriers=resolved_barriers,
            building_gap=f"{N100_Values.rbc_building_clearance_distance_m.value} Meters",
            minimum_size="1 meters",
        )

        arcpy.management.Copy(
            in_data=self.work_file_manager.extract_key_by_alias(
                data=self.lyrx_outputs,
                unique_alias="building",
                key="feature_copy",
            ),
            out_data=self.output_building_polygons,
        )

    def invisibility_selections(self):

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.building_polygon_rbc_output,
            expression="invisibility = 1",
            output_name=self.invisible_polygons,
        )

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.building_polygon_rbc_output,
            expression="invisibility = 0",
            output_name=self.output_building_polygons,
        )

        arcpy.management.FeatureToPoint(
            in_features=self.invisible_polygons,
            out_feature_class=self.feature_to_points,
        )

        arcpy.management.Copy(
            in_data=self.feature_to_points,
            out_data=self.output_building_points,
        )

    @partition_io_decorator(
        input_param_names=["input_list_of_dicts_data_structure"],
        output_param_names=[
            "output_building_polygons",
            # "output_building_points",
        ],
    )
    def run(self):
        arcpy.env.referenceScale = "100000"
        environment_setup.main()
        self.copy_input_layers()
        self.apply_symbology()
        self.resolve_building_conflicts()
        # self.invisibility_selections()


if __name__ == "__main__":
    input_data_structure = [
        {
            "unique_alias": "building_points",
            "input_feature": Building_N100.point_displacement_with_buffer___merged_buffer_displaced_points___n100_building.value,
            "lyrx_file": input_symbology.SymbologyN100.squares.value,
            "grouped_lyrx": False,
            "target_layer_name": "",
        },
        {
            "unique_alias": "building_polygons",
            "input_feature": Building_N100.polygon_resolve_building_conflicts___building_polygons_final___n100_building.value,
            "lyrx_file": input_symbology.SymbologyN100.building_polygon.value,
            "grouped_lyrx": False,
            "target_layer_name": "",
        },
        {
            "unique_alias": "road",
            "input_feature": Building_N100.data_preparation___unsplit_roads___n100_building.value,
            "lyrx_file": config.symbology_samferdsel,
            "grouped_lyrx": True,
            "target_layer_name": "N100_Samferdsel_senterlinje_veg_bru_L2",
        },
        {
            "unique_alias": "railroad",
            "input_feature": input_data.input_n100.Bane,
            "lyrx_file": config.symbology_samferdsel,
            "grouped_lyrx": True,
            "target_layer_name": "N100_Samferdsel_senterlinje_jernbane_terreng_sort_maske",
        },
        {
            "unique_alias": "railroad_station",
            "input_feature": Building_N100.data_preparation___railway_stations_to_polygons___n100_building.value,
            "lyrx_file": input_symbology.SymbologyN100.railway_station_squares.value,
            "grouped_lyrx": False,
            "target_layer_name": "",
        },
        {
            "unique_alias": "begrensningskurve",
            "input_feature": Building_N100.data_preparation___begrensningskurve_buffer_erase_2___n100_building.value,
            "lyrx_file": input_symbology.SymbologyN100.begrensningskurve_polygon.value,
            "grouped_lyrx": False,
            "target_layer_name": "",
        },
        {
            "unique_alias": "power_grid_lines",
            "input_feature": Building_N100.data_preparation___power_grid_lines___n100_building.value,
            "lyrx_file": config.symbology_samferdsel,
            "grouped_lyrx": True,
            "target_layer_name": "AnleggsLinje_maske_sort",
        },
    ]

    resolve_building_conflicts = ResolveBuildingConflictsPoints(
        input_list_of_dicts_data_structure=input_data_structure,
        building_inputs={
            "building_points": Building_N100.point_displacement_with_buffer___merged_buffer_displaced_points___n100_building.value,
            "building_polygons": Building_N100.polygon_resolve_building_conflicts___building_polygons_final___n100_building.value,
        },
        building_gap_distance=30,
        barrier_inputs={
            "begrensningskurve": Building_N100.data_preparation___begrensningskurve_buffer_erase_2___n100_building.value,
            "road": Building_N100.data_preparation___unsplit_roads___n100_building.value,
            "railway_station": Building_N100.data_preparation___railway_stations_to_polygons___n100_building.value,
            "railway": input_data.input_n100.Bane,
        },
        barrier_gap_distances={
            "begrensningskurve": 45,
            "road": 45,
            "railway_station": 45,
            "railway": 45,
        },
        building_symbol_dimension=N100_Symbology.building_symbol_dimensions.value,
        lyrx_files={
            "building_squares": input_symbology.SymbologyN100.squares.value,
            "building_polygons": input_symbology.SymbologyN100.building_polygon.value,
            "begrensningskurve": input_symbology.SymbologyN100.begrensningskurve_polygon.value,
            "road": input_symbology.SymbologyN100.road.value,
            "railway_station": input_symbology.SymbologyN100.railway_station_squares.value,
            "railway": input_symbology.SymbologyN100.railway.value,
        },
        base_path_for_lyrx=Building_N100.point_resolve_building_conflicts___lyrx_root___n100_building.value,
        root_path=Building_N100.point_resolve_building_conflicts___base_path_for_features___n100_building.value,
        output_files={
            "building_points": Building_N100.point_resolve_building_conflicts___POINT_OUTPUT___n100_building.value,
            "building_polygons": Building_N100.point_resolve_building_conflicts___POLYGON_OUTPUT___n100_building.value,
        },
        map_scale="100000",
    )

    resolve_building_conflicts.run()
    # resolve_building_conflicts.barriers_for_rbc()
