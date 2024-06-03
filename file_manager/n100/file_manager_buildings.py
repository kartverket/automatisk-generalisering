# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager


# Initialize BaseFileManager
scale = global_config.scale_n100
object_name = global_config.object_bygning
file_manager = BaseFileManager(scale=scale, object_name=object_name)


# All scripts
data_preparation = "data_preparation"
simplify_polygons = "simplify_polygons"
polygon_propogate_displacement = "polygon_propogate_displacement"
polygon_resolve_building_conflicts = "polygon_resolve_building_conflicts"
polygon_to_point = "polygon_to_point"
line_to_buffer_symbology = "line_to_buffer_symbology"
calculating_polygon_values = "calculating_polygon_values"
calculate_point_values = "calculate_point_values"
point_propogate_displacement = "point_propogate_displacement"
removing_points_and_erasing_polygons_in_water_features = (
    "removing_points_and_erasing_polygons_in_water_features"
)
removing_overlapping_points = "removing_overlapping_points"
hospital_church_clusters = "hospital_church_clusters"
point_displacement_with_buffer = "point_displacement_with_buffer"
points_to_squares = "points_to_squares"
point_resolve_building_conflicts = "point_resolve_building_conflicts"
finalizing_buildings = "finalizing_buildings"
data_clean_up = "data_clean_up"


# Additional names
overview = "overview"

# TO BE DELETED
create_cartographic_partitions = "create_cartographic_partitions"
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

    data_preperation___waterfeatures_from_begrensningskurve_not_rivers___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=data_preparation,
        description="waterfeatures_from_begrensningskurve_not_rivers",
    )

    data_preperation___waterfeatures_from_begrensningskurve_rivers___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="waterfeatures_from_begrensningskurve_rivers",
        )
    )

    data_preperation___waterfeatures_from_begrensningskurve_rivers_buffer___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=data_preparation,
        description="waterfeatures_from_begrensningskurve_rivers_buffer",
    )

    data_preparation___merged_begrensningskurve_all_waterbodies___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="merged_begrensningskurve_all_waterbodies",
        )
    )

    data_preparation___selected_land_features_area___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="selected_land_features_area",
        )
    )

    data_preparation___land_features_near_water___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="land_features_near_water",
        )
    )

    data_preparation___begrensningskurve_waterfeatures_buffer___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="begrensningskurve_waterfeatures_buffer",
        )
    )

    data_preparation___land_features_buffer___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="land_features_buffer",
        )
    )

    data_preparation___begrensningskurve_buffer_erase_1___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="begrensningskurve_buffer_erase_1",
        )
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
    begrensingskurve_land_water___begrensingskurve_buffer_in_water___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=begrensingskurve_land_water,
            description="begrensingskurve_buffer_in_water",
        )
    )

    # ========================================
    #                      CALCULATE POINT VALUES
    # ========================================

    calculate_point_values___points_going_into_rbc___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=calculate_point_values,
            description="points_going_into_rbc",
        )
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

    polygon_to_point___spatial_join_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_to_point,
            description="spatial_join_points",
        )
    )

    polygon_to_point___merged_points_final___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_to_point,
            description="merged_points_final",
        )
    )

    # ========================================
    #                              LINE TO BUFFER SYMBOLOGY
    # ========================================
    line_to_buffer_symbology___buffer_symbology___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=line_to_buffer_symbology,
            description="buffer_symbology",
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

    simplify_polygons___simplify_building_1_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=simplify_polygons,
            description="simplify_building_1_points",
        )
    )

    simplify_polygons___simplify_building_2___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=simplify_polygons,
            description="simplify_building_2",
        )
    )

    simplify_polygons___simplify_building_2_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=simplify_polygons,
            description="_simplify_building_2_points",
        )
    )

    simplify_polygons___simplify_polygon___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=simplify_polygons,
            description="simplify_polygon",
        )
    )

    simplify_polygons___points___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=simplify_polygons,
        description="points",
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

    polygon_propogate_displacement___displacement_feature_500m_from_polygon___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_propogate_displacement,
        description="displacement_feature_500m_from_polygon",
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

    polygon_resolve_building_conflicts___merged_road_buffers___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_resolve_building_conflicts,
            description="merged_road_buffers",
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

    polygon_resolve_building_conflicts___railway_500m_from_displaced_polygon___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_resolve_building_conflicts,
        description="railway_500m_from_displaced_polygon",
    )

    polygon_resolve_building_conflicts___railway_buffer___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_resolve_building_conflicts,
            description="railway_buffer",
        )
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

    hospital_church_clusters___hospital_church_points_final___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=hospital_church_clusters,
            description="hospital_church_points_final",
        )
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
    #                  POINT PROPOATE DISPLACEMENT
    # ========================================

    point_propogate_displacement___points_pre_propogate_displacement___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_propogate_displacement,
            description="points_pre_propogate_displacement",
        )
    )

    point_propogate_displacement___displacement_feature_500m_from_point___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=point_propogate_displacement,
        description="displacement_feature_500m_from_point",
    )

    point_propogate_displacement___points_after_propogate_displacement___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=point_propogate_displacement,
        description="points_after_propogate_displacement",
    )

    point_propogate_displacement___area_oslo_asker___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_propogate_displacement,
            description="area_oslo_asker",
        )
    )

    point_propogate_displacement___points_in_area_oslo_asker___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_propogate_displacement,
            description="points_in_area_oslo_asker",
        )
    )

    # ========================================
    #                REMOVING POINTS IN WATER FEATURES
    # ========================================

    removing_points_and_erasing_polygons_in_water_features___water_features___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_points_and_erasing_polygons_in_water_features,
        description="water_features",
    )

    removing_points_and_erasing_polygons_in_water_features___final_points___n100_building = file_manager.generate_file_name_gdb(
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

    removing_overlapping_points___graphic_conflicts_polygon___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_points,
            description="graphic_conflicts_polygon",
        )
    )

    removing_overlapping_points___points_close_to_graphic_conflict_polygons___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_overlapping_points,
        description="points_close_to_graphic_conflict_polygons",
    )

    removing_overlapping_points___point_clusters___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_points,
            description="point_clusters",
        )
    )

    removing_overlapping_points___all_building_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_points,
            description="all_building_points",
        )
    )

    removing_overlapping_points___building_points_overlaps_removed___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_points,
            description="building_points_overlaps_removed",
        )
    )

    removing_overlapping_points___points_in_a_cluster___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_points,
            description="points_in_a_cluster",
        )
    )

    removing_overlapping_points___points_not_in_a_cluster___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_points,
            description="points_not_in_a_cluster",
        )
    )

    removing_overlapping_points___merging_final_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_points,
            description="merging_final_points",
        )
    )

    removing_overlapping_points___points_in_a_cluster_original___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_points,
            description="points_in_a_cluster_original",
        )
    )

    removing_overlapping_points___points_NOT_close_to_graphic_conflict_polygons___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_overlapping_points,
        description="points_NOT_close_to_graphic_conflict_polygons",
    )

    removing_overlapping_points___points_to_squares___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_points,
            description="points_to_squares",
        )
    )

    removing_overlapping_points___final___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_points,
            description="final",
        )
    )

    removing_overlapping_points___all_points_not_hospital_and_church__n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_points,
            description="all_points_not_hospital_and_church",
        )
    )

    removing_overlapping_points___squares_back_to_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_points,
            description="squares_back_to_points",
        )
    )

    removing_overlapping_points___hospital_and_church_points__n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_overlapping_points,
            description="hospital_and_church_points",
        )
    )

    ############################################## NEEDS TO BE UPDATED ###########################################################

    # ========================================
    #                  POINT DISPLACEMENT WITH BUFFER
    # ========================================

    building_point_buffer_displacement__roads_study_area__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="roads_study_area",
        )
    )

    building_point_buffer_displacement__begrensningskurve_study_area__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="begrensningskurve_study_area",
        )
    )

    building_point_buffer_displacement__buildings_study_area__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="buildings_study_area",
        )
    )

    building_point_buffer_displacement__selection_roads__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="selection_roads",
        )
    )

    building_point_buffer_displacement__selection_urban_areas__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="selection_urban_areas",
        )
    )

    building_point_buffer_displacement__align_buffer_schema_to_template__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="align_buffer_schema_to_template",
        )
    )

    building_point_buffer_displacement__roads_buffer__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="roads_buffer",
        )
    )

    building_point_buffer_displacement__roads_buffer_appended__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="roads_buffer_appended",
        )
    )

    building_point_buffer_displacement__iteration_points_to_square_polygons__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="iteration_points_to_square_polygons",
        )
    )

    building_point_buffer_displacement__building_polygon_erased__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="building_polygon_erased",
        )
    )

    building_point_buffer_displacement__displaced_building_points__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="displaced_building_points",
        )
    )

    removing_overlapping_points___squares_not_overlapping_roads___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_displacement_with_buffer,
            description="squares_not_overlapping_roads",
        )
    )

    ############################################## NOT USED RIGHT NOW ###########################################################

    ##############################################
    ######## CREATE CARTOGRAPHIC PARTITIONS ########
    ##############################################

    create_cartographic_partitions__cartographic_partitions__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=create_cartographic_partitions,
            description="cartographic_partitions",
        )
    )

    create_cartographic_partitions__cartographic_partitions_buffer__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=create_cartographic_partitions,
            description="cartographic_partitions_buffer",
        )
    )

    create_cartographic_partitions__buffer_erased__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=create_cartographic_partitions,
            description="buffer_erased",
        )
    )

    ##################################
    ############ ITERATION ############
    ##################################

    iteration__partition_iterator__n100 = file_manager.generate_file_name_gdb(
        script_source_name=iteration,
        description="partition_iterator",
    )

    iteration__partition_iterator_final_output__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=iteration,
            description="partition_iterator_final_output",
        )
    )

    iteration__partition_iterator_final_output_points__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=iteration,
            description="partition_iterator_final_output_points",
        )
    )

    iteration__partition_iterator_final_output_polygons__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=iteration,
            description="partition_iterator_final_output_polygons",
        )
    )

    iteration__iteration_partition__n100 = file_manager.generate_file_name_gdb(
        script_source_name=iteration,
        description="iteration_partition",
    )

    iteration__iteration_buffer__n100 = file_manager.generate_file_name_gdb(
        script_source_name=iteration,
        description="iteration_buffer",
    )

    iteration__iteration_erased_buffer__n100 = file_manager.generate_file_name_gdb(
        script_source_name=iteration,
        description="iteration_erased_buffer",
    )

    iteration__append_feature_building_point__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=iteration,
            description="append_feature_building_point",
        )
    )

    iteration__append_feature_building_polygon__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=iteration,
            description="append_feature_building_polygon",
        )
    )

    iteration__building_points_iteration_selection_append__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=iteration,
            description="building_points_iteration_selection_append",
        )
    )

    iteration__building_polygon_iteration_selection_append__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=iteration,
            description="building_polygon_iteration_selection_append",
        )
    )

    iteration__building_points_present_partition__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=iteration,
            description="building_points_present_partition",
        )
    )

    iteration__building_polygon_present_partition__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=iteration,
            description="building_polygon_present_partition",
        )
    )

    iteration__building_points_base_partition_selection__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=iteration,
            description="building_points_base_partition_selection",
        )
    )

    iteration__building_polygon_base_partition_selection__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=iteration,
            description="building_polygon_base_partition_selection",
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

    point_resolve_building_conflicts___road_buffers_selection_rbc___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="road_buffers_selection_rbc",
        )
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

    point_resolve_building_conflicts___drawn_polygon_RBC_result_1___n100_building_lyrx = file_manager.generate_file_name_lyrx(
        script_source_name=point_resolve_building_conflicts,
        description="drawn_polygon_RBC_result_1",
    )

    point_resolve_building_conflicts___rbc_1_squares_to_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="building_points_RBC_result_1",
        )
    )

    point_resolve_building_conflicts___building_points_RBC_result_1___n100_building_lyrx = file_manager.generate_file_name_lyrx(
        script_source_name=point_resolve_building_conflicts,
        description="building_points_RBC_result_1",
    )

    point_resolve_building_conflicts___building_points_RBC_final___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="building_points_RBC_final",
        )
    )

    point_resolve_building_conflicts___building_points_RBC_final___n100_building_lyrx = file_manager.generate_file_name_lyrx(
        script_source_name=point_resolve_building_conflicts,
        description="building_points_RBC_final",
    )

    point_resolve_building_conflicts___drawn_polygons_result_2___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=point_resolve_building_conflicts,
            description="drawn_polygons_result_2",
        )
    )

    point_resolve_building_conflicts___drawn_polygon_result_2___n100_building_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=point_resolve_building_conflicts,
            description="drawn_polygon_result_2",
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
