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
    return rf"{relative_path_gdb}\{function_name}__{description}__{scale}"


def generate_file_name_general_files(
    function_name,
    description,
    scale,
    file_type,
):
    return rf"{relative_path_general_files}\{function_name}__{description}__{scale}.{file_type}"


def generate_file_name_lyrx(
    function_name,
    description,
    scale,
):
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
simplify_building_polygons = "simplify_building_polygons"

# create_points_from_polygon.py
points_to_polygon = "points_to_polygon"

# hospital_church_clusters.py
hospital_church_selections = "hospital_church_selections"
find_and_remove_clusters = "find_and_remove_clusters"

# resolve_building_conflicts.py
rbc_selection = "rbc_selection"
apply_symbology = "apply_symbology"
resolve_building_conflicts = "resolve_building_conflicts"

##############################################################################################################################################


class Building_N100(Enum):

    """
    This class stores all the file names used when generalizing buildings

    File-names for are built up of:
    - Function name
    - Description of what is being done / tool
    - Scale we are generalizing to

    """

    #################################################
    ########### BUILDING DATA PREPARATION ###########
    #################################################

    preparation_begrensningskurve__selected_waterfeatures_from_begrensningskurve__n100 = generate_file_name_gdb(
        function_name=preparation_begrensningskurve,
        description="selected_waterfeatures_from_begrensningskurve",
        scale=scale,
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

    grunnriss_to_point__aggregated_polygon__n100 = generate_file_name_gdb(
        function_name=grunnriss_to_point,
        description="aggregated_polygon",
        scale=scale,
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

    grunnriss_to_point__simplified_building_points_simplified_building_1__n100 = (
        generate_file_name_gdb(
            function_name=grunnriss_to_point,
            description="simplified_building_points_simplified_building_1",
            scale=scale,
        )
    )

    grunnriss_to_point__simplified_building_points_simplified_building_2__n100 = (
        generate_file_name_gdb(
            function_name=grunnriss_to_point,
            description="simplified_building_points_simplified_building_2",
            scale=scale,
        )
    )

    grunnriss_to_point__collapsed_points_simplified_polygon__n100 = (
        generate_file_name_gdb(
            function_name=grunnriss_to_point,
            description="collapsed_points_simplified_polygon",
            scale=scale,
        )
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

    # Function: simplify_building_polygons

    simplify_building_polygons__simplified_building_1__n100 = generate_file_name_gdb(
        function_name=simplify_building_polygons,
        description="simplified_building_1",
        scale=scale,
    )

    simplify_building_polygons__simplified_building_2__n100 = generate_file_name_gdb(
        function_name=simplify_building_polygons,
        description="simplified_building_2",
        scale=scale,
    )

    simplify_building_polygons__simplified_polygon__n100 = generate_file_name_gdb(
        function_name=simplify_building_polygons,
        description="simplified_polygon",
        scale=scale,
    )

    simplify_building_polygons__simplified_grunnriss__n100 = generate_file_name_gdb(
        function_name=simplify_building_polygons,
        description="simplified_grunnriss",
        scale=scale,
    )

    simplify_building_polygons__spatial_joined_polygon__n100 = generate_file_name_gdb(
        function_name=simplify_building_polygons,
        description="spatial_joined_polygon",
        scale=scale,
    )

    ####################################################
    ########### HOSPITAL AND CHURCH CLUSTERS ###########
    ####################################################

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

    # Function: find_and_remove_clusters

    find_and_remove_clusters__all_hospital_clusters__n100 = generate_file_name_gdb(
        function_name=find_and_remove_clusters,
        description="all_hospital_clusters",
        scale=scale,
    )

    find_and_remove_clusters__all_church_clusters__n100 = generate_file_name_gdb(
        function_name=find_and_remove_clusters,
        description="all_church_clusters",
        scale=scale,
    )

    find_and_remove_clusters_hospital_points_not_in_cluster_n100 = (
        generate_file_name_gdb(
            function_name=find_and_remove_clusters,
            description="hospital_points_not_in_cluster",
            scale=scale,
        )
    )

    find_and_remove_clusters_hospital_points_in_cluster_n100 = generate_file_name_gdb(
        function_name=find_and_remove_clusters,
        description="hospital_points_in_cluster",
        scale=scale,
    )

    find_and_remove_clusters_church_points_not_in_cluster_n100 = generate_file_name_gdb(
        function_name=find_and_remove_clusters,
        description="church_points_not_in_cluster",
        scale=scale,
    )

    find_and_remove_clusters_church_points_in_cluster_n100 = generate_file_name_gdb(
        function_name=find_and_remove_clusters,
        description="church_points_in_cluster",
        scale=scale,
    )

    find_and_remove_clusters__minimum_bounding_geometry_hospital__n100 = (
        generate_file_name_gdb(
            function_name=find_and_remove_clusters,
            description="minimum_bounding_geometry_hospital",
            scale=scale,
        )
    )

    find_and_remove_clusters__feature_to_point_hospital__n100 = generate_file_name_gdb(
        function_name=find_and_remove_clusters,
        description="feature_to_point_hospital",
        scale=scale,
    )

    find_and_remove_clusters__minimum_bounding_geometry_church__n100 = (
        generate_file_name_gdb(
            function_name=find_and_remove_clusters,
            description="minimum_bounding_geometry_church",
            scale=scale,
        )
    )

    find_and_remove_clusters__feature_to_point_church__n100 = generate_file_name_gdb(
        function_name=find_and_remove_clusters,
        description="feature_to_point_church",
        scale=scale,
    )

    find_and_remove_clusters__chosen_hospitals_from_cluster__n100 = (
        generate_file_name_gdb(
            function_name=find_and_remove_clusters,
            description="chosen_hospitals_from_cluster",
            scale=scale,
        )
    )

    find_and_remove_clusters__chosen_churches_from_cluster__n100 = (
        generate_file_name_gdb(
            function_name=find_and_remove_clusters,
            description="chosen_churches_from_cluster",
            scale=scale,
        )
    )

    find_and_remove_clusters__reduced_hospital_and_church_points_2__n100 = (
        generate_file_name_gdb(
            function_name=find_and_remove_clusters,
            description="reduced_hospital_and_church_points_2",
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
