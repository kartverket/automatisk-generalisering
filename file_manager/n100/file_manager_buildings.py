from enum import Enum
import config
from env_setup import setup_directory_structure

# Scale name
scale = setup_directory_structure.scale_n100

# Object name
object = setup_directory_structure.object_bygning

# Relative path to geodatabase
relative_path_gdb = (
    rf"{config.output_folder}\automatic_generalization_outputs\{scale}\{object}.gdb"
)

# Relative path to geodatabase
relative_path_sub_dir = (
    rf"{config.output_folder}\automatic_generalization_outputs\{scale}"
)


# Creating file names based on set standard
def generate_file_name_gdb(function_name, description, scale):
    return rf"{relative_path_gdb}\{function_name}__{description}__{scale}"


def generate_file_name_sub_dir(function_name, description, scale, file_type):
    return (
        rf"{relative_path_sub_dir}\{function_name}__{description}__{scale}.{file_type}"
    )


preparation_begrensningskurve = "preparation_begrensningskurve"
preperation_veg_sti = "preperation_veg_sti"
adding_matrikkel_as_points = "adding_matrikkel_as_points"
selecting_grunnriss_for_generalization = "selecting_grunnriss_for_generalization"
table_management = "table_management"
grunnriss_to_point = "grunnriss_to_point"
simplify_building_polygons = "simplify_building_polygons"
points_to_polygon = "points_to_polygon"
find_point_clusters = "find_point_clusters"

resolve_building_conflicts = "resolve_building_conflicts"

file_function = {
    "building_data_preparation": [
        preparation_begrensningskurve,
        preperation_veg_sti,
        adding_matrikkel_as_points,
        selecting_grunnriss_for_generalization,
    ],
    "create_simplified_building_polygons": [simplify_building_polygons],
    "create_points_from_polygon": [grunnriss_to_point, find_point_clusters],
    "calculating_values": [table_management],
    "resolve_building_conflicts": [resolve_building_conflicts],
}


class Building_N100(Enum):
    ########### BUILDING DATA PREPARATION ###########

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

    # adding_matrikkel_as_points

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

    # selecting_grunnriss_for_generalization

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

    ########### CALCULATING VALUES ###########

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

    table_management__building_points_with_undefined_nbr_values__n100 = (
        generate_file_name_sub_dir(
            function_name=table_management,
            description="building_points_with_undefined_nbr_values",
            scale=scale,
            file_type="txt",
        )
    )

    ########### CREATE POINTS FROM POLYGON ###########

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

    ########### CREATE SIMPLIFIED BUILDING POLYGONS ###########

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

    ########### FIND POINT CLUSTERS ###########

    find_point_clusters__reduced_hospital_church_points__n100 = generate_file_name_gdb(
        function_name=find_point_clusters,
        description="reduced_hospital_church_points",
        scale=scale,
    )
    ########### POINTS TO POLYGON ###########

    points_to_polygon__transform_points_to_square_polygons__n100 = (
        generate_file_name_gdb(
            function_name=points_to_polygon,
            description="transform_points_to_square_polygons",
            scale=scale,
        )
    )

    ########### RESOLVE BUILDING CONFLICTS ###########

    resolve_building_conflicts__conflicts_bygningspunkt_result_1__n100 = (
        generate_file_name_gdb(
            function_name=resolve_building_conflicts,
            description="conflicts_bygningspunkt_result_1",
            scale=scale,
        )
    )

    resolve_building_conflicts__conflicts_bygningspunkt_result_2__n100 = (
        generate_file_name_gdb(
            function_name=resolve_building_conflicts,
            description="conflicts_bygningspunkt_result_2",
            scale=scale,
        )
    )

    resolve_building_conflicts__conflicts_bygningspunkt_result_3__n100 = (
        generate_file_name_gdb(
            function_name=resolve_building_conflicts,
            description="conflicts_bygningspunkt_result_3",
            scale=scale,
        )
    )


class PermanentFiles(Enum):
    n100_building_points_undefined_nbr_values = (
        "n100_building_points_undefined_nbr_values"
    )
