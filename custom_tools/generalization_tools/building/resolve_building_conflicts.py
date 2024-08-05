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
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.decorators.partition_io_decorator import partition_io_decorator


class ResolveBuildingConflicts:
    def __init__(
        self,
        building_inputs: Dict[str, str],
        building_gap_distance: int,
        barrier_inputs: Dict[str, str],
        barrier_gap_distances: Dict[str, int],
        building_symbol_dimension: Dict[int, tuple],
        lyrx_files: Dict[str, str],
        base_path_for_lyrx: str,
        base_path_for_features: str,
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

        # Barrier inputs
        self.input_road_barrier = barrier_inputs["road"]
        self.input_railway_barrier = barrier_inputs["railway"]
        self.input_railway_station_barrier = barrier_inputs["railway_station"]
        self.input_begrensningskurve_barrier = barrier_inputs["begrensningskurve"]

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

        # Output files
        self.output_points = output_files["building_points"]
        self.output_polygons = output_files["building_polygons"]

        self.work_file_manager_gdb = WorkFileManager(
            unique_id=id(self),
            root_file=base_path_for_features,
            write_to_memory=write_work_files_to_memory,
            keep_files=keep_work_files,
        )

        self.work_file_manager_lyrx = WorkFileManager(
            unique_id=id(self),
            root_file=base_path_for_lyrx,
            write_to_memory=write_work_files_to_memory,
            keep_files=keep_work_files,
        )

        # GDB Work Files
        self.points_to_squares = "points_to_squares"
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
            self.points_to_squares,
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
            self.adding_symbology_to_squares_going_into_rbc2,
            self.adding_symbology_to_polygons_going_into_rbc2,
        ]

        self.working_files_list = []

        # Feature base path
        self.base_path_for_features = base_path_for_features

        # Lyrx base path
        self.lyrx_base_path = base_path_for_lyrx

        # ========================================
        #                                       LOGICS
        # ========================================

    @timing_decorator
    def building_points_to_squares(self):
        # Transforms all the building points to squares
        polygon_processor = PolygonProcessor(
            input_building_points=self.input_building_points,
            output_polygon_feature_class=self.points_to_squares,
            building_symbol_dimensions=self.building_symbol_dimension,
            symbol_field_name="symbol_val",
            index_field_name="OBJECTID",
        )
        polygon_processor.run()

        print("Polygon processor is done")

    @timing_decorator
    def apply_symbology_to_the_layers(self):
        print("Now starting to apply symbology to layers")
        features_for_apply_symbology = [
            {
                "input_layer": self.points_to_squares,
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
        ]

        # Loop over the symbology configurations and apply the function
        for symbology_config in features_for_apply_symbology:
            print("Now starting to apply symbology to layer")
            print(f"{symbology_config['input_layer']}\n")
            custom_arcpy.apply_symbology(
                input_layer=symbology_config["input_layer"],
                in_symbology_layer=symbology_config["in_symbology_layer"],
                output_name=symbology_config["output_name"],
            )

    def barriers_for_rbc(self):
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
        ]

        return input_barriers_for_rbc

    @timing_decorator
    def resolve_building_conflicts_1(self):
        try:
            arcpy.env.referenceScale = "100000"
            input_buildings_rbc_1 = [
                self.polygons_with_lyrx,
                self.building_squares_with_lyrx,
            ]
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

    @timing_decorator
    def building_squares_and_polygons_to_keep_after_rbc_1(self):
        # Sql expression to select building squares that are visible + church and hospital points
        sql_expression_resolve_building_conflicts_squares = (
            "(invisibility = 0) OR (BYGGTYP_NBR IN (970, 719, 671))"
        )
        # Selecting building squares that are visible OR are hospitals/churches
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.points_to_squares,
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

    @timing_decorator
    def transforming_invisible_polygons_to_points_and_then_to_squares(self):
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

    @timing_decorator
    def calculating_symbol_val_and_nbr_for_squares(self):
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

    @timing_decorator
    def adding_symbology_to_layers_being_used_for_rbc_2(self):
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

    @timing_decorator
    def resolve_building_conflicts_2(self):
        print("Starting resolve building conflicts 2")
        arcpy.env.referenceScale = "100000"

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

    @timing_decorator
    def selecting_features_to_be_kept_after_rbc_2(self):
        sql_expression_squares = "(invisibility = 0) OR (symbol_val IN (1, 2, 3))"

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

    @timing_decorator
    def transforming_squares_back_to_points(self):
        # Squares from points are transformed back to points
        arcpy.management.FeatureToPoint(
            in_features=self.squares_after_rbc2,
            out_feature_class=self.squares_back_to_points_after_rbc2,
            point_location="INSIDE",
        )

    @timing_decorator
    def assigning_final_names(self):
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

    @timing_decorator
    def adding_files_to_working_list(self):
        self.working_files_list.extend(
            [
                f"{self.base_path_for_features}points_to_squares",
                f"{self.lyrx_base_path}building_squares_with_lyrx.lyrx",
                f"{self.lyrx_base_path}polygons_with_lyrx.lyrx",
                f"{self.lyrx_base_path}roads_with_lyrx.lyrx",
                f"{self.lyrx_base_path}begrensningskurve_with_lyrx.lyrx",
                f"{self.lyrx_base_path}railway_with_lyrx.lyrx",
                f"{self.lyrx_base_path}railway_stations_with_lyrx.lyrx",
                f"{self.base_path_for_features}results_rbc_1_squares",
                f"{self.base_path_for_features}results_rbc_1_polygons",
                f"{self.base_path_for_features}invisible_polygons_after_rbc_1",
                f"{self.base_path_for_features}invisible_polygons_to_points_after_rbc_1",
                f"{self.base_path_for_features}building_polygons_to_points_and_then_squares_rbc_1",
                f"{self.base_path_for_features}merged_squares_rbc1",
                f"{self.lyrx_base_path}adding_symbology_to_squares_going_into_rbc2.lyrx",
                f"{self.lyrx_base_path}adding_symbology_to_polygons_going_into_rbc2.lyrx",
                f"{self.base_path_for_features}squares_back_to_points_after_rbc2"
                f"{self.base_path_for_features}squares_after_rbc2",
                f"{self.base_path_for_features}polygons_after_rbc2",
                self.points_to_squares,
            ]
        )

    @timing_decorator
    def delete_working_files(self, *file_paths):
        """
        Deletes multiple feature classes or files.
        """
        for file_path in file_paths:
            self.delete_feature_class(file_path)
            print(f"Deleted file: {file_path}")

    @staticmethod
    def delete_feature_class(feature_class_path):
        """
        Deletes a feature class if it exists.
        """
        if arcpy.Exists(feature_class_path):
            arcpy.management.Delete(feature_class_path)

    @partition_io_decorator(
        input_param_names=[
            "building_inputs",
            "barrier_inputs",
            "lyrx_files",
        ],
        output_param_names=["output_files"],
    )
    def run(self):
        environment_setup.main()

        self.work_file_manager_gdb.setup_work_file_paths(
            instance=self,
            file_names=self.working_files_list_gdb,
        )

        self.work_file_manager_lyrx.setup_work_file_paths_lyrx(
            instance=self,
            file_names=self.working_files_list_lyrx,
        )

        for file in self.working_files_list_gdb:
            print(f"Working file: {file}")

        for file in self.working_files_list_lyrx:
            print(f"Working file: {file}")

        self.building_points_to_squares()
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
        # self.adding_files_to_working_list()
        # self.delete_working_files(self.working_files_list)

        self.work_file_manager_gdb.cleanup_files(
            [self.working_files_list_gdb, self.working_files_list_lyrx]
        )


if __name__ == "__main__":
    resolve_building_conflicts = ResolveBuildingConflicts(
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
        base_path_for_features=Building_N100.point_resolve_building_conflicts___base_path_for_features___n100_building.value,
        output_files={
            "building_points": Building_N100.point_resolve_building_conflicts___POINT_OUTPUT___n100_building.value,
            "building_polygons": Building_N100.point_resolve_building_conflicts___POLYGON_OUTPUT___n100_building.value,
        },
    )

    resolve_building_conflicts.run()
