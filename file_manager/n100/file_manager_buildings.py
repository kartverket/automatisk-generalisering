# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager


# Initialize BaseFileManager
scale = global_config.scale_n100
object_name = global_config.object_bygning
file_manager = BaseFileManager(scale=scale, object_name=object_name)


# All scripts
data_selection = "data_selection"
data_preparation = "data_preparation"
simplify_polygons = "simplify_polygons"
polygon_propogate_displacement = "polygon_propogate_displacement"
polygon_resolve_building_conflicts = "polygon_resolve_building_conflicts"
polygon_to_point = "polygon_to_point"
line_to_buffer_symbology = "line_to_buffer_symbology"
calculating_polygon_values = "calculating_polygon_values"
calculate_point_values = "calculate_point_values"
point_propagate_displacement = "point_propagate_displacement"
removing_points_and_erasing_polygons_in_water_features = (
    "removing_points_and_erasing_polygons_in_water_features"
)
removing_overlapping_polygons_and_points = "removing_overlapping_polygons_and_points"
hospital_church_clusters = "hospital_church_clusters"
point_displacement_with_buffer = "point_displacement_with_buffer"
point_resolve_building_conflicts = "point_resolve_building_conflicts"
finalizing_buildings = "finalizing_buildings"
data_cleanup = "data_cleanup"


# Additional names
overview = "overview"

# TO BE DELETED

iteration = "iteration"
begrensingskurve_land_water = "begrensingskurve_land_water"


class Building_N100(Enum):

    """
    An enumeration for building-related geospatial data file paths within the N100 scale and building object context.

    Utilizes the BaseFileManager to generate standardized file paths for geodatabase files, general files, and layer files,
    tailored to building data preparation and analysis tasks.

    Example Syntaxes:
        - For Geodatabase (.gdb) Files:
            the_file_name_of_the_script___the_description_of_the_file___n100_building = file_manager.generate_file_name_gdb(
                script_source_name="the_file_name_of_the_script",
                description="the_description_of_the_file"
            )

        - For General Files (e.g., .txt, .csv):
            the_file_name_of_the_script___the_description_of_the_file___n100_building_filetype_extension = file_manager.generate_file_name_general_files(
                script_source_name="the_file_name_of_the_script",
                description="the_description_of_the_file",
                file_type="filetype_extension"
            )

        - For ArcGIS Layer Files (.lyrx):
            the_file_name_of_the_script___the_description_of_the_file___n100_building_lyrx = file_manager.generate_file_name_lyrx(
                script_source_name="the_file_name_of_the_script",
                description="the_description_of_the_file"
            )

    These examples show how to utilize the BaseFileManager's methods to generate file paths for different types of files,
    reflecting the specific needs and naming conventions of building data management within the project.


    """

    # ========================================
    #                                ADDITIONAL FILES
    # ========================================

    overview__runtime_all_building_functions__n100 = (
        file_manager.generate_file_name_general_files(
            script_source_name=overview,
            description="runtime_all_building_functions",
            file_type="txt",
        )
    )

    # ========================================
    #                                DATA PREPARATION
    # ========================================

    data_selection___begrensningskurve_n100_input_data___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="begrensningskurve_n100_input_data",
        )
    )

    data_selection___land_cover_n100_input_data___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="land_cover_n100_input_data",
        )
    )

    data_selection___land_cover_n50_input_data___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="land_cover_n50_input_data",
        )
    )

    data_selection___road_n100_input_data___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="road_n100_input_data",
        )
    )

    data_selection___building_point_n50_input_data___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="building_point_n50_input_data",
        )
    )

    data_selection___building_polygon_n50_input_data___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="building_polygon_n50_input_data",
        )
    )

    data_selection___tourist_hut_n50_input_data___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="tourist_hut_n50_input_data",
        )
    )

    data_selection___railroad_stations_n100_input_data___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="railroad_stations_n100_input_data",
        )
    )

    data_selection___railroad_tracks_n100_input_data___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="railroad_tracks_n100_input_data",
        )
    )

    data_selection___matrikkel_input_data___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="matrikkel_input_data",
        )
    )

    data_selection___displacement_feature___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="displacement_feature",
        )
    )

    data_preparation___geometry_validation___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="geometry_validation",
        )
    )

    data_preparation___begrensingskurve_docu___building_n100 = (
        file_manager.generate_file_name_general_files(
            script_source_name=data_preparation,
            description="begrensingskurve_docu",
            file_type="json",
        )
    )

    data_preparation___begrensningskurve_base___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="begrensningskurve_base",
        )
    )

    data_preparation___processed_begrensningskurve___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="processed_begrensningskurve",
        )
    )

    data_preparation___waterfeatures_from_begrensningskurve_rivers___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="waterfeatures_from_begrensningskurve_rivers",
        )
    )

    data_preparation___waterfeatures_from_begrensningskurve_rivers_buffer___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=data_preparation,
        description="waterfeatures_from_begrensningskurve_rivers_buffer",
    )

    data_preparation___begrensningskurve_buffer_erase_2___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="begrensningskurve_buffer_erase_2",
        )
    )

    data_preparation___unsplit_roads___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="unsplit_roads",
        )
    )

    data_preparation___road_symbology_buffers___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="road_symbology_buffers",
        )
    )

    data_preparation___root_file_line_symbology___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="root_file_line_symbology",
        )
    )

    data_preparation___urban_area_selection_n100___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="urban_area_selection_n100",
        )
    )

    data_preparation___urban_area_selection_n50___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="urban_area_selection_n50",
        )
    )

    data_preparation___urban_area_selection_n100_buffer___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="urban_area_selection_n100_buffer",
        )
    )

    data_preparation___no_longer_urban_areas___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="no_longer_urban_areas",
        )
    )

    data_preparation___matrikkel_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="matrikkel_points",
        )
    )

    data_preparation___n50_points___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=data_preparation,
        description="n50_points",
    )

    data_preparation___grunnriss_copy___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="grunnriss_copy",
        )
    )

    data_preparation___polygons_that_are_large_enough___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="polygons_that_are_large_enough",
        )
    )

    data_preparation___polygons_that_are_too_small___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="polygons_that_are_too_small",
        )
    )

    data_preparation___points_created_from_small_polygons___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="points_created_from_small_polygons",
        )
    )

    data_preperation___matrikkel_n50_touristcabins_points_merged___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="matrikkel_n50_points_touristcabins_merged",
        )
    )

    data_preparation___n50_polygons___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="n50_polygons",
        )
    )

    data_preparation___n50_points_in_urban_areas___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="n50_points_in_urban_areas",
        )
    )

    data_preparation___churches_and_hospitals_in_urban_areas___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="churches_and_hospitals_in_urban_areas",
        )
    )

    data_preparation___railway_stations_to_polygons___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="railway_stations_to_polygons",
        )
    )

    data_preparation___railway_stations_to_polygons_symbology___n100_building_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=data_preparation,
            description="railway_stations_to_polygons_symbology",
        )
    )

    data_preparation___railway_station_points_from_n100___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="railway_station_points_from_n100",
        )
    )

    # ========================================
    #                              begrensingskurve_land_water
    # ========================================

    begrensingskurve_land_water___root_file___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=begrensingskurve_land_water,
            description="root_file",
        )
    )

    begrensingskurve_land_water___begrensingskurve_buffer_in_water___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=begrensingskurve_land_water,
            description="begrensingskurve_buffer_in_water",
        )
    )

    # ========================================
    #                      CALCULATE POINT VALUES
    # ========================================

    calculate_point_values___points_going_into_propagate_displacement___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=calculate_point_values,
        description="points_going_into_propagate_displacement",
    )

    calculate_point_values___selection_building_points_with_undefined_nbr_values___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=calculate_point_values,
        description="selection_building_points_with_undefined_nbr_values",
    )

    calculate_point_values___building_points_with_undefined_nbr_values___n100_building = file_manager.generate_file_name_general_files(
        script_source_name=calculate_point_values,
        description="building_points_with_undefined_nbr_values",
        file_type="txt",
    )

    # ========================================
    #                      CALCULATE POLYGON VALUES
    # ========================================

    calculate_polygon_values___final___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=calculating_polygon_values,
            description="final",
        )
    )

    # ========================================
    #                              POLYGON TO POINT
    # ========================================

    polygon_to_point___merged_points_final___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_to_point,
            description="merged_points_final",
        )
    )

    # ========================================
    #                              LINE TO BUFFER SYMBOLOGY
    # ========================================
    line_to_buffer_symbology___test___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=line_to_buffer_symbology,
            description="test",
        )
    )

    line_to_buffer_symbology___root_file___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=line_to_buffer_symbology,
            description="root_file",
        )
    )

    line_to_buffer_symbology___buffer_displaced_building_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=line_to_buffer_symbology,
            description="buffer_displaced_building_points",
        )
    )

    line_to_buffer_symbology___root_buffer_displaced___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=line_to_buffer_symbology,
            description="root_buffer_displaced",
        )
    )

    # ========================================
    #                              SIMPLIFY POLYGONS
    # ========================================

    simplify_polygons___aggregated_polygons_to_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=simplify_polygons,
            description="aggregated_polygons_to_points",
        )
    )

    simplify_polygons___not_intersect_aggregated_and_original_polygon___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_to_point,
        description="not_intersect_aggregated_and_original_polygon",
    )

    simplify_polygons___small_gaps___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=simplify_polygons,
            description="small_gaps",
        )
    )

    simplify_polygons___simplify_building_1___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=simplify_polygons,
            description="simplify_building_1",
        )
    )

    simplify_polygons___simplify_building_2___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=simplify_polygons,
            description="simplify_building_2",
        )
    )

    simplify_polygons___simplify_polygon___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=simplify_polygons,
            description="simplify_polygon",
        )
    )

    simplify_polygons___spatial_join_polygons___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=simplify_polygons,
            description="spatial_join_polygons",
        )
    )

    # ========================================
    #                  POLYGON PROPOATE DISPLACEMENT
    # ========================================

    polygon_propogate_displacement___pre_displacement___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_propogate_displacement,
            description="pre_displacement",
        )
    )

    polygon_propogate_displacement___building_polygons_after_displacement___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_propogate_displacement,
        description="building_polygons_after_displacement",
    )

    # ========================================
    #                  POLYGON RESOLVE BUILDING CONFLICT
    # ========================================

    polygon_resolve_building_conflicts___begrensningskurve_500m_from_displaced_polygon___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_resolve_building_conflicts,
        description="begrensningskurve_500m_from_displaced_polygon",
    )
    polygon_resolve_building_conflicts___roads_500m_from_displaced_polygon___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_resolve_building_conflicts,
        description="roads_500m_from_displaced_polygon",
    )

    polygon_resolve_building_conflicts___railroads_500m_from_displaced_polygon___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_resolve_building_conflicts,
        description="railroads_500m_from_displaced_polygon",
    )

    polygon_resolve_building_conflicts___building_polygon___n100_building_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=polygon_resolve_building_conflicts,
            description="building_polygon",
        )
    )

    polygon_resolve_building_conflicts___roads___n100_building_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=polygon_resolve_building_conflicts,
            description="roads",
        )
    )

    polygon_resolve_building_conflicts___begrensningskurve___n100_building_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=polygon_resolve_building_conflicts,
            description="begrensningskurve",
        )
    )

    polygon_resolve_building_conflicts___after_rbc___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_resolve_building_conflicts,
            description="after_rbc",
        )
    )

    polygon_resolve_building_conflicts___hospital_church_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_resolve_building_conflicts,
            description="hospital_church_points",
        )
    )

    polygon_resolve_building_conflicts___hospital_church_squares___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_resolve_building_conflicts,
            description="hospital_church_squares",
        )
    )

    polygon_resolve_building_conflicts___polygonprocessor_symbology___n100_building_lyrx = file_manager.generate_file_name_lyrx(
        script_source_name=polygon_resolve_building_conflicts,
        description="polygonprocessor_symbology",
    )

    polygon_resolve_building_conflicts___invisible_polygons_after_rbc___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_resolve_building_conflicts,
        description="invisible_polygons_after_rbc",
    )

    polygon_resolve_building_conflicts___not_invisible_polygons_after_rbc___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_resolve_building_conflicts,
        description="not_invisible_polygons_after_rbc",
    )

    polygon_resolve_building_conflicts___invisible_polygons_to_points___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_resolve_building_conflicts,
        description="invisible_polygons_to_points",
    )

    polygon_resolve_building_conflicts___road_buffer_selection___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_resolve_building_conflicts,
            description="road_buffer_selection",
        )
    )

    polygon_resolve_building_conflicts___road_buffers___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_resolve_building_conflicts,
            description="road_buffers",
        )
    )

    polygon_resolve_building_conflicts___building_polygons_final___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_resolve_building_conflicts,
            description="building_polygons_final",
        )
    )

    polygon_resolve_building_conflicts___building_polygons_not_invisible_not_intersecting___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_resolve_building_conflicts,
        description="building_polygons_not_invisible_not_intersecting",
    )

    polygon_resolve_building_conflicts___building_polygons_intersecting_road___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_resolve_building_conflicts,
        description="building_polygons_intersecting_road",
    )

    polygon_resolve_building_conflicts___intersecting_polygons_to_points___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_resolve_building_conflicts,
        description="intersecting_polygons_to_points",
    )

    polygon_resolve_building_conflicts___final_merged_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_resolve_building_conflicts,
            description="final_merged_points",
        )
    )

    polygon_resolve_building_conflicts___small_building_polygons___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_resolve_building_conflicts,
            description="small_building_polygons",
        )
    )

    polygon_resolve_building_conflicts___small_building_polygons_to_point___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_resolve_building_conflicts,
        description="small_building_polygons_to_point",
    )

    polygon_resolve_building_conflicts___railway___n100_building_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=polygon_resolve_building_conflicts,
            description="railway",
        )
    )

    # ========================================
    #                        HOSPITAL CHURCH CLUSTERS
    # ========================================

    hospital_church_clusters___hospital_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=hospital_church_clusters,
            description="hospital_points",
        )
    )

    hospital_church_clusters___church_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=hospital_church_clusters,
            description="church_points",
        )
    )

    hospital_church_clusters___all_hospital_clusters___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=hospital_church_clusters,
            description="all_hospital_clusters",
        )
    )

    hospital_church_clusters___all_church_clusters___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=hospital_church_clusters,
            description="all_church_clusters",
        )
    )

    hospital_church_clusters___hospital_points_not_in_cluster___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=hospital_church_clusters,
            description="hospital_points_not_in_cluster",
        )
    )

    hospital_church_clusters___hospital_points_in_cluster___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=hospital_church_clusters,
            description="hospital_points_in_cluster",
        )
    )

    hospital_church_clusters___church_points_not_in_cluster___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=hospital_church_clusters,
            description="church_points_not_in_cluster",
        )
    )

    hospital_church_clusters___church_points_in_cluster___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=hospital_church_clusters,
            description="church_points_in_cluster",
        )
    )

    hospital_church_clusters___minimum_bounding_geometry_hospital___n100_hospital = (
        file_manager.generate_file_name_gdb(
            script_source_name=hospital_church_clusters,
            description="minimum_bounding_geometry_hospital",
        )
    )
    hospital_church_clusters___feature_to_point_hospital___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=hospital_church_clusters,
            description="feature_to_point_hospital",
        )
    )

    hospital_church_clusters___minimum_bounding_geometry_church___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=hospital_church_clusters,
            description="minimum_bounding_geometry_church",
        )
    )

    hospital_church_clusters___feature_to_point_church___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=hospital_church_clusters,
            description="feature_to_point_church",
        )
    )

    hospital_church_clusters___chosen_hospitals_from_cluster___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=hospital_church_clusters,
            description="chosen_hospitals_from_cluster",
        )
    )
    hospital_church_clusters___chosen_churches_from_cluster___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=hospital_church_clusters,
            description="chosen_churches_from_cluster",
        )
    )

    hospital_church_clusters___reduced_hospital_and_church_points_merged___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=hospital_church_clusters,
        description="reduced_hospital_and_church_points_final",
    )

    hospital_church_clusters___selecting_hospital_points_after_cluster_reduction___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=hospital_church_clusters,
        description="selecting_hospital_points_after_cluster_reduction",
    )

    hospital_church_clusters___selecting_church_points_after_cluster_reduction___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=hospital_church_clusters,
        description="selecting_church_points_after_cluster_reduction",
    )

    hospital_church_clusters___church_points_NOT_too_close_to_hospitals___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=hospital_church_clusters,
        description="church_points_NOT_too_close_to_hospitals",
    )

    hospital_church_clusters___final___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=hospital_church_clusters,
            description="final",
        )
    )

    hospital_church_clusters___all_other_points_that_are_not_hospital_church___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=hospital_church_clusters,
        description="all_other_points_that_are_not_hospital_church",
    )

    # ========================================
    #                  POINT PROPAGATE DISPLACEMENT
    # ========================================

    point_propagate_displacement___points_after_propagate_displacement___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=point_propagate_displacement,
        description="points_after_propagate_displacement",
    )

    # ========================================
    #                REMOVING POINTS IN WATER FEATURES
    # ========================================

    removing_points_and_erasing_polygons_in_water_features___water_features___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_points_and_erasing_polygons_in_water_features,
        description="water_features",
    )

    removing_points_and_erasing_polygons_in_water_features___tourist_cabins___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_points_and_erasing_polygons_in_water_features,
        description="tourist_cabins",
    )

    removing_points_and_erasing_polygons_in_water_features___not_tourist_cabins___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_points_and_erasing_polygons_in_water_features,
        description="not_tourist_cabins",
    )

    removing_points_and_erasing_polygons_in_water_features___merged_points_and_tourist_cabins___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_points_and_erasing_polygons_in_water_features,
        description="merged_points_and_tourist_cabins",
    )

    removing_points_and_erasing_polygons_in_water_features___points_that_do_not_intersect_water_features___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_points_and_erasing_polygons_in_water_features,
        description="points_that_do_not_intersect_water_features",
    )

    removing_points_and_erasing_polygons_in_water_features___final_points___n100_lyrx = file_manager.generate_file_name_lyrx(
        script_source_name=removing_points_and_erasing_polygons_in_water_features,
        description="final_points",
    )

    removing_points_and_erasing_polygons_in_water_features___building_polygons_too_close_to_water_features___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_points_and_erasing_polygons_in_water_features,
        description="building_polygons_too_close_to_water_features",
    )

    removing_points_and_erasing_polygons_in_water_features___building_polygons_NOT_too_close_to_water_features___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_points_and_erasing_polygons_in_water_features,
        description="building_polygons_NOT_too_close_to_water_features",
    )

    removing_points_and_erasing_polygons_in_water_features___erased_polygons___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_points_and_erasing_polygons_in_water_features,
        description="erased_polygons",
    )

    removing_points_and_erasing_polygons_in_water_features___simplified_polygons___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_points_and_erasing_polygons_in_water_features,
        description="simplified_polygons",
    )

    removing_points_and_erasing_polygons_in_water_features___water_features_buffered___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_points_and_erasing_polygons_in_water_features,
        description="water_features_buffered",
    )

    removing_points_and_erasing_polygons_in_water_features___water_features_close_to_building_polygons___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_points_and_erasing_polygons_in_water_features,
        description="water_feature_buffer_close_to_building_polygons",
    )
    removing_points_and_erasing_polygons_in_water_features___final_points_merged___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_points_and_erasing_polygons_in_water_features,
        description="final_points_merged",
    )

    removing_points_and_erasing_polygons_in_water_features___final_building_polygons_merged___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_points_and_erasing_polygons_in_water_features,
        description="final_building_polygons_merged",
    )

    # ========================================
    #                REMOVING OVERLAPPING POINTS
    # ========================================

    removing_overlapping_polygons_and_points___graphic_conflicts_polygon___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_overlapping_polygons_and_points,
        description="graphic_conflicts_polygon",
    )

    removing_overlapping_polygons_and_points___points_close_to_graphic_conflict_polygons___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_overlapping_polygons_and_points,
        description="points_close_to_graphic_conflict_polygons",
    )

    removing_overlapping_polygons_and_points___point_clusters___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_polygons_and_points,
            description="point_clusters",
        )
    )

    removing_overlapping_polygons_and_points___all_building_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_polygons_and_points,
            description="all_building_points",
        )
    )

    removing_overlapping_polygons_and_points___all_building_points___n100_building_lyrx = file_manager.generate_file_name_lyrx(
        script_source_name=removing_overlapping_polygons_and_points,
        description="all_building_points",
    )

    removing_overlapping_polygons_and_points___all_building_points_to_squares___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_overlapping_polygons_and_points,
        description="all_building_points_to_squares",
    )

    removing_overlapping_polygons_and_points___squares_close_to_graphic_conflict_polygons___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_overlapping_polygons_and_points,
        description="squares_close_to_graphic_conflict_polygons",
    )

    removing_overlapping_polygons_and_points___squares_not_close_to_graphic_conflict_polygons___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_overlapping_polygons_and_points,
        description="squares_not_close_to_graphic_conflict_polygons",
    )

    removing_overlapping_polygons_and_points___points_in_a_cluster___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_polygons_and_points,
            description="points_in_a_cluster",
        )
    )

    removing_overlapping_polygons_and_points___points_not_in_a_cluster___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_overlapping_polygons_and_points,
        description="points_not_in_a_cluster",
    )

    removing_overlapping_polygons_and_points___merging_final_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_polygons_and_points,
            description="merging_final_points",
        )
    )

    removing_overlapping_polygons_and_points___points_in_a_cluster_original___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_overlapping_polygons_and_points,
        description="points_in_a_cluster_original",
    )

    removing_overlapping_polygons_and_points___points_NOT_close_to_graphic_conflict_polygons___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_overlapping_polygons_and_points,
        description="points_NOT_close_to_graphic_conflict_polygons",
    )

    removing_overlapping_polygons_and_points___points_to_squares___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_polygons_and_points,
            description="points_to_squares",
        )
    )

    removing_overlapping_polygons_and_points___final___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_polygons_and_points,
            description="final",
        )
    )

    removing_overlapping_polygons_and_points___all_points_not_hospital_and_church__n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_overlapping_polygons_and_points,
        description="all_points_not_hospital_and_church",
    )

    removing_overlapping_polygons_and_points___squares_back_to_points___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_overlapping_polygons_and_points,
        description="squares_back_to_points",
    )

    removing_overlapping_polygons_and_points___hospital_and_church_points__n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_overlapping_polygons_and_points,
        description="hospital_and_church_points",
    )

    removing_overlapping_polygons_and_points___points_to_squares_church_hospitals___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_overlapping_polygons_and_points,
        description="points_to_squares_church_hospitals",
    )

    removing_overlapping_polygons_and_points___building_polygons_not_intersecting_church_hospitals____n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_overlapping_polygons_and_points,
        description="building_polygons_not_intersecting_church_hospitals_",
    )

    removing_overlapping_polygons_and_points___road_symbology_no_buffer_addition___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_overlapping_polygons_and_points,
        description="road_symbology_no_buffer_addition",
    )

    removing_overlapping_polygons_and_points___root_file_line_symbology___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_overlapping_polygons_and_points,
        description="root_file_line_symbology",
    )

    removing_overlapping_polygons_and_points___polygons_intersecting_road_buffers___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_overlapping_polygons_and_points,
        description="polygons_intersecting_road_buffers",
    )

    removing_overlapping_polygons_and_points___polygons_NOT_intersecting_road_buffers___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_overlapping_polygons_and_points,
        description="polygons_NOT_intersecting_road_buffers",
    )

    removing_overlapping_polygons_and_points___polygons_to_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_polygons_and_points,
            description="polygons_to_points",
        )
    )

    ############################################## NEEDS TO BE UPDATED ###########################################################

    # ========================================
    #                  POINT DISPLACEMENT WITH BUFFER
    # ========================================

    point_displacement_with_buffer___church_hospital_selection___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="church_hospital_selection",
        )
    )

    point_displacement_with_buffer___building_points_selection___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="building_points_selection",
        )
    )

    point_displacement_with_buffer___root_file___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="root_file",
        )
    )

    point_displacement_with_buffer___displaced_building_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="displaced_building_points",
        )
    )

    point_displacement_with_buffer___documentation___building_n100 = (
        file_manager.generate_file_name_general_files(
            script_source_name=point_displacement_with_buffer,
            description="documentation",
            file_type="json",
        )
    )

    point_displacement_with_buffer___merged_buffer_displaced_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="merged_buffer_displaced_points",
        )
    )

    point_displacement_with_buffer__iteration_points_to_square_polygons__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="iteration_points_to_square_polygons",
        )
    )

    point_displacement_with_buffer__displaced_building_points__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="displaced_building_points",
        )
    )

    point_displacement_with_buffer___squares_not_overlapping_roads___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="squares_not_overlapping_roads",
        )
    )

    ############################################## NOT USED RIGHT NOW ###########################################################

    ##################################
    ############ ITERATION ############
    ##################################

    iteration__partition_iterator__n100 = file_manager.generate_file_name_gdb(
        script_source_name=iteration,
        description="partition_iterator",
    )

    iteration__partition_iterator_final_output_points__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=iteration,
            description="partition_iterator_final_output_points",
        )
    )

    iteration___json_documentation___building_n100 = (
        file_manager.generate_file_name_general_files(
            script_source_name=iteration,
            description="json_documentation",
            file_type="json",
        )
    )

    # ========================================
    #                  POINT RESOLVE BUILDING CONFLICTS
    # ========================================

    point_resolve_building_conflicts___building_points_squares___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="building_points_squares",
        )
    )

    point_resolve_building_conflicts___geometry_validation___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="geometry_validation",
        )
    )

    point_resolve_building_conflicts___lyrx_root___n100_building = (
        file_manager.generate_file_lyrx_directory(
            script_source_name=point_resolve_building_conflicts,
            description="lyrx_root",
        )
    )

    point_resolve_building_conflicts___base_path_for_features___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="base_path_for_features",
        )
    )

    point_resolve_building_conflicts___root_file___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="root_file",
        )
    )

    point_resolve_building_conflicts___documentation___building_n100 = (
        file_manager.generate_file_name_general_files(
            script_source_name=point_resolve_building_conflicts,
            description="documentation",
            file_type="json",
        )
    )

    point_resolve_building_conflicts___transform_points_to_square_polygons___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=point_resolve_building_conflicts,
        description="transform_points_to_square_polygons",
    )

    point_resolve_building_conflicts___selection_area_resolve_building_conflicts___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=point_resolve_building_conflicts,
        description="selection_area_resolve_building_conflicts",
    )

    point_resolve_building_conflicts___building_polygon_selection_rbc___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=point_resolve_building_conflicts,
        description="building_polygon_selection_rbc",
    )

    point_resolve_building_conflicts___building_polygons_to_points_and_then_squares___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=point_resolve_building_conflicts,
        description="building_polygons_to_points_and_then_squares",
    )

    point_resolve_building_conflicts___building_point_selection_rbc___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="building_point_selection_rbc",
        )
    )

    point_resolve_building_conflicts___begrensningskurve_selection_rbc___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=point_resolve_building_conflicts,
        description="begrensningskurve_selection_rbc",
    )

    point_resolve_building_conflicts___squares_selection_rbc___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="drawn_polygon_selection_rbc",
        )
    )

    point_resolve_building_conflicts___bygningspunkt_selection___n100_building_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=point_resolve_building_conflicts,
            description="bygningspunkt_selection",
        )
    )

    point_resolve_building_conflicts___grunnriss_selection___n100_building_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=point_resolve_building_conflicts,
            description="grunnriss_selection",
        )
    )

    point_resolve_building_conflicts___building_polygons_to_points_and_then_squares___n100_building_lyrx = file_manager.generate_file_name_lyrx(
        script_source_name=point_resolve_building_conflicts,
        description="building_polygons_to_points_and_then_squares",
    )

    point_resolve_building_conflicts___veg_sti_selection___n100_building_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=point_resolve_building_conflicts,
            description="veg_sti_selection",
        )
    )

    point_resolve_building_conflicts___begrensningskurve_selection___n100_building_lyrx = file_manager.generate_file_name_lyrx(
        script_source_name=point_resolve_building_conflicts,
        description="begrensningskurve_selection",
    )

    point_resolve_building_conflicts___squares_selection___n100_building_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=point_resolve_building_conflicts,
            description="drawn_polygon_selection",
        )
    )

    point_resolve_building_conflicts___squares_to_keep_after_rbc1___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="drawn_polygons_result_1",
        )
    )

    point_resolve_building_conflicts___building_polygons_to_keep_after_rbc1___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=point_resolve_building_conflicts,
        description="building_polygons_visible_result_1",
    )

    point_resolve_building_conflicts___building_polygons_invisible_result_1___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=point_resolve_building_conflicts,
        description="building_polygons_invisible_result_1",
    )

    point_resolve_building_conflicts___building_polygons_to_points_result_1___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=point_resolve_building_conflicts,
        description="building_polygons_to_points_result_1",
    )

    point_resolve_building_conflicts___squares_to_keep_after_rbc1___n100_building_lyrx = file_manager.generate_file_name_lyrx(
        script_source_name=point_resolve_building_conflicts,
        description="squares_to_keep_after_rbc1",
    )

    point_resolve_building_conflicts___building_polygons_to_keep_after_rbc1___n100_building_lyrx = file_manager.generate_file_name_lyrx(
        script_source_name=point_resolve_building_conflicts,
        description="squares_to_keep_after_rbc1",
    )

    point_resolve_building_conflicts___building_polygons_rbc2___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="building_polygons_rbc2",
        )
    )

    point_resolve_building_conflicts___squares_from_points_rbc2___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="squares_from_points_rbc2",
        )
    )

    point_resolve_building_conflicts___squares_from_polygons_rbc2___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="squares_from_polygons_rbc2",
        )
    )

    point_resolve_building_conflicts___squares_from_points_transformed_back_to_points___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=point_resolve_building_conflicts,
        description="squares_from_points_transformed_back_to_points",
    )

    point_resolve_building_conflicts___squares_from_polygons_transformed_to_points___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=point_resolve_building_conflicts,
        description="squares_from_polygons_transformed_to_points",
    )

    point_resolve_building_conflicts___building_polygons_final___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="building_polygons_final",
        )
    )

    point_resolve_building_conflicts___final_points_merged___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="final_points_merged",
        )
    )

    point_resolve_building_conflicts___building_points_final___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="building_points_final",
        )
    )

    point_resolve_building_conflicts___road_selection_rbc___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="road_selection_rbc",
        )
    )

    ########################### testing ########################

    point_resolve_building_conflicts___POINT_OUTPUT___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="POINT_OUTPUT",
        )
    )

    point_resolve_building_conflicts___POLYGON_OUTPUT___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="POLYGON_OUTPUT",
        )
    )

    # ========================================
    #                              RBC TOOL
    # ========================================

    # ========================================
    #                              FINALIZING BUILDINGS
    # ========================================

    finalizing_buildings___tourist_cabins___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=finalizing_buildings,
            description="building_points_final",
        )
    )

    finalizing_buildings___points_not_close_to_urban_areas___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=finalizing_buildings,
            description="points_not_close_to_urban_areas",
        )
    )

    finalizing_buildings___all_points_except_tourist_cabins___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=finalizing_buildings,
            description="all_points_except_tourist_cabins",
        )
    )

    finalizing_buildings___urban_areas___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=finalizing_buildings,
            description="urban_areas",
        )
    )

    finalizing_buildings___selecting_hospital_and_churches_in_urban_areas___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=finalizing_buildings,
        description="selecting_hospital_and_churches_in_urban_areas",
    )

    finalizing_buildings___all_points_not_in_urban_areas___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=finalizing_buildings,
            description="all_points_not_in_urban_areas",
        )
    )

    finalizing_buildings___polygon_to_line___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=finalizing_buildings,
            description="polygon_to_line",
        )
    )

    finalizing_buildings___hospitals_and_churches_pictogram___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=finalizing_buildings,
            description="hospitals_and_churches_pictogram",
        )
    )

    finalizing_buildings___points_too_close_to_urban_areas___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=finalizing_buildings,
            description="points_too_close_to_urban_areas",
        )
    )

    data_cleanup___geometry_validation___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_cleanup,
            description="geometry_validation",
        )
    )

    TuristHytte = file_manager.generate_final_outputs(
        file_name="TuristHytte",
    )

    BygningsPunkt = file_manager.generate_final_outputs(
        file_name="BygningsPunkt",
    )

    Grunnriss = file_manager.generate_final_outputs(
        file_name="Grunnriss",
    )

    OmrissLinje = file_manager.generate_final_outputs(
        file_name="OmrissLinje",
    )

    Piktogram = file_manager.generate_final_outputs(
        file_name="Piktogram",
    )
