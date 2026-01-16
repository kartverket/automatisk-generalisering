# Importing packages
import arcpy

# Importing custom input files modules
from custom_tools.generalization_tools.building import (
    begrensningskurve_land_waterbodies,
)
from generalization.n100 import building
from input_data import input_n50
from input_data import input_n100
from input_data import input_other
from input_data import input_roads

# Importing custom modules
from file_manager.n100.file_manager_buildings import Building_N100
from file_manager.n100.file_manager_roads import Road_N100
from env_setup import environment_setup
import config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from custom_tools.general_tools.line_to_buffer_symbology import LineToBufferSymbology
from input_data.input_symbology import SymbologyN100
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values
from custom_tools.general_tools.partition_iterator import PartitionIterator
from custom_tools.generalization_tools.building.begrensningskurve_land_waterbodies import (
    BegrensningskurveLandWaterbodies,
)
from custom_tools.general_tools.study_area_selector import StudyAreaSelector
from custom_tools.general_tools.geometry_tools import GeometryValidator
from composition_configs import core_config, logic_config


@timing_decorator
def main():
    """
    What:
        Prepares the input data for future building generalization processes, does spatial selections and coverts.
    How:
        data_selection:
            Used for input datasets provided to the class. Is the focus of the processing. If you in a config want to use
            the partition selection of the original input data as an input this is the type which should be used.

        begrensningskurve_land_and_water_bodies:
            Creates a modified water boundary feature creating a polygon where an offset is erased of the land boundary
            depending on the size of the waterbody object, thin objects does not get this offset but wide waterbodies does.

        unsplit_roads_and_make_buffer:
            Unsplits the road feature to reduce the number of objects, reducing processing time.

        railway_station_points_to_polygons:
            Transforms the train station points to polygons representing their symbology size.

        adding_matrikkel_points_to_areas_that_are_no_longer_urban:
            Adds building points to the areas which no longer are urban areas in N100.

        selecting_n50_points_not_in_urban_areas:
            Making spatial selections of building points not intersecting with urban areas,
            except for churches and hospitals which are kept no matter what.

        polygon_selections_based_on_size:
            Selects building polygons based on their size (minimum 2500 m2) and converts small polygons to points.
    Why:
        Prepares the input data and files used in future processing steps.
    """

    environment_setup.main()
    data_selection()
    begrensningskurve_land_and_water_bodies()
    unsplit_roads_and_make_buffer()
    railway_station_points_to_polygons()
    selecting_power_grid_lines()
    selecting_urban_areas_by_sql()
    adding_matrikkel_points_to_areas_that_are_no_longer_urban()
    selecting_n50_points_not_in_urban_areas()
    adding_field_values_to_matrikkel()
    merge_building_points()
    reclassifying_polygon_values()
    polygon_selections_based_on_size()


@timing_decorator
def data_selection():
    """
    What:
        Selects and copies the input data for the building generalization process.
    How:
        input_output_file_dict takes a dictionary where the keys are the input data paths, and the values are the
        out paths for each data type. Depending on config.select_study_area is True or False it either copies the input
        data to the out paths, or does a spatial selection to the out path
    Why:
        Makes sure that the input data is never modified, and that all future I/O's use the same paths regardless if
        the script is run for global data or smaller subselection for logic testing.
    """
    print(input_roads.road_output_1)
    input_output_file_dict = {
        input_n100.BegrensningsKurve: Building_N100.data_selection___begrensningskurve_n100_input_data___n100_building.value,
        input_n100.ArealdekkeFlate: Building_N100.data_selection___land_cover_n100_input_data___n100_building.value,
        input_n100.VegSti: Building_N100.data_selection___road_n100_input_data___n100_building.value,
        input_n100.JernbaneStasjon: Building_N100.data_selection___railroad_stations_n100_input_data___n100_building.value,
        input_n100.Bane: Building_N100.data_selection___railroad_tracks_n100_input_data___n100_building.value,
        input_n50.ArealdekkeFlate: Building_N100.data_selection___land_cover_n50_input_data___n100_building.value,
        input_n50.BygningsPunkt: Building_N100.data_selection___building_point_n50_input_data___n100_building.value,
        input_n50.Grunnriss: Building_N100.data_selection___building_polygon_n50_input_data___n100_building.value,
        input_n50.TuristHytte: Building_N100.data_selection___tourist_hut_n50_input_data___n100_building.value,
        input_other.matrikkel_bygningspunkt: Building_N100.data_selection___matrikkel_input_data___n100_building.value,
        Road_N100.data_preparation___resolve_road_conflicts_displacement_feature___n100_road.value: Building_N100.data_selection___displacement_feature___n100_building.value,
        input_n100.AnleggsLinje: Building_N100.data_selection___anleggslinje___n100_building.value,
    }

    small_local_selection = "navn IN ('Asker', 'Oslo', 'Ringerike')"
    plot_area = "navn IN ('Asker', 'Bærum', 'Drammen', 'Frogn', 'Hole', 'Holmestrand', 'Horten', 'Jevnaker', 'Kongsberg', 'Larvik', 'Lier', 'Lunner', 'Modum', 'Nesodden', 'Oslo', 'Ringerike', 'Tønsberg', 'Øvre Eiker')"

    selector = StudyAreaSelector(
        input_output_file_dict=input_output_file_dict,
        selecting_file=input_n100.AdminFlate,
        selecting_sql_expression=small_local_selection,
        select_local=config.select_study_area,
    )

    selector.run()

    input_features_validation = {
        "begrensningskurve": Building_N100.data_selection___begrensningskurve_n100_input_data___n100_building.value,
        "land_cover": Building_N100.data_selection___land_cover_n100_input_data___n100_building.value,
        "roads": Building_N100.data_selection___road_n100_input_data___n100_building.value,
        "railroad_stations": Building_N100.data_selection___railroad_stations_n100_input_data___n100_building.value,
        "railroad_tracks": Building_N100.data_selection___railroad_tracks_n100_input_data___n100_building.value,
        "building_points": Building_N100.data_selection___building_point_n50_input_data___n100_building.value,
        "building_polygons": Building_N100.data_selection___building_polygon_n50_input_data___n100_building.value,
        "tourist_huts": Building_N100.data_selection___tourist_hut_n50_input_data___n100_building.value,
        "building_point_matrikkel": Building_N100.data_selection___matrikkel_input_data___n100_building.value,
        "road_displacement_feature": Building_N100.data_selection___displacement_feature___n100_building.value,
        "anleggslinje": Building_N100.data_selection___anleggslinje___n100_building.value,
    }

    data_validation = GeometryValidator(
        input_features=input_features_validation,
        output_table_path=Building_N100.data_preparation___geometry_validation___n100_building.value,
    )
    # data_validation.check_repair_sequence()

    begrensningskurve = "begrensningskurve"
    land_cover = "land_cover"
    roads = "roads"
    railroad_stations = "railroad_stations"
    railway_tracks = "railway_tracks"
    building_points = "building_points"
    building_polygons = "building_polygons"
    tourist_huts = "tourist_huts"
    building_point_matrikkel = "building_point_matrikkel"
    road_displacement_feature = "road_displacement_feature"
    anleggslinje = "anleggslinje"

    inputs = {
        begrensningskurve: [
            "input",
            Building_N100.data_selection___begrensningskurve_n100_input_data___n100_building.value,
        ],
        land_cover: [
            "input",
            Building_N100.data_selection___land_cover_n100_input_data___n100_building.value,
        ],
        roads: [
            "input",
            Building_N100.data_selection___road_n100_input_data___n100_building.value,
        ],
        railroad_stations: [
            "input",
            Building_N100.data_selection___railroad_stations_n100_input_data___n100_building.value,
        ],
        railway_tracks: [
            "input",
            Building_N100.data_selection___railroad_tracks_n100_input_data___n100_building.value,
        ],
        building_points: [
            "input",
            Building_N100.data_selection___building_point_n50_input_data___n100_building.value,
        ],
        building_polygons: [
            "input",
            Building_N100.data_selection___building_polygon_n50_input_data___n100_building.value,
        ],
        tourist_huts: [
            "input",
            Building_N100.data_selection___tourist_hut_n50_input_data___n100_building.value,
        ],
        building_point_matrikkel: [
            "input",
            Building_N100.data_selection___matrikkel_input_data___n100_building.value,
        ],
        road_displacement_feature: [
            "input",
            Building_N100.data_selection___displacement_feature___n100_building.value,
        ],
        anleggslinje: [
            "input",
            Building_N100.data_selection___anleggslinje___n100_building.value,
        ],
    }

    outputs = inputs

    input_features_validation = {
        "begrensningskurve": ("begrensningskurve", "input"),
        "land_cover": ("land_cover", "input"),
        "roads": ("roads", "input"),
        "railroad_stations": ("railroad_stations", "input"),
        "railroad_tracks": ("railroad_tracks", "input"),
        "building_points": ("building_points", "input"),
        "building_polygons": ("building_polygons", "input"),
        "tourist_huts": ("tourist_huts", "input"),
        "building_point_matrikkel": ("building_point_matrikkel", "input"),
        "road_displacement_feature": ("road_displacement_feature", "input"),
        "anleggslinje": ("anleggslinje", "input"),
    }

    process_data_validation = {
        "class": GeometryValidator,
        "method": "check_repair_sequence",
        "params": {
            "input_features": input_features_validation,
            "output_table_path": Building_N100.data_preparation___geometry_validation___n100_building.value,
        },
    }

    # partiotion_data_validation = PartitionIterator(
    #     alias_path_data=inputs,
    #     alias_path_outputs=outputs,
    #     custom_functions=[process_data_validation],
    #     root_file_partition_iterator=Building_N100.data_preparation___begrensningskurve_base___n100_building.value,
    #     dictionary_documentation_path=Building_N100.data_preparation___begrensingskurve_docu___building_n100.value,
    #     feature_count="5000",
    #     delete_final_outputs=False,
    # )

    # partiotion_data_validation.run()


@timing_decorator
def begrensningskurve_land_and_water_bodies():
    """
    What:
        Creates a modified water boundary feature creating a polygon where an offset is erased of the land boundary
        depending on the size of the waterbody object, thin objects does not get this offset but wide waterbodies does.
    How:
        Selects water features and creates a water feature polygon. Then depending on the ratio of ares to length
        it either appends the objects to the final feature or creates a modified water feature polygon.
    Why:
        This allows for building objects to graphically slightly move into some water features making it easier
        to keep buildings when placed between water and road features in future processing.
    """

    begrensningskurve = "begrensningskurve"
    land_cover = "land_cover"

    processed_begrensningskurve = "processed_begrensningskurve"

    begrensningskurve_input_config = core_config.PartitionInputConfig(
        entries=[
            core_config.InputEntry.processing_input(
                object=begrensningskurve,
                path=Building_N100.data_selection___begrensningskurve_n100_input_data___n100_building.value,
            ),
            core_config.InputEntry.processing_input(
                object=land_cover,
                path=Building_N100.data_selection___land_cover_n100_input_data___n100_building.value,
            ),
        ]
    )

    begrensningskurve_output_config = core_config.PartitionOutputConfig(
        entries=[
            core_config.OutputEntry.vector_output(
                object=begrensningskurve,
                tag=processed_begrensningskurve,
                path=Building_N100.data_preparation___processed_begrensningskurve___n100_building.value,
            )
        ]
    )

    begrensningskurve_io_config = core_config.PartitionIOConfig(
        input_config=begrensningskurve_input_config,
        output_config=begrensningskurve_output_config,
        documentation_directory=Building_N100.begrensningskurve_documentation_n100_building.value,
    )

    begrensningskurve_init_config = logic_config.BegrensningskurveLandWaterKwargs(
        input_begrensningskurve=core_config.InjectIO(
            object=begrensningskurve, tag="input"
        ),
        input_land_cover_features=core_config.InjectIO(object=land_cover, tag="input"),
        output_begrensningskurve=core_config.InjectIO(
            object=begrensningskurve, tag=processed_begrensningskurve
        ),
        water_feature_buffer_width=N100_Values.building_water_intrusion_distance_m.value,
        water_barrier_buffer_width=30,
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Building_N100.begrensingskurve_land_water___root_file___n100_building.value,
        ),
    )

    begrensningskurve_method_config = core_config.MethodEntriesConfig(
        entries=[
            core_config.ClassMethodEntryConfig(
                class_=BegrensningskurveLandWaterbodies,
                method=BegrensningskurveLandWaterbodies.run,
                init_params=begrensningskurve_init_config,
            )
        ]
    )

    begrensningskurve_partition_run_config = core_config.PartitionRunConfig(
        max_elements_per_partition=500_000,
        context_radius_meters=500,
    )

    partition_iterator_work_file_config = core_config.WorkFileConfig(
        root_file=Building_N100.data_preparation___begrensningskurve_base___n100_building.value,
        write_to_memory=True,
    )

    begrensningskurve_partition = PartitionIterator(
        partition_io_config=begrensningskurve_io_config,
        partition_method_inject_config=begrensningskurve_method_config,
        partition_iterator_run_config=begrensningskurve_partition_run_config,
        work_file_manager_config=partition_iterator_work_file_config,
    )
    begrensningskurve_partition.run()


@timing_decorator
def unsplit_roads_and_make_buffer():
    """
    Unsplits the road feature to reduce the number of objects, reducing processing time.
    """

    arcpy.CopyFeatures_management(
        in_features=Building_N100.data_selection___road_n100_input_data___n100_building.value,
        out_feature_class=Building_N100.data_preparation___unsplit_roads___n100_building.value,
    )

    road_lines_to_buffer_symbology = LineToBufferSymbology(
        logic_config.LineToBufferSymbologyKwargs(
            input_line=Building_N100.data_preparation___unsplit_roads___n100_building.value,
            output_line=Building_N100.data_preparation___road_symbology_buffers___n100_building.value,
            sql_selection_query=N100_SQLResources.new_road_symbology_size_sql_selection.value,
            work_file_manager_config=core_config.WorkFileConfig(
                root_file=Building_N100.data_preparation___root_file_line_symbology___n100_building.value
            ),
            buffer_distance_factor=1,
            buffer_distance_addition=0,
        )
    )
    road_lines_to_buffer_symbology.run()


@timing_decorator
def railway_station_points_to_polygons():
    """
    Transforms the train station points to polygons representing their symbology size.
    """
    # Railway stations from input data
    railway_stations = (
        Building_N100.data_selection___railroad_stations_n100_input_data___n100_building.value
    )

    # Adding symbol_val field
    arcpy.AddField_management(
        in_table=railway_stations,
        field_name="symbol_val",
        field_type="SHORT",
    )

    # Assigning symbol_val
    arcpy.CalculateField_management(
        in_table=railway_stations, field="symbol_val", expression="10"
    )

    # Polygon prosessor
    symbol_field_name = "symbol_val"
    index_field_name = "OBJECTID"

    print("Polygon prosessor...")
    polygon_process = PolygonProcessor(
        railway_stations,  # input
        Building_N100.data_preparation___railway_stations_to_polygons___n100_building.value,  # output
        N100_Symbology.building_symbol_dimensions.value,
        symbol_field_name,
        index_field_name,
    )
    polygon_process.run()

    # Applying symbology to polygonprocessed railwaystations
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.data_preparation___railway_stations_to_polygons___n100_building.value,
        in_symbology_layer=SymbologyN100.railway_station_squares.value,
        output_name=Building_N100.data_preparation___railway_stations_to_polygons_symbology___n100_building_lyrx.value,
    )


@timing_decorator
def selecting_power_grid_lines():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.data_selection___anleggslinje___n100_building.value,
        expression="objtype = 'LuftledningLH'",
        output_name=Building_N100.data_preparation___power_grid_lines___n100_building.value,
    )


@timing_decorator
def selecting_urban_areas_by_sql():
    """
    Creates a polygon of urban areas which was urban areas in N50 but are no longer urban areas in N100.
    """
    # Defining sql expression to select urban areas

    # Selecting urban areas from n100 using sql expression
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.data_selection___land_cover_n100_input_data___n100_building.value,
        expression=N100_SQLResources.urban_areas.value,
        output_name=Building_N100.data_preparation___urban_area_selection_n100___n100_building.value,
    )

    # Selecting urban areas from n50 using sql expression
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=Building_N100.data_selection___land_cover_n50_input_data___n100_building.value,
        expression=N100_SQLResources.urban_areas.value,
        output_name=Building_N100.data_preparation___urban_area_selection_n50___n100_building.value,
    )

    # Creating a buffer of the urban selection of n100 to take into account symbology
    arcpy.PairwiseBuffer_analysis(
        in_features=Building_N100.data_preparation___urban_area_selection_n100___n100_building.value,
        out_feature_class=Building_N100.data_preparation___urban_area_selection_n100_buffer___n100_building.value,
        buffer_distance_or_field=f"{N100_Values.buffer_clearance_distance_m.value} Meters",
        method="PLANAR",
    )

    # Removing areas from n50 urban areas from the buffer of n100 urban areas resulting in areas in n100 which no longer are urban
    arcpy.PairwiseErase_analysis(
        in_features=Building_N100.data_preparation___urban_area_selection_n50___n100_building.value,
        erase_features=Building_N100.data_preparation___urban_area_selection_n100_buffer___n100_building.value,
        out_feature_class=Building_N100.data_preparation___no_longer_urban_areas___n100_building.value,
    )


@timing_decorator
def adding_matrikkel_points_to_areas_that_are_no_longer_urban():
    """
    Adds building points to the areas which no longer are urban areas in N100.
    """
    # Selecting matrikkel building points in areas that were urban in n50, but are no longer urban in n100
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.data_selection___matrikkel_input_data___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.data_preparation___no_longer_urban_areas___n100_building.value,
        output_name=Building_N100.data_preparation___matrikkel_points___n100_building.value,
    )


@timing_decorator
def selecting_n50_points_not_in_urban_areas():
    """
    Making spatial selections of building points not intersecting with urban areas,
    except for churches and hospitals which are kept no matter what.
    """
    # Selecting n50 so they are not in urban areas
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.data_selection___building_point_n50_input_data___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.data_preparation___urban_area_selection_n100_buffer___n100_building.value,
        output_name=Building_N100.data_preparation___n50_points___n100_building.value,
        inverted=True,
    )

    # Making sure we are not loosing churches or hospitals
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.data_selection___building_point_n50_input_data___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.data_preparation___urban_area_selection_n100_buffer___n100_building.value,
        output_name=Building_N100.data_preparation___n50_points_in_urban_areas___n100_building.value,
    )

    sql_church_hospitals = "byggtyp_nbr IN (970, 719, 671)"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.data_preparation___n50_points_in_urban_areas___n100_building.value,
        expression=sql_church_hospitals,
        output_name=Building_N100.data_preparation___churches_and_hospitals_in_urban_areas___n100_building.value,
    )


@timing_decorator
def adding_field_values_to_matrikkel():
    """
    Adds byggtyp_nbr fieldto matrikkel building points and poplates it based on existing bygningstype values.
    """

    # Adding transferring the NBR value to the matrikkel building points
    arcpy.AddField_management(
        in_table=Building_N100.data_preparation___matrikkel_points___n100_building.value,
        field_name="byggtyp_nbr",
        field_type="LONG",
    )
    arcpy.CalculateField_management(
        in_table=Building_N100.data_preparation___matrikkel_points___n100_building.value,
        field="byggtyp_nbr",
        expression="!bygningstype!",
    )


@timing_decorator
def merge_building_points():
    """
    Merging building points to a single feature.
    """

    arcpy.management.Merge(
        inputs=[
            Building_N100.data_preparation___n50_points___n100_building.value,
            Building_N100.data_preparation___matrikkel_points___n100_building.value,
            Building_N100.data_preparation___churches_and_hospitals_in_urban_areas___n100_building.value,
            Building_N100.data_selection___tourist_hut_n50_input_data___n100_building.value,
        ],
        output=Building_N100.data_preparation___merged_building_points___n100_building.value,
    )


@timing_decorator
def reclassifying_polygon_values():
    """
    Reclassifies the values of hospitals and churches in the specified polygon layer to a new value (729), corresponding to "other buildings".
    """

    # Reclassify the hospitals and churches to NBR value 729 ("other buildings" / "andre bygg")
    reclassify_hospital_church_polygons = (
        "def reclassify(nbr):\n"
        "    mapping = {970: 729, 719: 729, 671: 729}\n"
        "    return mapping.get(nbr, nbr)"
    )

    arcpy.CalculateField_management(
        in_table=Building_N100.data_selection___building_polygon_n50_input_data___n100_building.value,
        field="byggtyp_nbr",
        expression="reclassify(!byggtyp_nbr!)",
        expression_type="PYTHON3",
        code_block=reclassify_hospital_church_polygons,
    )


@timing_decorator
def polygon_selections_based_on_size():
    """
    Selects building polygons based on their size (minimum 2500 m2) and converts small polygons to points.
    """

    # Selecting only building polygons over 2500 (the rest will be transformed to points due to size)
    sql_expression_too_small_polygons = (
        f"Shape_Area < {N100_Values.minimum_selection_building_polygon_size_m2.value}"
    )
    sql_expression_correct_size_polygons = (
        f"Shape_Area >= {N100_Values.minimum_selection_building_polygon_size_m2.value}"
    )

    # Polygons over or equal to 2500 Square Meters are selected
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.data_selection___building_polygon_n50_input_data___n100_building.value,
        expression=sql_expression_correct_size_polygons,
        output_name=Building_N100.data_preparation___polygons_that_are_large_enough___n100_building.value,
    )

    # Polygons under 2500 Square Meters are selected
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=Building_N100.data_selection___building_polygon_n50_input_data___n100_building.value,
        expression=sql_expression_too_small_polygons,
        output_name=Building_N100.data_preparation___polygons_that_are_too_small___n100_building.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # Transforming small building polygons into points
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.data_preparation___polygons_that_are_too_small___n100_building.value,
        out_feature_class=Building_N100.data_preparation___points_created_from_small_polygons___n100_building.value,  # Sent to polygon to point - to get merged as an additional input
    )


if __name__ == "__main__":
    main()
