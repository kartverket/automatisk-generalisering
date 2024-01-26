# Imports
from enum import Enum
import config
from env_setup import setup_directory_structure


# Scale name
scale = setup_directory_structure.scale_n100

# Object name
object = setup_directory_structure.object_bygning

# Relative paths
relative_path_gdb = (
    rf"{config.output_folder}\automatic_generalization_outputs\{scale}\{object}.gdb"
)

relative_path_general_files = rf"{config.output_folder}\automatic_generalization_outputs\{scale}\{setup_directory_structure.general_files_name}"

relative_path_lyrx = rf"{config.output_folder}\automatic_generalization_outputs\{scale}\{setup_directory_structure.lyrx_directory_name}"


##############################################################################################################################################


# Creating file names based on set standard
def generate_file_name_gdb(
    function_name,
    description,
    scale,
):
    """
    Summary:
        Generates the full file path for files which can be stored in gdb's, where the files are generated to the bygning.gdb in the n100 subdirectory.

    Details:
        - The path is generated using the relative path to the bygning.gdb in the n100 subdirectory.
        - The file name is generated using the function name, description, and scale.
    """
    return rf"{relative_path_gdb}\{function_name}__{description}__{scale}"


def generate_file_name_general_files(
    function_name,
    description,
    scale,
    file_type,
):
    """
    Summary:
        Generates the full file path for files which can not be stored in gdb's, but are stored in the general_files subdirectory for n100.

    Details:
        - The path is generated using the relative path to the genral_files subdirectory.
        - The file name is generated using the function name, description, and scale.
    """
    return rf"{relative_path_general_files}\{function_name}__{description}__{scale}.{file_type}"


def generate_file_name_lyrx(
    function_name,
    description,
    scale,
):
    """
    Summary:
        Generates the full file path for lyrx files which can not be stored in gdb's. The lyrx files are generated to the lyrx_outputs subdirectory for n100.

    Details:
        - The path is generated using the relative path to the lyrx_outputs subdirectory.
        - The file name is generated using the function name, description, and scale.
    """
    return rf"{relative_path_lyrx}\{function_name}__{description}__{scale}.lyrx"


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

# building_polygon_displacement.py
propagate_displacement_building_polygons = "propagate_displacement_building_polygons"
features_500_m_from_building_polygons = "features_500_m_from_building_polygons"
apply_symbology_to_layers = "apply_symbology_to_layers"
creating_road_buffer = "creating_road_buffer"
erasing_building_polygons_with_road_buffer = (
    "erasing_building_polygons_with_road_buffer"
)
small_building_polygons_to_point = "small_building_polygons_to_point"

# iteration.py
iteration = "iteration"

# propagate_displacement.py
propagate_displacement = "propagate_displacement"

# building_point_buffer_displacement.py
building_point_buffer_displacement = "building_point_buffer_displacement"

# create_points_from_polygon.py
points_to_polygon = "points_to_polygon"

# hospital_church_clusters.py
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
    Summary:
        The class `Building_N100`is the file manager used for the Building generalization. It is used to build and hold the full output paths for files in our project.
        The way the paths are generated they work in any directive setup for different systems, and can handle files
        which can be stored in gdb's and files which can not be stored in gdb's. It uses the direcory structure created by `setup_directory_structure.py`.

    Details:
        - generate_file_name_gdb: Genereates the full file path for files which can be stored in gdb's, where the files are generated to the bygning.gdb in the n100 subdirectory.
        - generate_file_name_general_files: Genereates the full file path for files which can not be stored in gdb's, but are stored in the general_files subdirectory for n100.
        - generate_file_name_lyrx: Genereates the full file path for lyrx files which can not be stored in gdb's. The lyrx files are generated to the lyrx_outputs subdirectory for n100.
    """

    displacement_feature_asker__displacement_feature_asker__n100 = (
        generate_file_name_gdb(
            function_name=displacement_feature_asker,
            description="displacement_feature_asker",
            scale=scale,
        )
    )

    #################################################
    ########### BUILDING DATA PREPARATION ###########
    #################################################

    preparation_begrensningskurve__selected_waterfeatures_from_begrensningskurve__n100 = generate_file_name_gdb(
        function_name=preparation_begrensningskurve,
        description="selected_waterfeatures_from_begrensningskurve",
        scale=scale,
    )

    preparation_begrensningskurve__selected_land_features_area__n100 = (
        generate_file_name_gdb(
            function_name=preparation_begrensningskurve,
            description="selected_land_features_area",
            scale=scale,
        )
    )

    preparation_begrensningskurve__land_features_near_water__n100 = (
        generate_file_name_gdb(
            function_name=preparation_begrensningskurve,
            description="land_features_near_water",
            scale=scale,
        )
    )

    preparation_begrensningskurve__begrensningskurve_waterfeatures_buffer__n100 = (
        generate_file_name_gdb(
            function_name=preparation_begrensningskurve,
            description="begrensningskurve_waterfeatures_buffer",
            scale=scale,
        )
    )

    preparation_begrensningskurve__land_features_buffer__n100 = generate_file_name_gdb(
        function_name=preparation_begrensningskurve,
        description="land_features_buffer",
        scale=scale,
    )

    preparation_begrensningskurve__begrensningskurve_buffer_erase_1__n100 = (
        generate_file_name_gdb(
            function_name=preparation_begrensningskurve,
            description="begrensningskurve_buffer_erase_1",
            scale=scale,
        )
    )

    preparation_begrensningskurve__begrensningskurve_buffer_erase_2__n100 = (
        generate_file_name_gdb(
            function_name=preparation_begrensningskurve,
            description="begrensningskurve_buffer_erase_2",
            scale=scale,
        )
    )

    preperation_veg_sti__unsplit_veg_sti__n100 = generate_file_name_gdb(
        function_name=preperation_veg_sti,
        description="unsplit_veg_sti",
        scale=scale,
    )

    # Function: adding_matrikkel_as_points

    adding_matrikkel_as_points__urban_area_selection_n100__n100 = (
        generate_file_name_gdb(
            function_name=adding_matrikkel_as_points,
            description="urban_area_selection_n100",
            scale=scale,
        )
    )

    adding_matrikkel_as_points__urban_area_selection_n50__n100 = generate_file_name_gdb(
        function_name=adding_matrikkel_as_points,
        description="urban_area_selection_n50",
        scale=scale,
    )

    adding_matrikkel_as_points__urban_area_selection_n100_buffer__n100 = (
        generate_file_name_gdb(
            function_name=adding_matrikkel_as_points,
            description="urban_area_selection_n100_buffer",
            scale=scale,
        )
    )

    adding_matrikkel_as_points__no_longer_urban_areas__n100 = generate_file_name_gdb(
        function_name=adding_matrikkel_as_points,
        description="no_longer_urban_areas",
        scale=scale,
    )

    adding_matrikkel_as_points__matrikkel_bygningspunkt__n100 = generate_file_name_gdb(
        function_name=adding_matrikkel_as_points,
        description="matrikkel_bygningspunkt",
        scale=scale,
    )

    # Function: selecting_grunnriss_for_generalization

    selecting_grunnriss_for_generalization__selected_grunnriss_not_church__n100 = (
        generate_file_name_gdb(
            function_name=selecting_grunnriss_for_generalization,
            description="selected_grunnriss_not_church",
            scale=scale,
        )
    )

    selecting_grunnriss_for_generalization__large_enough_grunnriss__n100 = (
        generate_file_name_gdb(
            function_name=selecting_grunnriss_for_generalization,
            description="large_enough_grunnriss",
            scale=scale,
        )
    )

    selecting_grunnriss_for_generalization__too_small_grunnriss__n100 = (
        generate_file_name_gdb(
            function_name=selecting_grunnriss_for_generalization,
            description="too_small_grunnriss",
            scale=scale,
        )
    )

    selecting_grunnriss_for_generalization__points_created_from_small_grunnriss__n100 = generate_file_name_gdb(
        function_name=selecting_grunnriss_for_generalization,
        description="points_created_from_small_grunnriss",
        scale=scale,
    )

    selecting_grunnriss_for_generalization__grunnriss_kirke__n100 = (
        generate_file_name_gdb(
            function_name=selecting_grunnriss_for_generalization,
            description="grunnriss_kirke",
            scale=scale,
        )
    )

    selecting_grunnriss_for_generalization__kirke_points_created_from_grunnriss__n100 = generate_file_name_gdb(
        function_name=selecting_grunnriss_for_generalization,
        description="kirke_points_created_from_grunnriss",
        scale=scale,
    )

    ##########################################
    ########### CALCULATING VALUES ###########
    ##########################################

    # Function: table_management

    table_management__merged_bygningspunkt_n50_matrikkel__n100 = generate_file_name_gdb(
        function_name=table_management,
        description="merged_bygningspunkt_n50_matrikkel",
        scale=scale,
    )

    table_management__bygningspunkt_pre_resolve_building_conflicts__n100 = (
        generate_file_name_gdb(
            function_name=table_management,
            description="bygningspunkt_pre_resolve_building_conflicts",
            scale=scale,
        )
    )

    table_management__selection_bygningspunkt_with_undefined_nbr_values__n100 = (
        generate_file_name_gdb(
            function_name=table_management,
            description="selection_bygningspunkt_with_undefined_nbr_values",
            scale=scale,
        )
    )

    table_management__building_points_with_undefined_nbr_values__n100 = (
        generate_file_name_general_files(
            function_name=table_management,
            description="building_points_with_undefined_nbr_values",
            scale=scale,
            file_type="txt",
        )
    )

    ##################################################
    ########### CREATE POINTS FROM POLYGON ###########
    ##################################################

    # Function: grunnriss_to_point

    grunnriss_to_point__intersect_aggregated_and_original__n100 = (
        generate_file_name_gdb(
            function_name=grunnriss_to_point,
            description="intersect_aggregated_and_original",
            scale=scale,
        )
    )

    grunnriss_to_point__grunnriss_feature_to_point__n100 = generate_file_name_gdb(
        function_name=grunnriss_to_point,
        description="grunnriss_feature_to_point",
        scale=scale,
    )

    grunnriss_to_point__spatial_join_points__n100 = generate_file_name_gdb(
        function_name=grunnriss_to_point,
        description="spatial_join_points",
        scale=scale,
    )

    grunnriss_to_point__merged_points_created_from_grunnriss__n100 = (
        generate_file_name_gdb(
            function_name=grunnriss_to_point,
            description="merged_points_created_from_grunnriss",
            scale=scale,
        )
    )

    ###########################################################
    ########### CREATE SIMPLIFIED BUILDING POLYGONS ###########
    ###########################################################

    # Function: aggregate_polygons

    aggregate_polygons__fill_hole__n100 = generate_file_name_gdb(
        function_name=aggregate_polygons,
        description="fill_hole",
        scale=scale,
    )

    # Function: simplify_buildings_1

    simplify_buildings_1_simplifying__n100 = generate_file_name_gdb(
        function_name=simplify_buildings_1,
        description="simplifying",
        scale=scale,
    )

    simplify_buildings_1__points__n100 = generate_file_name_gdb(
        function_name=grunnriss_to_point,
        description="points",
        scale=scale,
    )

    # Function: simplify_buildings_2

    simplify_buildings_2_simplifying__n100 = generate_file_name_gdb(
        function_name=simplify_buildings_2,
        description="simplifying",
        scale=scale,
    )

    simplify_buildings_2__points__n100 = generate_file_name_gdb(
        function_name=grunnriss_to_point,
        description="points",
        scale=scale,
    )

    # Function: simplify_polygons
    simplify_polygons__simplifying__n100 = generate_file_name_gdb(
        function_name=simplify_polygons,
        description="simplifying",
        scale=scale,
    )

    simplify_polygons__points__n100 = generate_file_name_gdb(
        function_name=grunnriss_to_point,
        description="points",
        scale=scale,
    )

    # Function: join_and_add_fields

    join_and_add_fields__spatial_join_polygons__n100 = generate_file_name_gdb(
        function_name=join_and_add_fields,
        description="spatial_join_polygons",
        scale=scale,
    )

    join_and_add_fields__building_polygons_final__n100 = generate_file_name_gdb(
        function_name=join_and_add_fields,
        description="building_polygons_final",
        scale=scale,
    )

    ####################################################
    ########### BUILDING POLYGON DISPLACEMENT ##########
    ####################################################

    # Function: propagate_displacement_building_polygons

    propagate_displacement_building_polygons__building_polygon_pre_propogate_displacement__n100 = generate_file_name_gdb(
        function_name=propagate_displacement_building_polygons,
        description="building_polygons_pre_propogate_displacement",
        scale=scale,
    )

    propagate_displacement_building_polygons__after_propogate_displacement__n100 = (
        generate_file_name_gdb(
            function_name=propagate_displacement_building_polygons,
            description="building_polygons_after_propogate_displacement",
            scale=scale,
        )
    )

    propagate_displacement_building_polygons__displacement_feature_1000_m_from_building_polygon__n100 = generate_file_name_gdb(
        function_name=propagate_displacement_building_polygons,
        description="displacement_feature_1000_m_from_building_polygon",
        scale=scale,
    )

    # features_500_m_from_building_polygons

    features_500_m_from_building_polygons__selected_begrensningskurve__n100 = (
        generate_file_name_gdb(
            function_name=features_500_m_from_building_polygons,
            description="selected_begrensningskurve__n100",
            scale=scale,
        )
    )
    features_500_m_from_building_polygons__selected_roads__n100 = (
        generate_file_name_gdb(
            function_name=features_500_m_from_building_polygons,
            description="selected_roads__n100",
            scale=scale,
        )
    )

    # Function: apply_symbology_to_layers

    apply_symbology_to_layers__building_polygon__n100__lyrx = generate_file_name_lyrx(
        function_name=apply_symbology_to_layers,
        description="building_polygon",
        scale=scale,
    )

    apply_symbology_to_layers__roads__n100__lyrx = generate_file_name_lyrx(
        function_name=apply_symbology_to_layers,
        description="roads",
        scale=scale,
    )

    apply_symbology_to_layers__begrensningskurve__n100__lyrx = generate_file_name_lyrx(
        function_name=apply_symbology_to_layers,
        description="begrensningskurve",
        scale=scale,
    )
    # Function: resolve_building_conflict_building_polygon

    # Function: creating_road_buffer

    creating_road_buffer__merged_road_buffers__n100 = generate_file_name_gdb(
        function_name=creating_road_buffer,
        description="merged_road_buffers",
        scale=scale,
    )

    creating_road_buffer__selection__n100 = generate_file_name_gdb(
        function_name=creating_road_buffer,
        description="selection",
        scale=scale,
    )

    creating_road_buffer__buffers__n100 = generate_file_name_gdb(
        function_name=creating_road_buffer,
        description="buffers",
        scale=scale,
    )

    # Function: erasing_building_polygons_with_road_buffer

    erasing_building_polygons_with_road_buffer__erased_buildings__n100 = (
        generate_file_name_gdb(
            function_name=erasing_building_polygons_with_road_buffer,
            description="erased_buildings",
            scale=scale,
        )
    )

    erasing_building_polygons_with_road_buffer__after_multipart_to_singlepart__n100 = (
        generate_file_name_gdb(
            function_name=erasing_building_polygons_with_road_buffer,
            description="after_multipart_to_singlepart",
            scale=scale,
        )
    )

    erasing_building_polygons_with_road_buffer__selected_building_parts__n100 = (
        generate_file_name_gdb(
            function_name=erasing_building_polygons_with_road_buffer,
            description="selected_building_parts",
            scale=scale,
        )
    )

    erasing_building_polygons_with_road_buffer__building_polygons_erased_and_reduced__n100 = generate_file_name_gdb(
        function_name=erasing_building_polygons_with_road_buffer,
        description="building_polygons_erased_and_reduced",
        scale=scale,
    )

    erasing_building_polygons_with_road_buffer__reduced_building_polygons__n100 = (
        generate_file_name_gdb(
            function_name=erasing_building_polygons_with_road_buffer,
            description="reduced_building_polygons",
            scale=scale,
        )
    )

    erasing_building_polygons_with_road_buffer__building_polygons_too_small_n100 = (
        generate_file_name_gdb(
            function_name=erasing_building_polygons_with_road_buffer,
            description="building_polygons_too_small",
            scale=scale,
        )
    )

    erasing_building_polygons_with_road_buffer__building_polygons_erased_final__n100 = (
        generate_file_name_gdb(
            function_name=erasing_building_polygons_with_road_buffer,
            description="building_polygons_erased_final",
            scale=scale,
        )
    )

    # Function: small_building_polygons_to_point

    small_building_polygons_to_point__building_polygons_too_small__n100 = (
        generate_file_name_gdb(
            function_name=small_building_polygons_to_point,
            description="building_polygons_too_small",
            scale=scale,
        )
    )

    small_building_polygons_to_point__building_points__n100 = generate_file_name_gdb(
        function_name=small_building_polygons_to_point,
        description="building_points",
        scale=scale,
    )

    ##############################################
    ######## CREATE CARTOGRAPHIC PARTITIONS ########
    ##############################################

    create_cartographic_partitions__cartographic_partitions__n100 = (
        generate_file_name_gdb(
            function_name=create_cartographic_partitions,
            description="cartographic_partitions",
            scale=scale,
        )
    )

    create_cartographic_partitions__cartographic_partitions_buffer__n100 = (
        generate_file_name_gdb(
            function_name=create_cartographic_partitions,
            description="cartographic_partitions_buffer",
            scale=scale,
        )
    )

    create_cartographic_partitions__buffer_erased__n100 = generate_file_name_gdb(
        function_name=create_cartographic_partitions,
        description="buffer_erased",
        scale=scale,
    )

    ##################################
    ############ ITERATION ############
    ##################################

    iteration__partition_iterator__n100 = generate_file_name_gdb(
        function_name=iteration,
        description="partition_iterator",
        scale=scale,
    )

    iteration__partition_iterator_final_output__n100 = generate_file_name_gdb(
        function_name=iteration,
        description="partition_iterator_final_output",
        scale=scale,
    )

    iteration__iteration_partition__n100 = generate_file_name_gdb(
        function_name=iteration,
        description="iteration_partition",
        scale=scale,
    )

    iteration__iteration_buffer__n100 = generate_file_name_gdb(
        function_name=iteration,
        description="iteration_buffer",
        scale=scale,
    )

    iteration__iteration_erased_buffer__n100 = generate_file_name_gdb(
        function_name=iteration,
        description="iteration_erased_buffer",
        scale=scale,
    )

    iteration__append_feature_building_point__n100 = generate_file_name_gdb(
        function_name=iteration,
        description="append_feature_building_point",
        scale=scale,
    )

    iteration__append_feature_building_polygon__n100 = generate_file_name_gdb(
        function_name=iteration,
        description="append_feature_building_polygon",
        scale=scale,
    )

    iteration__building_points_iteration_selection_append__n100 = (
        generate_file_name_gdb(
            function_name=iteration,
            description="building_points_iteration_selection_append",
            scale=scale,
        )
    )

    iteration__building_polygon_iteration_selection_append__n100 = (
        generate_file_name_gdb(
            function_name=iteration,
            description="building_polygon_iteration_selection_append",
            scale=scale,
        )
    )

    iteration__building_points_present_partition__n100 = generate_file_name_gdb(
        function_name=iteration,
        description="building_points_present_partition",
        scale=scale,
    )

    iteration__building_polygon_present_partition__n100 = generate_file_name_gdb(
        function_name=iteration,
        description="building_polygon_present_partition",
        scale=scale,
    )

    iteration__building_points_base_partition_selection__n100 = generate_file_name_gdb(
        function_name=iteration,
        description="building_points_base_partition_selection",
        scale=scale,
    )

    iteration__building_polygon_base_partition_selection__n100 = generate_file_name_gdb(
        function_name=iteration,
        description="building_polygon_base_partition_selection",
        scale=scale,
    )

    ###################################################
    ########### HOSPITAL AND CHURCH CLUSTERS ###########
    ###################################################

    # Functon: hospital_church_selections

    hospital_church_selections__hospital_points__n100 = generate_file_name_gdb(
        function_name=hospital_church_selections,
        description="hospital_points",
        scale=scale,
    )

    hospital_church_selections__church_points__n100 = generate_file_name_gdb(
        function_name=hospital_church_selections,
        description="church_points",
        scale=scale,
    )

    # Function: find_clusters

    find_clusters__all_hospital_clusters__n100 = generate_file_name_gdb(
        function_name=find_clusters,
        description="all_hospital_clusters",
        scale=scale,
    )

    find_clusters__all_church_clusters__n100 = generate_file_name_gdb(
        function_name=find_clusters,
        description="all_church_clusters",
        scale=scale,
    )

    find_clusters__hospital_points_not_in_cluster__n100 = generate_file_name_gdb(
        function_name=find_clusters,
        description="hospital_points_not_in_cluster",
        scale=scale,
    )

    find_clusters__hospital_points_in_cluster__n100 = generate_file_name_gdb(
        function_name=find_clusters,
        description="hospital_points_in_cluster",
        scale=scale,
    )

    find_clusters__church_points_not_in_cluster__n100 = generate_file_name_gdb(
        function_name=find_clusters,
        description="church_points_not_in_cluster",
        scale=scale,
    )

    find_clusters__church_points_in_cluster__n100 = generate_file_name_gdb(
        function_name=find_clusters,
        description="church_points_in_cluster",
        scale=scale,
    )

    # Function: reducing_clusters
    reducing_clusters__minimum_bounding_geometry_hospital__n100 = (
        generate_file_name_gdb(
            function_name=reducing_clusters,
            description="minimum_bounding_geometry_hospital",
            scale=scale,
        )
    )
    reducing_clusters__feature_to_point_hospital__n100 = generate_file_name_gdb(
        function_name=reducing_clusters,
        description="feature_to_point_hospital",
        scale=scale,
    )

    reducing_clusters__minimum_bounding_geometry_church__n100 = generate_file_name_gdb(
        function_name=reducing_clusters,
        description="minimum_bounding_geometry_church",
        scale=scale,
    )

    reducing_clusters__feature_to_point_church__n100 = generate_file_name_gdb(
        function_name=reducing_clusters,
        description="feature_to_point_church",
        scale=scale,
    )

    reducing_clusters__chosen_hospitals_from_cluster__n100 = generate_file_name_gdb(
        function_name=reducing_clusters,
        description="chosen_hospitals_from_cluster",
        scale=scale,
    )
    reducing_clusters__chosen_churches_from_cluster__n100 = generate_file_name_gdb(
        function_name=reducing_clusters,
        description="chosen_churches_from_cluster",
        scale=scale,
    )

    reducing_clusters__reduced_hospital_and_church_points_2__n100 = (
        generate_file_name_gdb(
            function_name=reducing_clusters,
            description="reduced_hospital_and_church_points_2",
            scale=scale,
        )
    )

    ########################################
    ######## PROPAGATE DISPLACEMENT  ########
    ########################################

    propagate_displacement__bygningspunkt_pre_propogate_displacement__n100 = (
        generate_file_name_gdb(
            function_name=propagate_displacement,
            description="bygningspunkt_pre_propogate_displacement",
            scale=scale,
        )
    )

    ########################################
    ########### ROADS TO POLYGON ###########
    ########################################

    building_point_buffer_displacement__roads_study_area__n100 = generate_file_name_gdb(
        function_name=building_point_buffer_displacement,
        description="roads_study_area",
        scale=scale,
    )

    building_point_buffer_displacement__begrensningskurve_study_area__n100 = (
        generate_file_name_gdb(
            function_name=building_point_buffer_displacement,
            description="begrensningskurve_study_area",
            scale=scale,
        )
    )

    building_point_buffer_displacement__buildings_study_area__n100 = (
        generate_file_name_gdb(
            function_name=building_point_buffer_displacement,
            description="buildings_study_area",
            scale=scale,
        )
    )

    building_point_buffer_displacement__selection_roads__n100 = generate_file_name_gdb(
        function_name=building_point_buffer_displacement,
        description="selection_roads",
        scale=scale,
    )

    building_point_buffer_displacement__align_buffer_schema_to_template__n100 = (
        generate_file_name_gdb(
            function_name=building_point_buffer_displacement,
            description="align_buffer_schema_to_template",
            scale=scale,
        )
    )

    building_point_buffer_displacement__roads_buffer__n100 = generate_file_name_gdb(
        function_name=building_point_buffer_displacement,
        description="roads_buffer",
        scale=scale,
    )

    building_point_buffer_displacement__roads_buffer_appended__n100 = (
        generate_file_name_gdb(
            function_name=building_point_buffer_displacement,
            description="roads_buffer_appended",
            scale=scale,
        )
    )

    building_point_buffer_displacement__iteration_points_to_square_polygons__n100 = (
        generate_file_name_gdb(
            function_name=building_point_buffer_displacement,
            description="iteration_points_to_square_polygons",
            scale=scale,
        )
    )

    building_point_buffer_displacement__building_polygon_erased__n100 = (
        generate_file_name_gdb(
            function_name=building_point_buffer_displacement,
            description="building_polygon_erased",
            scale=scale,
        )
    )

    building_point_buffer_displacement__displaced_building_points__n100 = (
        generate_file_name_gdb(
            function_name=building_point_buffer_displacement,
            description="displaced_building_points",
            scale=scale,
        )
    )

    #########################################
    ########### POINTS TO POLYGON ###########
    #########################################

    points_to_polygon__transform_points_to_square_polygons__n100 = (
        generate_file_name_gdb(
            function_name=points_to_polygon,
            description="transform_points_to_square_polygons",
            scale=scale,
        )
    )

    ###################################################
    ########### RESOLVE BUILDING CONFLICTS  ###########
    ###################################################

    # Function: rbc_selection

    rbc_selection__selection_area_resolve_building_conflicts__n100 = (
        generate_file_name_gdb(
            function_name=rbc_selection,
            description="selection_area_resolve_building_conflicts",
            scale=scale,
        )
    )

    rbc_selection__grunnriss_selection_rbc__n100 = generate_file_name_gdb(
        function_name=rbc_selection,
        description="grunnriss_selection_rbc",
        scale=scale,
    )

    rbc_selection__veg_sti_selection_rbc_rbc__n100 = generate_file_name_gdb(
        function_name=rbc_selection,
        description="veg_sti_selection_rbc",
        scale=scale,
    )

    rbc_selection__bygningspunkt_selection_rbc__n100 = generate_file_name_gdb(
        function_name=rbc_selection,
        description="bygningspunkt_selection_rbc",
        scale=scale,
    )

    rbc_selection__begrensningskurve_selection_rbc__n100 = generate_file_name_gdb(
        function_name=rbc_selection,
        description="begrensningskurve_selection_rbc",
        scale=scale,
    )

    rbc_selection__drawn_polygon_selection_rbc__n100 = generate_file_name_gdb(
        function_name=rbc_selection,
        description="drawn_polygon_selection_rbc",
        scale=scale,
    )

    # Function: apply_symbology

    apply_symbology__bygningspunkt_selection__n100_lyrx = generate_file_name_lyrx(
        function_name=apply_symbology,
        description="bygningspunkt_selection",
        scale=scale,
    )

    apply_symbology__grunnriss_selection__n100_lyrx = generate_file_name_lyrx(
        function_name=apply_symbology,
        description="grunnriss_selection",
        scale=scale,
    )

    apply_symbology__veg_sti_selection__n100_lyrx = generate_file_name_lyrx(
        function_name=apply_symbology,
        description="veg_sti_selection",
        scale=scale,
    )

    apply_symbology__begrensningskurve_selection__n100_lyrx = generate_file_name_lyrx(
        function_name=apply_symbology,
        description="begrensningskurve_selection",
        scale=scale,
    )

    apply_symbology__drawn_polygon_selection__n100_lyrx = generate_file_name_lyrx(
        function_name=apply_symbology,
        description="drawn_polygon_selection",
        scale=scale,
    )

    # Function: resolve_building_conflicts

    resolve_building_conflicts__drawn_polygons_result_1__n100 = generate_file_name_gdb(
        function_name=resolve_building_conflicts,
        description="drawn_polygons_result_1",
        scale=scale,
    )

    resolve_building_conflicts__drawn_polygon_RBC_result_1__n100_lyrx = (
        generate_file_name_lyrx(
            function_name=resolve_building_conflicts,
            description="drawn_polygon_RBC_result_1",
            scale=scale,
        )
    )

    resolve_building_conflicts__building_points_RBC_result_1__n100 = (
        generate_file_name_gdb(
            function_name=resolve_building_conflicts,
            description="building_points_RBC_result_1",
            scale=scale,
        )
    )

    resolve_building_conflicts__building_points_RBC_result_2__n100 = (
        generate_file_name_gdb(
            function_name=resolve_building_conflicts,
            description="building_points_RBC_result_2",
            scale=scale,
        )
    )

    resolve_building_conflicts__building_points_RBC_result_1__n100_lyrx = (
        generate_file_name_lyrx(
            function_name=resolve_building_conflicts,
            description="building_points_RBC_result_1",
            scale=scale,
        )
    )

    resolve_building_conflicts__building_points_RBC_result_2__n100_lyrx = (
        generate_file_name_lyrx(
            function_name=resolve_building_conflicts,
            description="building_points_RBC_result_2",
            scale=scale,
        )
    )

    resolve_building_conflicts__drawn_polygons_result_2__n100 = generate_file_name_gdb(
        function_name=resolve_building_conflicts,
        description="drawn_polygons_result_2",
        scale=scale,
    )

    resolve_building_conflicts__drawn_polygon_RBC_result_2__n100_lyrx = (
        generate_file_name_lyrx(
            function_name=resolve_building_conflicts,
            description="drawn_polygon_RBC_result_2",
            scale=scale,
        )
    )
