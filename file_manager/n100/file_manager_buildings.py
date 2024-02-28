# Imports
from enum import Enum
import config
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager


# Initialize BaseFileManager
scale = global_config.scale_n100
object_name = global_config.object_bygning
file_manager = BaseFileManager(scale=scale, object_name=object_name)


##############################################################################################################################################

# All file and function names in correct order

# building_data_preparation.py
preparation_begrensningskurve = "preparation_begrensningskurve"
preperation_veg_sti = "preperation_veg_sti"
adding_matrikkel_as_points = "adding_matrikkel_as_points"
selecting_grunnriss_for_generalization = "selecting_grunnriss_for_generalization"
table_management = "table_management"
grunnriss_to_point = "grunnriss_to_point"


# create_simplified_building_polygons.py
aggregate_polygons = "aggregate_building_polygons"
simplify_buildings_1 = "simplify_buildings_1"
simplify_buildings_2 = "simplify_buildings_2"
simplify_polygons = "simplify_polygons"
join_and_add_fields = "join_and_add_fields"

# create_cartographic_partitions.py
create_cartographic_partitions = "create_cartographic_partitions"

# building_polygon_displacement_rbc.py
propagate_displacement_building_polygons = "propagate_displacement_building_polygons"
features_500_m_from_building_polygons = "features_500_m_from_building_polygons"
apply_symbology_to_layers = "apply_symbology_to_layers"
resolve_building_conflict_building_polygon = (
    "resolve_building_conflict_building_polygon"
)
creating_road_buffer = "creating_road_buffer"
invisible_building_polygons_to_point = "invisible_building_polygons_to_point"
intersecting_building_polygons_to_point = "intersecting_building_polygons_to_point"
merging_invisible_intersecting_points = "merging_invisible_intersecting_points"


# iteration.py
iteration = "iteration"

# building_points_propagate_displacement.py
propagate_displacement = "propagate_displacement"

# building_point_buffer_displacement.py
building_point_buffer_displacement = "building_point_buffer_displacement"

# create_points_from_polygon.py
points_to_polygon = "points_to_polygon"

# reducing_hospital_church_clusters.py
hospital_church_selections = "hospital_church_selections"
find_clusters = "find_clusters"
reducing_clusters = "reducing_clusters"

# resolve_building_conflicts.py
rbc_selection = "rbc_selection"
apply_symbology = "apply_symbology"
resolve_building_conflicts = "resolve_building_conflicts"


displacement_feature_asker = "displacement_feature_asker"

##############################################################################################################################################


class Building_N100(Enum):

    """
    An enumeration for river-related geospatial data file paths within the N100 scale and bygning object context.

    Utilizes the BaseFileManager to generate standardized file paths for geodatabase files, general files, and layer files,
    tailored to river data preparation and analysis tasks.

    Example Syntaxes:
        - For Geodatabase (.gdb) Files:
            the_file_name_of_the_script___the_description_of_the_file___n100_bygning = file_manager.generate_file_name_gdb(
                script_source_name="the_file_name_of_the_script",
                description="the_description_of_the_file",
            )

        - For General Files (e.g., .txt, .csv):
            the_file_name_of_the_script___the_description_of_the_file___n100_bygning_filetype_extension = file_manager.generate_file_name_general_files(
                script_source_name="the_file_name_of_the_script",
                description="the_description_of_the_file",
                file_type="filetype_extension",
            )

        - For ArcGIS Layer Files (.lyrx):
            the_file_name_of_the_script___the_description_of_the_file___n100_bygning_lyrx = file_manager.generate_file_name_lyrx(
                script_source_name="the_file_name_of_the_script",
                description="the_description_of_the_file",
            )

    These examples show how to utilize the BaseFileManager's methods to generate file paths for different types of files,
    reflecting the specific needs and naming conventions of river data management within the project.
    """

    #################################################
    ########### BUILDING DATA PREPARATION ###########
    #################################################

    preparation_begrensningskurve__selected_waterfeatures_from_begrensningskurve__n100 = file_manager.generate_file_name_gdb(
        script_source_name=preparation_begrensningskurve,
        description="selected_waterfeatures_from_begrensningskurve",
    )

    preparation_begrensningskurve__selected_land_features_area__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=preparation_begrensningskurve,
            description="selected_land_features_area",
        )
    )

    preparation_begrensningskurve__land_features_near_water__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=preparation_begrensningskurve,
            description="land_features_near_water",
        )
    )

    preparation_begrensningskurve__begrensningskurve_waterfeatures_buffer__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=preparation_begrensningskurve,
            description="begrensningskurve_waterfeatures_buffer",
        )
    )

    preparation_begrensningskurve__land_features_buffer__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=preparation_begrensningskurve,
            description="land_features_buffer",
        )
    )

    preparation_begrensningskurve__begrensningskurve_buffer_erase_1__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=preparation_begrensningskurve,
            description="begrensningskurve_buffer_erase_1",
        )
    )

    preparation_begrensningskurve__begrensningskurve_buffer_erase_2__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=preparation_begrensningskurve,
            description="begrensningskurve_buffer_erase_2",
        )
    )

    preperation_veg_sti__unsplit_veg_sti__n100 = file_manager.generate_file_name_gdb(
        script_source_name=preperation_veg_sti,
        description="unsplit_veg_sti",
    )

    # Function: adding_matrikkel_as_points

    adding_matrikkel_as_points__urban_area_selection_n100__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=adding_matrikkel_as_points,
            description="urban_area_selection_n100",
        )
    )

    adding_matrikkel_as_points__urban_area_selection_n50__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=adding_matrikkel_as_points,
            description="urban_area_selection_n50",
        )
    )

    adding_matrikkel_as_points__urban_area_selection_n100_buffer__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=adding_matrikkel_as_points,
            description="urban_area_selection_n100_buffer",
        )
    )

    adding_matrikkel_as_points__no_longer_urban_areas__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=adding_matrikkel_as_points,
            description="no_longer_urban_areas",
        )
    )

    adding_matrikkel_as_points__matrikkel_bygningspunkt__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=adding_matrikkel_as_points,
            description="matrikkel_bygningspunkt",
        )
    )

    # Function: selecting_grunnriss_for_generalization

    selecting_grunnriss_for_generalization__selected_grunnriss_not_church__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=selecting_grunnriss_for_generalization,
            description="selected_grunnriss_not_church",
        )
    )

    selecting_grunnriss_for_generalization__large_enough_grunnriss__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=selecting_grunnriss_for_generalization,
            description="large_enough_grunnriss",
        )
    )

    selecting_grunnriss_for_generalization__too_small_grunnriss__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=selecting_grunnriss_for_generalization,
            description="too_small_grunnriss",
        )
    )

    selecting_grunnriss_for_generalization__points_created_from_small_grunnriss__n100 = file_manager.generate_file_name_gdb(
        script_source_name=selecting_grunnriss_for_generalization,
        description="points_created_from_small_grunnriss",
    )

    selecting_grunnriss_for_generalization__grunnriss_kirke__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=selecting_grunnriss_for_generalization,
            description="grunnriss_kirke",
        )
    )

    selecting_grunnriss_for_generalization__kirke_points_created_from_grunnriss__n100 = file_manager.generate_file_name_gdb(
        script_source_name=selecting_grunnriss_for_generalization,
        description="kirke_points_created_from_grunnriss",
    )

    ##########################################
    ########### CALCULATING VALUES ###########
    ##########################################

    # Function: table_management

    table_management__merged_bygningspunkt_n50_matrikkel__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=table_management,
            description="merged_bygningspunkt_n50_matrikkel",
        )
    )

    table_management__bygningspunkt_pre_resolve_building_conflicts__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=table_management,
            description="bygningspunkt_pre_resolve_building_conflicts",
        )
    )

    table_management__selection_bygningspunkt_with_undefined_nbr_values__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=table_management,
            description="selection_bygningspunkt_with_undefined_nbr_values",
        )
    )

    table_management__building_points_with_undefined_nbr_values__n100 = (
        file_manager.generate_file_name_general_files(
            script_source_name=table_management,
            description="building_points_with_undefined_nbr_values",
            file_type="txt",
        )
    )

    ##################################################
    ########### CREATE POINTS FROM POLYGON ###########
    ##################################################

    # Function: grunnriss_to_point

    grunnriss_to_point__intersect_aggregated_and_original__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=grunnriss_to_point,
            description="intersect_aggregated_and_original",
        )
    )

    grunnriss_to_point__grunnriss_feature_to_point__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=grunnriss_to_point,
            description="grunnriss_feature_to_point",
        )
    )

    grunnriss_to_point__spatial_join_points__n100 = file_manager.generate_file_name_gdb(
        script_source_name=grunnriss_to_point,
        description="spatial_join_points",
    )

    grunnriss_to_point__merged_points_created_from_grunnriss__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=grunnriss_to_point,
            description="merged_points_created_from_grunnriss",
        )
    )

    ###########################################################
    ########### CREATE SIMPLIFIED BUILDING POLYGONS ###########
    ###########################################################

    # Function: aggregate_polygons

    aggregate_polygons__fill_hole__n100 = file_manager.generate_file_name_gdb(
        script_source_name=aggregate_polygons,
        description="fill_hole",
    )

    # Function: simplify_buildings_1

    simplify_buildings_1_simplifying__n100 = file_manager.generate_file_name_gdb(
        script_source_name=simplify_buildings_1,
        description="simplifying",
    )

    simplify_buildings_1__points__n100 = file_manager.generate_file_name_gdb(
        script_source_name=grunnriss_to_point,
        description="points",
    )

    # Function: simplify_buildings_2

    simplify_buildings_2_simplifying__n100 = file_manager.generate_file_name_gdb(
        script_source_name=simplify_buildings_2,
        description="simplifying",
    )

    simplify_buildings_2__points__n100 = file_manager.generate_file_name_gdb(
        script_source_name=grunnriss_to_point,
        description="points",
    )

    # Function: simplify_polygons
    simplify_polygons__simplifying__n100 = file_manager.generate_file_name_gdb(
        script_source_name=simplify_polygons,
        description="simplifying",
    )

    simplify_polygons__points__n100 = file_manager.generate_file_name_gdb(
        script_source_name=grunnriss_to_point,
        description="points",
    )

    # Function: join_and_add_fields

    join_and_add_fields__spatial_join_polygons__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=join_and_add_fields,
            description="spatial_join_polygons",
        )
    )

    join_and_add_fields__building_polygons_final__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=join_and_add_fields,
            description="building_polygons_final",
        )
    )

    ####################################################
    ########### BUILDING POLYGON DISPLACEMENT ##########
    ####################################################

    # Function: propagate_displacement_building_polygons

    propagate_displacement_building_polygons__building_polygon_pre_propogate_displacement__n100 = file_manager.generate_file_name_gdb(
        script_source_name=propagate_displacement_building_polygons,
        description="building_polygons_pre_propogate_displacement",
    )

    propagate_displacement_building_polygons__after_propogate_displacement__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=propagate_displacement_building_polygons,
            description="building_polygons_after_propogate_displacement",
        )
    )

    propagate_displacement_building_polygons__displacement_feature_1000_m_from_building_polygon__n100 = file_manager.generate_file_name_gdb(
        script_source_name=propagate_displacement_building_polygons,
        description="displacement_feature_1000_m_from_building_polygon",
    )

    # features_500_m_from_building_polygons

    features_500_m_from_building_polygons__selected_begrensningskurve__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=features_500_m_from_building_polygons,
            description="selected_begrensningskurve",
        )
    )
    features_500_m_from_building_polygons__selected_roads__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=features_500_m_from_building_polygons,
            description="selected_roads",
        )
    )

    # Function: apply_symbology_to_layers

    apply_symbology_to_layers__building_polygon__n100__lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=apply_symbology_to_layers,
            description="building_polygon",
        )
    )

    apply_symbology_to_layers__roads__n100__lyrx = file_manager.generate_file_name_lyrx(
        script_source_name=apply_symbology_to_layers,
        description="roads",
    )

    apply_symbology_to_layers__begrensningskurve__n100__lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=apply_symbology_to_layers,
            description="begrensningskurve",
        )
    )
    # Function: resolve_building_conflict_building_polygon

    resolve_building_conflict_building_polygon__after_RBC__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=resolve_building_conflict_building_polygon,
            description="after_RBC",
        )
    )

    resolve_building_conflict_building_selected_hospital_church_points__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=resolve_building_conflict_building_polygon,
            description="selected_hospital_church_points",
        )
    )

    resolve_building_conflict_building_polygon__hospital_church_polygons__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=resolve_building_conflict_building_polygon,
            description="hospital_church_polygons",
        )
    )

    resolve_building_conflict_building_polygon__polygonprocessor_symbology__n100__lyrx = file_manager.generate_file_name_lyrx(
        script_source_name=resolve_building_conflict_building_polygon,
        description="polygonprocessor_symbology",
    )

    # Function: invisible_building_polygons_to_point

    invisible_building_polygons_to_point__invisible_polygons__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=invisible_building_polygons_to_point,
            description="invisible_polygons",
        )
    )

    invisible_building_polygons_to_point__not_invisible_polygons__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=invisible_building_polygons_to_point,
            description="not_invisible_polygons",
        )
    )

    invisible_building_polygons_to_point__invisible_polygons_to_points__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=invisible_building_polygons_to_point,
            description="invisible_polygons_to_points",
        )
    )

    # Function: creating_road_buffer

    creating_road_buffer__selection__n100 = file_manager.generate_file_name_gdb(
        script_source_name=creating_road_buffer,
        description="selection",
    )

    creating_road_buffer__buffers__n100 = file_manager.generate_file_name_gdb(
        script_source_name=creating_road_buffer,
        description="buffers",
    )

    creating_road_buffer__merged_buffers__n100 = file_manager.generate_file_name_gdb(
        script_source_name=creating_road_buffer,
        description="merged_buffers",
    )

    # Function: intersecting_building_polygons_to_point

    intersecting_building_polygons_to_point__final_building_polygons__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=intersecting_building_polygons_to_point,
            description="final_building_polgyons",
        )
    )

    intersecting_building_polygons_to_point__building_polygons_intersecting__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=intersecting_building_polygons_to_point,
            description="building_polygons_intersecting",
        )
    )

    intersecting_building_polygons_to_point__building_points__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=intersecting_building_polygons_to_point,
            description="building_points",
        )
    )

    # Function: merging_invisible_intersecting_points

    merging_invisible_intersecting_points__final__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=merging_invisible_intersecting_points,
            description="final",
        )
    )

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

    ###################################################
    ########### HOSPITAL AND CHURCH CLUSTERS ###########
    ###################################################

    # Functon: hospital_church_selections

    hospital_church_selections__hospital_points__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=hospital_church_selections,
            description="hospital_points",
        )
    )

    hospital_church_selections__church_points__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=hospital_church_selections,
            description="church_points",
        )
    )

    # Function: find_clusters

    find_clusters__all_hospital_clusters__n100 = file_manager.generate_file_name_gdb(
        script_source_name=find_clusters,
        description="all_hospital_clusters",
    )

    find_clusters__all_church_clusters__n100 = file_manager.generate_file_name_gdb(
        script_source_name=find_clusters,
        description="all_church_clusters",
    )

    find_clusters__hospital_points_not_in_cluster__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=find_clusters,
            description="hospital_points_not_in_cluster",
        )
    )

    find_clusters__hospital_points_in_cluster__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=find_clusters,
            description="hospital_points_in_cluster",
        )
    )

    find_clusters__church_points_not_in_cluster__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=find_clusters,
            description="church_points_not_in_cluster",
        )
    )

    find_clusters__church_points_in_cluster__n100 = file_manager.generate_file_name_gdb(
        script_source_name=find_clusters,
        description="church_points_in_cluster",
    )

    # Function: reducing_clusters
    reducing_clusters__minimum_bounding_geometry_hospital__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=reducing_clusters,
            description="minimum_bounding_geometry_hospital",
        )
    )
    reducing_clusters__feature_to_point_hospital__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=reducing_clusters,
            description="feature_to_point_hospital",
        )
    )

    reducing_clusters__minimum_bounding_geometry_church__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=reducing_clusters,
            description="minimum_bounding_geometry_church",
        )
    )

    reducing_clusters__feature_to_point_church__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=reducing_clusters,
            description="feature_to_point_church",
        )
    )

    reducing_clusters__chosen_hospitals_from_cluster__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=reducing_clusters,
            description="chosen_hospitals_from_cluster",
        )
    )
    reducing_clusters__chosen_churches_from_cluster__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=reducing_clusters,
            description="chosen_churches_from_cluster",
        )
    )

    reducing_clusters__reduced_hospital_and_church_points_2__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=reducing_clusters,
            description="reduced_hospital_and_church_points_2",
        )
    )

    ########################################
    ######## PROPAGATE DISPLACEMENT  ########
    ########################################

    propagate_displacement__bygningspunkt_pre_propogate_displacement__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=propagate_displacement,
            description="bygningspunkt_pre_propogate_displacement",
        )
    )

    ########################################
    ########### ROADS TO POLYGON ###########
    ########################################

    building_point_buffer_displacement__roads_study_area__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=building_point_buffer_displacement,
            description="roads_study_area",
        )
    )

    building_point_buffer_displacement__begrensningskurve_study_area__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=building_point_buffer_displacement,
            description="begrensningskurve_study_area",
        )
    )

    building_point_buffer_displacement__buildings_study_area__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=building_point_buffer_displacement,
            description="buildings_study_area",
        )
    )

    building_point_buffer_displacement__selection_roads__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=building_point_buffer_displacement,
            description="selection_roads",
        )
    )

    building_point_buffer_displacement__align_buffer_schema_to_template__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=building_point_buffer_displacement,
            description="align_buffer_schema_to_template",
        )
    )

    building_point_buffer_displacement__roads_buffer__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=building_point_buffer_displacement,
            description="roads_buffer",
        )
    )

    building_point_buffer_displacement__roads_buffer_appended__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=building_point_buffer_displacement,
            description="roads_buffer_appended",
        )
    )

    building_point_buffer_displacement__iteration_points_to_square_polygons__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=building_point_buffer_displacement,
            description="iteration_points_to_square_polygons",
        )
    )

    building_point_buffer_displacement__building_polygon_erased__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=building_point_buffer_displacement,
            description="building_polygon_erased",
        )
    )

    building_point_buffer_displacement__displaced_building_points__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=building_point_buffer_displacement,
            description="displaced_building_points",
        )
    )

    #########################################
    ########### POINTS TO POLYGON ###########
    #########################################

    points_to_polygon__transform_points_to_square_polygons__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=points_to_polygon,
            description="transform_points_to_square_polygons",
        )
    )

    ###################################################
    ########### RESOLVE BUILDING CONFLICTS  ###########
    ###################################################

    # Function: rbc_selection

    rbc_selection__selection_area_resolve_building_conflicts__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=rbc_selection,
            description="selection_area_resolve_building_conflicts",
        )
    )

    rbc_selection__grunnriss_selection_rbc__n100 = file_manager.generate_file_name_gdb(
        script_source_name=rbc_selection,
        description="grunnriss_selection_rbc",
    )

    rbc_selection__veg_sti_selection_rbc_rbc__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=rbc_selection,
            description="veg_sti_selection_rbc",
        )
    )

    rbc_selection__bygningspunkt_selection_rbc__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=rbc_selection,
            description="bygningspunkt_selection_rbc",
        )
    )

    rbc_selection__begrensningskurve_selection_rbc__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=rbc_selection,
            description="begrensningskurve_selection_rbc",
        )
    )

    rbc_selection__drawn_polygon_selection_rbc__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=rbc_selection,
            description="drawn_polygon_selection_rbc",
        )
    )

    # Function: apply_symbology

    apply_symbology__bygningspunkt_selection__n100_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=apply_symbology,
            description="bygningspunkt_selection",
        )
    )

    apply_symbology__grunnriss_selection__n100_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=apply_symbology,
            description="grunnriss_selection",
        )
    )

    apply_symbology__veg_sti_selection__n100_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=apply_symbology,
            description="veg_sti_selection",
        )
    )

    apply_symbology__begrensningskurve_selection__n100_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=apply_symbology,
            description="begrensningskurve_selection",
        )
    )

    apply_symbology__drawn_polygon_selection__n100_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=apply_symbology,
            description="drawn_polygon_selection",
        )
    )

    # Function: resolve_building_conflicts

    resolve_building_conflicts__drawn_polygons_result_1__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=resolve_building_conflicts,
            description="drawn_polygons_result_1",
        )
    )

    resolve_building_conflicts__drawn_polygon_RBC_result_1__n100_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=resolve_building_conflicts,
            description="drawn_polygon_RBC_result_1",
        )
    )

    resolve_building_conflicts__building_points_RBC_result_1__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=resolve_building_conflicts,
            description="building_points_RBC_result_1",
        )
    )

    resolve_building_conflicts__building_points_RBC_result_2__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=resolve_building_conflicts,
            description="building_points_RBC_result_2",
        )
    )

    resolve_building_conflicts__building_points_RBC_result_1__n100_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=resolve_building_conflicts,
            description="building_points_RBC_result_1",
        )
    )

    resolve_building_conflicts__building_points_RBC_result_2__n100_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=resolve_building_conflicts,
            description="building_points_RBC_result_2",
        )
    )

    resolve_building_conflicts__drawn_polygons_result_2__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=resolve_building_conflicts,
            description="drawn_polygons_result_2",
        )
    )

    resolve_building_conflicts__drawn_polygon_RBC_result_2__n100_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=resolve_building_conflicts,
            description="drawn_polygon_RBC_result_2",
        )
    )
