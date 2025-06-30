# Importing modules
import arcpy

# Importing custom modules
import config
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.partition_iterator import PartitionIterator
from custom_tools.decorators.partition_io_decorator import partition_io_decorator
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from custom_tools.general_tools.line_to_buffer_symbology import LineToBufferSymbology
from input_data import input_symbology
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values

from custom_tools.general_tools.file_utilities import WorkFileManager

# Importing environment settings
from env_setup import environment_setup

# Importing file manager
from file_manager.n100.file_manager_buildings import Building_N100

# Importing timing decorator

from custom_tools.decorators.timing_decorator import timing_decorator


@timing_decorator
def main():
    """
    What:
        This script processes spatial data to resolve conflicts between building polygons and nearby
        barriers such as roads, water bodies, hospitals, and churches.
        It transforms certain building polygons into points based on proximity to barriers and polygon size.

    How:
        The script begins by selecting roads, water features, and railways within 500 meters of building polygons,
        which serve as barriers. It processes hospital and church points into squares and applies the correct
        symbology. Symbology is then applied to the layers, including roads, water barriers, and building polygons.

        Building conflicts are resolved by ensuring appropriate clearances between building polygons and the
        selected barriers, including roads, hospitals, churches, and water features. Invisible building polygons,
        building polygons that intersect roads, and building polygons that are considered too small,
         are converted into points, while the rest of the building polygons are kept as they are.

    Why:
        The goal is to ensure accurate representation of building polygons in a geospatial dataset where
        buildings may conflict with barriers like roads or are too small for cartographic visibility.

    """

    environment_setup.main()
    roads_and_water_barriers_500_m_from_building_polygons()
    hospital_church_points_to_squares()
    apply_symbology_to_layers()
    resolve_building_conflicts_polygon()
    # resolve_building_conflict_building_polygon_old()
    invisible_building_polygons_to_point()
    intersecting_building_polygons_to_point()
    merging_invisible_intersecting_points()
    check_if_building_polygons_are_big_enough()
    small_building_polygons_to_points()


@timing_decorator
def roads_and_water_barriers_500_m_from_building_polygons():
    """
    Selects roads, water barriers, and railways that are within 500 meters of building polygons.
    """
    print("Selecting features 500 meter from building polygon ...")
    # Selecting begrensningskurve 500 meters from building polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.data_preparation___processed_begrensningskurve___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.polygon_propogate_displacement___building_polygons_after_displacement___n100_building.value,
        output_name=Building_N100.polygon_resolve_building_conflicts___begrensningskurve_500m_from_displaced_polygon___n100_building.value,
        search_distance="500 Meters",
    )

    # Selecting roads 500 meters from building polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.data_preparation___road_symbology_buffers___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.polygon_propogate_displacement___building_polygons_after_displacement___n100_building.value,
        output_name=Building_N100.polygon_resolve_building_conflicts___roads_500m_from_displaced_polygon___n100_building.value,
        search_distance="500 Meters",
    )

    # Selecting railway 500 meters from building polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.data_selection___railroad_tracks_n100_input_data___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.polygon_propogate_displacement___building_polygons_after_displacement___n100_building.value,
        output_name=Building_N100.polygon_resolve_building_conflicts___railroads_500m_from_displaced_polygon___n100_building.value,
        search_distance="500 Meters",
    )
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.data_preparation___power_grid_lines___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.polygon_propogate_displacement___building_polygons_after_displacement___n100_building.value,
        output_name=Building_N100.data_selection___power_grid_lines_500m_selection___n100_building.value,
        search_distance="500 Meters",
    )


@timing_decorator
def hospital_church_points_to_squares():
    """
    Selects hospital and church points, processes them into squares, and applies the appropriate symbology.
    """
    # Selecting hospital and churches from n50
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.data_selection___building_point_n50_input_data___n100_building.value,
        expression="byggtyp_nbr IN (970, 719, 671)",
        output_name=Building_N100.polygon_resolve_building_conflicts___hospital_church_points___n100_building.value,
    )

    # Adding a symbology value field based on NBR values
    arcpy.AddField_management(
        in_table=Building_N100.polygon_resolve_building_conflicts___hospital_church_points___n100_building.value,
        field_name="symbol_val",
        field_type="LONG",
    )

    arcpy.CalculateField_management(
        in_table=Building_N100.polygon_resolve_building_conflicts___hospital_church_points___n100_building.value,
        field="symbol_val",
        expression="determineVal(!byggtyp_nbr!)",
        expression_type="PYTHON3",
        code_block=N100_SQLResources.nbr_symbol_val_code_block.value,
    )

    # Polygon prosessor
    symbol_field_name = "symbol_val"
    index_field_name = "OBJECTID"

    print("Polygon prosessor...")
    polygon_process = PolygonProcessor(
        Building_N100.polygon_resolve_building_conflicts___hospital_church_points___n100_building.value,  # input
        Building_N100.polygon_resolve_building_conflicts___hospital_church_squares___n100_building.value,  # output
        N100_Symbology.building_symbol_dimensions.value,
        symbol_field_name,
        index_field_name,
    )
    polygon_process.run()

    # Applying symbology to polygonprocessed hospital and churches
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.polygon_resolve_building_conflicts___hospital_church_squares___n100_building.value,
        in_symbology_layer=input_symbology.SymbologyN100.building_polygon.value,
        output_name=Building_N100.polygon_resolve_building_conflicts___polygonprocessor_symbology___n100_building_lyrx.value,
    )


@timing_decorator
def apply_symbology_to_layers():
    """
    Applies symbology (lyrx files) to building polygons, roads, and water barriers.
    """
    print("Applying symbology ...")
    # Applying symbology to building polygons
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.polygon_propogate_displacement___building_polygons_after_displacement___n100_building.value,
        in_symbology_layer=input_symbology.SymbologyN100.building_polygon.value,
        output_name=Building_N100.polygon_resolve_building_conflicts___building_polygon___n100_building_lyrx.value,
    )
    # Applying symbology to roads
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.polygon_resolve_building_conflicts___roads_500m_from_displaced_polygon___n100_building.value,
        in_symbology_layer=input_symbology.SymbologyN100.road_buffer.value,
        output_name=Building_N100.polygon_resolve_building_conflicts___roads___n100_building_lyrx.value,
    )

    # Applying symbology to begrensningskurve (limiting curve)
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.polygon_resolve_building_conflicts___begrensningskurve_500m_from_displaced_polygon___n100_building.value,
        in_symbology_layer=input_symbology.SymbologyN100.begrensningskurve_polygon.value,
        output_name=Building_N100.polygon_resolve_building_conflicts___begrensningskurve___n100_building_lyrx.value,
    )

    # Applying symbology to railway
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.polygon_resolve_building_conflicts___railroads_500m_from_displaced_polygon___n100_building.value,
        in_symbology_layer=input_symbology.SymbologyN100.railway.value,
        output_name=Building_N100.polygon_resolve_building_conflicts___railway___n100_building_lyrx.value,
    )

    custom_arcpy.apply_symbology(
        input_layer=Building_N100.data_selection___power_grid_lines_500m_selection___n100_building.value,
        in_symbology_layer=config.symbology_samferdsel,
        output_name=Building_N100.polygon_resolve_building_conflicts___power_grid_lines___n100_building_lyrx.value,
        grouped_lyrx=True,
        target_layer_name="N100_Samferdsel_senterlinje_veg_anlegg_sort_maske",
    )


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


def resolve_building_conflicts_polygon():
    building = "building"
    railroad = "railroad"
    begrensningskurve = "begrensningskurve"
    power_grid_lines = "power_grid_lines"
    hospital_churches = "hospital_churches"
    railroad_station = "railroad_station"
    building_points = "building_points"

    inputs = {
        building: [
            "input",
            Building_N100.polygon_propogate_displacement___building_polygons_after_displacement___n100_building.value,
        ],
        railroad: [
            "context",
            Building_N100.polygon_resolve_building_conflicts___railroads_500m_from_displaced_polygon___n100_building.value,
        ],
        begrensningskurve: [
            "context",
            Building_N100.polygon_resolve_building_conflicts___begrensningskurve_500m_from_displaced_polygon___n100_building.value,
        ],
        power_grid_lines: [
            "context",
            Building_N100.data_selection___power_grid_lines_500m_selection___n100_building.value,
        ],
        hospital_churches: [
            "context",
            Building_N100.polygon_resolve_building_conflicts___hospital_church_squares___n100_building.value,
        ],
        railroad_station: [
            "context",
            Building_N100.data_preparation___railway_stations_to_polygons___n100_building.value,
        ],
    }

    outputs = {
        building: [
            "not_invisible_polygons_after_rbc",
            Building_N100.polygon_resolve_building_conflicts___after_rbc___n100_building.value,
        ],
        # building_points: [
        #     "invisible_polygons_to_points",
        #     Building_N100.polygon_resolve_building_conflicts___invisible_polygons_to_points___n100_building.value,
        # ],
    }

    input_data_structure = [
        {
            "unique_alias": building,
            "input_layer": (building, "input"),
            "input_lyrx_feature": input_symbology.SymbologyN100.building_polygon.value,
            "grouped_lyrx": False,
            "target_layer_name": None,
        },
        {
            "unique_alias": railroad,
            "input_layer": (railroad, "context"),
            "input_lyrx_feature": input_symbology.SymbologyN100.railway.value,
            "grouped_lyrx": False,
            "target_layer_name": None,
        },
        {
            "unique_alias": begrensningskurve,
            "input_layer": (begrensningskurve, "context"),
            "input_lyrx_feature": input_symbology.SymbologyN100.begrensningskurve_polygon.value,
            "grouped_lyrx": False,
            "target_layer_name": None,
        },
        {
            "unique_alias": power_grid_lines,
            "input_layer": (power_grid_lines, "context"),
            "input_lyrx_feature": config.symbology_samferdsel,
            "grouped_lyrx": True,
            "target_layer_name": "N100_Samferdsel_senterlinje_veg_anlegg_sort_maske",
        },
        {
            "unique_alias": hospital_churches,
            "input_layer": (hospital_churches, "context"),
            "input_lyrx_feature": input_symbology.SymbologyN100.building_polygon.value,
            "grouped_lyrx": False,
            "target_layer_name": None,
        },
        {
            "unique_alias": railroad_station,
            "input_layer": (railroad_station, "context"),
            "input_lyrx_feature": input_symbology.SymbologyN100.railway_station_squares.value,
            "grouped_lyrx": False,
            "target_layer_name": None,
        },
    ]

    resolve_building_conflicts_config = {
        "class": ResolveBuildingConflictsPolygon,
        "method": "run",
        "params": {
            "input_list_of_dicts_data_structure": input_data_structure,
            "root_file": Building_N100.polygon_resolve_building_conflicts___root_file___n100_building.value,
            "output_building_polygons": (building, "not_invisible_polygons_after_rbc"),
            # "output_building_points": (building_points, "invisible_polygons_to_points"),
        },
    }

    partition_rbc_polygon = PartitionIterator(
        alias_path_data=inputs,
        alias_path_outputs=outputs,
        custom_functions=[resolve_building_conflicts_config],
        root_file_partition_iterator=Building_N100.polygon_resolve_building_conflicts___partition_root_file___n100_building.value,
        dictionary_documentation_path=Building_N100.polygon_resolve_building_conflicts___begrensingskurve_docu___building_n100.value,
        feature_count=15_000,
        run_partition_optimization=False,
        search_distance="500 Meters",
    )
    partition_rbc_polygon.run()


@timing_decorator
def resolve_building_conflict_building_polygon_old():
    """
    Resolves conflicts among building polygons considering roads, water features, hospitals, and churches as barriers.
    This function resolves conflicts among building polygons by taking into account various barriers such as roads,
    water features, hospitals, and churches. To incorporate hospital and church points as barriers, these points are first
    transformed into polygons using the dimensions of their symbology.
    """

    # Resolving Building Conflicts for building polygons
    print("Resolving building conflicts ...")
    # Setting scale to 1: 100 000
    arcpy.env.referenceScale = "100000"

    # Barriers: roads, begrensningskurve, hospital and church squares
    input_barriers = [
        [
            Building_N100.polygon_resolve_building_conflicts___roads___n100_building_lyrx.value,
            "false",
            f"{N100_Values.rbc_barrier_clearance_distance_m.value} Meters",  # 30 Meters for all barriers
        ],
        [
            Building_N100.polygon_resolve_building_conflicts___begrensningskurve___n100_building_lyrx.value,
            "false",
            f"{N100_Values.rbc_barrier_clearance_distance_m.value} Meters",
        ],
        [
            Building_N100.polygon_resolve_building_conflicts___polygonprocessor_symbology___n100_building_lyrx.value,
            "false",
            f"{N100_Values.rbc_barrier_clearance_distance_m.value} Meters",
        ],
        [
            Building_N100.data_preparation___railway_stations_to_polygons_symbology___n100_building_lyrx.value,
            "false",
            f"{N100_Values.rbc_barrier_clearance_distance_m.value} Meters",
        ],
        [
            Building_N100.polygon_resolve_building_conflicts___railway___n100_building_lyrx.value,
            "false",
            f"{N100_Values.rbc_barrier_clearance_distance_m.value} Meters",
        ],
        [
            Building_N100.polygon_resolve_building_conflicts___power_grid_lines___n100_building_lyrx.value,
            "false",
            f"{N100_Values.rbc_barrier_clearance_distance_m.value} Meters",
        ],
    ]

    # Resolve Building Conflict with building polygons and barriers
    arcpy.cartography.ResolveBuildingConflicts(
        in_buildings=Building_N100.polygon_resolve_building_conflicts___building_polygon___n100_building_lyrx.value,
        invisibility_field="invisibility",
        in_barriers=input_barriers,
        building_gap=f"{N100_Values.rbc_building_clearance_distance_m.value} Meters",
        minimum_size="1 meters",
    )

    # Copying and assigning new name to layer
    arcpy.management.Copy(
        in_data=Building_N100.polygon_propogate_displacement___building_polygons_after_displacement___n100_building.value,
        out_data=Building_N100.polygon_resolve_building_conflicts___after_rbc___n100_building.value,
    )
    print("Finished")


@timing_decorator
def invisible_building_polygons_to_point():
    """
    Converts invisible building polygons to points and separates them from non-invisible polygons.
    """
    print("Transforming polygons marked with invisibility 1 to points ...")

    # Making new feature layer of polygons that is invisible
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.polygon_resolve_building_conflicts___after_rbc___n100_building.value,
        expression="invisibility = 1",
        output_name=Building_N100.polygon_resolve_building_conflicts___invisible_polygons_after_rbc___n100_building.value,
    )

    # Making new feature layer of polygons that is NOT invisible
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.polygon_resolve_building_conflicts___after_rbc___n100_building.value,
        expression="invisibility = 0",
        output_name=Building_N100.polygon_resolve_building_conflicts___not_invisible_polygons_after_rbc___n100_building.value,
    )

    # Polygon to point
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.polygon_resolve_building_conflicts___invisible_polygons_after_rbc___n100_building.value,
        out_feature_class=Building_N100.polygon_resolve_building_conflicts___invisible_polygons_to_points___n100_building.value,
    )

    print("Finished.")


@timing_decorator
def intersecting_building_polygons_to_point():
    """
    Identifies building polygons that intersects road and converts them into points.
    """
    print("Finding intersecting points... ")

    # Selecting buildings that DO NOT overlap with road buffer layer and will be kept as polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.polygon_resolve_building_conflicts___not_invisible_polygons_after_rbc___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.data_preparation___road_symbology_buffers___n100_building.value,
        inverted=True,  # Inverted
        output_name=Building_N100.polygon_resolve_building_conflicts___building_polygons_not_invisible_not_intersecting___n100_building.value,
    )

    # Selecting buildings that overlap with road buffer layer and will be transformed to points
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.polygon_resolve_building_conflicts___not_invisible_polygons_after_rbc___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.data_preparation___road_symbology_buffers___n100_building.value,
        inverted=False,
        output_name=Building_N100.polygon_resolve_building_conflicts___building_polygons_intersecting_road___n100_building.value,
    )

    # Transforming these polygons to points
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.polygon_resolve_building_conflicts___building_polygons_intersecting_road___n100_building.value,
        out_feature_class=Building_N100.polygon_resolve_building_conflicts___intersecting_polygons_to_points___n100_building.value,
    )


@timing_decorator
def merging_invisible_intersecting_points():
    """
    Merges points from intersecting building polygons and invisible polygons.
    """
    print("Merging points...")
    arcpy.management.Merge(
        inputs=[
            Building_N100.polygon_resolve_building_conflicts___intersecting_polygons_to_points___n100_building.value,
            Building_N100.polygon_resolve_building_conflicts___invisible_polygons_to_points___n100_building.value,
        ],
        output=Building_N100.polygon_resolve_building_conflicts___final_merged_points___n100_building.value,
    )


@timing_decorator
def check_if_building_polygons_are_big_enough():
    """
    Removes building polygons from the input layer that have a shape area smaller than
    a specified threshold (3200 square meters).
    """
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.polygon_resolve_building_conflicts___building_polygons_not_invisible_not_intersecting___n100_building.value,
        expression="Shape_Area >= 3200",
        output_name=Building_N100.polygon_resolve_building_conflicts___building_polygons_final___n100_building.value,
    )


@timing_decorator
def small_building_polygons_to_points():
    """
    Selects small building polygons based on a specified area threshold and transforms them into points.
    """

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.polygon_resolve_building_conflicts___building_polygons_not_invisible_not_intersecting___n100_building.value,
        expression="Shape_Area < 3200",
        output_name=Building_N100.polygon_resolve_building_conflicts___small_building_polygons___n100_building.value,
    )

    # Transforming small polygons to points
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.polygon_resolve_building_conflicts___small_building_polygons___n100_building.value,
        out_feature_class=Building_N100.polygon_resolve_building_conflicts___small_building_polygons_to_point___n100_building.value,
    )


if __name__ == "__main__":
    main()
