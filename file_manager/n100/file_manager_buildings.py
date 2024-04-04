# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager


# Initialize BaseFileManager
scale = global_config.scale_n100
object_name = global_config.object_bygning
file_manager = BaseFileManager(scale=scale, object_name=object_name)


##############################################################################################################################################


# All scripts
data_preparation = "data_preparation"
simplify_polygons = "simplify_polygons"
polygon_propogate_displacement = "polygon_propogate_displacement"
polygon_to_point = "polygon_to_point"
calculating_field_values = "calculating_field_values"
point_propogate_displacement = "point_propogate_displacement"
removing_points_in_water_features = "removing_points_in_water_features"
hospital_church_clusters = "hospital_church_clusters"
point_displacement_with_buffer = "point_displacement_with_buffer"
points_to_squares = "points_to_squares"
resolve_building_conflicts_points = "resolve_building_conflicts_points"
data_clean_up = "data_clean_up"

# Additional names
overview = "overview"

# TO BE DELETED
create_cartographic_partitions = "create_cartographic_partitions"
iteration = "iteration"


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

    data_preperation___matrikkel_n50_points_merged___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="matrikkel_n50_points_merged",
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

    # ========================================
    #                      CALCULATING FIELD VALUES
    # ========================================

    calculate_field_values___points_pre_resolve_building_conflicts___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=calculating_field_values,
            description="points_pre_resolve_building_conflicts",
        )
    )

    calculating_field_values___selection_building_points_with_undefined_nbr_values___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=calculating_field_values,
        description="selection_building_points_with_undefined_nbr_values",
    )

    calculating_field_values___building_points_with_undefined_nbr_values___n100_building = file_manager.generate_file_name_general_files(
        script_source_name=calculating_field_values,
        description="building_points_with_undefined_nbr_values",
        file_type="txt",
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

    simplify_polygons___final___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=simplify_polygons,
        description="final",
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

    polygon_propogate_displacement___after_displacement___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_propogate_displacement,
            description="after_displacement",
        )
    )

    polygon_propogate_displacement___displacement_feature_500m_from_polygon___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_propogate_displacement,
        description="displacement_feature_500m_from_polygon",
    )

    polygon_propogate_displacement___begrensningskurve_500m_from_displaced_polygon___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_propogate_displacement,
        description="begrensningskurve_500m_from_displaced_polygon",
    )
    polygon_propogate_displacement___roads_500m_from_displaced_polygon___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_propogate_displacement,
        description="roads_500m_from_displaced_polygon",
    )

    polygon_propogate_displacement___building_polygon___n100_building_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=polygon_propogate_displacement,
            description="building_polygon",
        )
    )

    polygon_propogate_displacement___roads___n100_building_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=polygon_propogate_displacement,
            description="roads",
        )
    )

    polygon_propogate_displacement___begrensningskurve___n100_building_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=polygon_propogate_displacement,
            description="begrensningskurve",
        )
    )

    polygon_propogate_displacement___after_rbc___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_propogate_displacement,
            description="after_rbc",
        )
    )

    polygon_propogate_displacement___hospital_church_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_propogate_displacement,
            description="hospital_church_points",
        )
    )

    polygon_propogate_displacement___hospital_church_squares___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_propogate_displacement,
            description="hospital_church_squares",
        )
    )

    polygon_propogate_displacement___polygonprocessor_symbology___n100_building_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=polygon_propogate_displacement,
            description="polygonprocessor_symbology",
        )
    )

    polygon_propogate_displacement___invisible_polygons_after_rbc___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_propogate_displacement,
            description="invisible_polygons_after_rbc",
        )
    )

    polygon_propogate_displacement___not_invisible_polygons_after_rbc___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_propogate_displacement,
        description="not_invisible_polygons_after_rbc",
    )

    polygon_propogate_displacement___invisible_polygons_to_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_propogate_displacement,
            description="invisible_polygons_to_points",
        )
    )

    polygon_propogate_displacement___road_buffer_selection___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_propogate_displacement,
            description="road_buffer_selection",
        )
    )

    polygon_propogate_displacement___road_buffers___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_propogate_displacement,
            description="road_buffers",
        )
    )

    polygon_propogate_displacement___merged_road_buffers___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_propogate_displacement,
            description="merged_road_buffers",
        )
    )

    polygon_propogate_displacement___building_polygons_final___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_propogate_displacement,
            description="building_polygons_final",
        )
    )

    polygon_propogate_displacement___building_polygons_not_invisible_not_intersecting___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_propogate_displacement,
        description="building_polygons_not_invisible_not_intersecting",
    )

    polygon_propogate_displacement___building_polygons_intersecting_road___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_propogate_displacement,
        description="building_polygons_intersecting_road",
    )

    polygon_propogate_displacement___intersecting_polygons_to_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_propogate_displacement,
            description="intersecting_polygons_to_points",
        )
    )

    polygon_propogate_displacement___final_merged_points___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_propogate_displacement,
            description="final_merged_points",
        )
    )

    polygon_propogate_displacement___small_building_polygons___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=polygon_propogate_displacement,
            description="small_building_polygons",
        )
    )

    polygon_propogate_displacement___small_building_polygons_to_point___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=polygon_propogate_displacement,
        description="small_building_polygons_to_point",
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

    hospital_church_clusters___reduced_hospital_and_church_points_final___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=hospital_church_clusters,
        description="reduced_hospital_and_church_points_final",
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

    # ========================================
    #                REMOVING POINTS IN WATER FEATURES
    # ========================================

    removing_points_in_water_features___water_features___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=removing_points_in_water_features,
            description="water_features",
        )
    )

    removing_points_in_water_features___points_that_do_not_intersect_water_features___n100_building = file_manager.generate_file_name_gdb(
        script_source_name=removing_points_in_water_features,
        description="points_that_do_not_intersect_water_features",
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

    #########################################
    ########### POINTS TO POLYGON ###########
    #########################################

    points_to_squares___transform_points_to_square_polygons___n100_building = (
        file_manager.generate_file_name_gdb(
            script_source_name=points_to_squares,
            description="transform_points_to_square_polygons",
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

    iteration___partition_iterator_json_documentation___building_n100 = (
        file_manager.generate_file_name_general_files(
            script_source_name=iteration,
            description="partition_iterator_json_documentation",
            file_type="json",
        )
    )

    ###################################################
    ########### RESOLVE BUILDING CONFLICTS  ###########
    ###################################################

    # Function: rbc_selection

    rbc_selection__selection_area_resolve_building_conflicts__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=resolve_building_conflicts_points,
            description="selection_area_resolve_building_conflicts",
        )
    )

    rbc_selection__grunnriss_selection_rbc__n100 = file_manager.generate_file_name_gdb(
        script_source_name=resolve_building_conflicts_points,
        description="grunnriss_selection_rbc",
    )

    rbc_selection__veg_sti_selection_rbc_rbc__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=resolve_building_conflicts_points,
            description="veg_sti_selection_rbc",
        )
    )

    rbc_selection__bygningspunkt_selection_rbc__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=resolve_building_conflicts_points,
            description="bygningspunkt_selection_rbc",
        )
    )

    rbc_selection__begrensningskurve_selection_rbc__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=resolve_building_conflicts_points,
            description="begrensningskurve_selection_rbc",
        )
    )

    rbc_selection__drawn_polygon_selection_rbc__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=resolve_building_conflicts_points,
            description="drawn_polygon_selection_rbc",
        )
    )

    # Function: apply_symbology

    apply_symbology__bygningspunkt_selection__n100_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=resolve_building_conflicts_points,
            description="bygningspunkt_selection",
        )
    )

    apply_symbology__grunnriss_selection__n100_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=resolve_building_conflicts_points,
            description="grunnriss_selection",
        )
    )

    apply_symbology__veg_sti_selection__n100_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=resolve_building_conflicts_points,
            description="veg_sti_selection",
        )
    )

    apply_symbology__begrensningskurve_selection__n100_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=resolve_building_conflicts_points,
            description="begrensningskurve_selection",
        )
    )

    apply_symbology__drawn_polygon_selection__n100_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=resolve_building_conflicts_points,
            description="drawn_polygon_selection",
        )
    )

    # Function: resolve_building_conflicts

    resolve_building_conflicts__drawn_polygons_result_1__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=resolve_building_conflicts_points,
            description="drawn_polygons_result_1",
        )
    )

    resolve_building_conflicts__drawn_polygon_RBC_result_1__n100_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=resolve_building_conflicts_points,
            description="drawn_polygon_RBC_result_1",
        )
    )

    resolve_building_conflicts__building_points_RBC_result_1__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=resolve_building_conflicts_points,
            description="building_points_RBC_result_1",
        )
    )

    resolve_building_conflicts__building_points_RBC_final__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=resolve_building_conflicts_points,
            description="building_points_RBC_result_2",
        )
    )

    resolve_building_conflicts__building_points_RBC_result_1__n100_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=resolve_building_conflicts_points,
            description="building_points_RBC_result_1",
        )
    )

    resolve_building_conflicts__building_points_RBC_final__n100_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=resolve_building_conflicts_points,
            description="building_points_RBC_result_2",
        )
    )

    resolve_building_conflicts__drawn_polygons_result_2__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=resolve_building_conflicts_points,
            description="drawn_polygons_result_2",
        )
    )

    resolve_building_conflicts__drawn_polygon_RBC_result_2__n100_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=resolve_building_conflicts_points,
            description="drawn_polygon_RBC_result_2",
        )
    )
