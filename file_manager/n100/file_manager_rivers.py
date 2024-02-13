# Imports
from enum import Enum
import config
import env_setup.global_config

# Local root directory
local_root_directory = config.output_folder

# Project root directory
project_root_directory = env_setup.global_config.main_directory_name

# Scale name
scale = env_setup.global_config.scale_n100

# Object name
object = env_setup.global_config.object_elv_bekk

# General files directory name
general_files_directory_name = env_setup.global_config.general_files_name

# Lyrx directory name
lyrx_directory_name = env_setup.global_config.lyrx_directory_name

# Relative paths constructor
relative_path_gdb = (
    rf"{local_root_directory}\{project_root_directory}\{scale}\{object}.gdb"
)

relative_path_general_files = rf"{local_root_directory}\{project_root_directory}\{scale}\{general_files_directory_name}"

relative_path_lyrx = (
    rf"{local_root_directory}\{project_root_directory}\{scale}\{lyrx_directory_name}"
)


##############################################################################################################################################


# Creating file names based on set standard
def generate_file_name_gdb(
    function_name,
    description,
    scale,
):
    """
    Summary:
        Generates the full file path for files which can be stored in gdb's, where the files are generated to the river.gdb in the n100 subdirectory.

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
unconnected_river_geometry = "unconnected_river_geometry"
extending_river_geometry = "extending_river_geometry"
river_centerline = "river_centerline"
centerline_pruning = "centerline_pruning"
centerline_pruning_loop = "centerline_pruning_loop"

##############################################################################################################################################


class River_N100(Enum):
    #################################################
    ########### UNCONNECTED RIVER GEOMETRY  ###########
    #################################################

    unconnected_river_geometry__river_area_selection__n100 = generate_file_name_gdb(
        function_name=unconnected_river_geometry,
        description="river_area_selection",
        scale=scale,
    )

    unconnected_river_geometry__unsplit_river_features__n100 = generate_file_name_gdb(
        function_name=unconnected_river_geometry,
        description="unsplit_river_features",
        scale=scale,
    )

    unconnected_river_geometry__water_area_features__n100 = generate_file_name_gdb(
        function_name=unconnected_river_geometry,
        description="water_area_features",
        scale=scale,
    )

    unconnected_river_geometry__water_area_features_selected__n100 = (
        generate_file_name_gdb(
            function_name=unconnected_river_geometry,
            description="water_area_features_selected",
            scale=scale,
        )
    )

    unconnected_river_geometry__river_dangles__n100 = generate_file_name_gdb(
        function_name=unconnected_river_geometry,
        description="river_dangles",
        scale=scale,
    )

    unconnected_river_selected_river_dangles__n100 = generate_file_name_gdb(
        function_name=unconnected_river_geometry,
        description="selected_river_dangles",
        scale=scale,
    )

    unconnected_river_geometry__river_end_points__n100 = generate_file_name_gdb(
        function_name=unconnected_river_geometry,
        description="river_end_points",
        scale=scale,
    )
    unconnected_river_geometry__river_dangles_buffer__n100 = generate_file_name_gdb(
        function_name=unconnected_river_geometry,
        description="river_dangles_buffer",
        scale=scale,
    )

    unconnected_river_geometry__problematic_river_lines__n100 = generate_file_name_gdb(
        function_name=unconnected_river_geometry,
        description="problematic_river_lines",
        scale=scale,
    )

    unconnected_river_geometry__problematic_river_dangles__n100 = (
        generate_file_name_gdb(
            function_name=unconnected_river_geometry,
            description="problematic_river_dangles",
            scale=scale,
        )
    )

    #################################################
    ########### EXTENDING RIVER LINES ###########
    #################################################

    extending_river_geometry__input_rivers_copy__n100 = generate_file_name_gdb(
        function_name=extending_river_geometry,
        description="input_rivers_copy",
        scale=scale,
    )

    extending_river_geometry__exluded_objects__n100 = generate_file_name_gdb(
        function_name=extending_river_geometry,
        description="exluded_objects",
        scale=scale,
    )

    extending_river_geometry__near_table__n100 = generate_file_name_gdb(
        function_name=extending_river_geometry,
        description="near_table",
        scale=scale,
    )

    extending_river_geometry__new_lines__n100 = generate_file_name_gdb(
        function_name=extending_river_geometry,
        description="new_lines",
        scale=scale,
    )

    extending_river_geometry__unsplit_new_lines__n100 = generate_file_name_gdb(
        function_name=extending_river_geometry,
        description="unsplit_new_lines",
        scale=scale,
    )

    extending_river_geometry__merged_lines__n100 = generate_file_name_gdb(
        function_name=extending_river_geometry,
        description="merged_lines",
        scale=scale,
    )

    extending_river_geometry__unsplit_merged_lines__n100 = generate_file_name_gdb(
        function_name=extending_river_geometry,
        description="unsplit_merged_lines",
        scale=scale,
    )

    #################################################
    ########### RIVER CENTERLINE ###########
    #################################################

    river_centerline__rivers_near_waterfeatures__n100 = generate_file_name_gdb(
        function_name=river_centerline,
        description="rivers_near_waterfeatures",
        scale=scale,
    )

    river_centerline__rivers_near_waterfeatures_erased__n100 = generate_file_name_gdb(
        function_name=river_centerline,
        description="rivers_near_waterfeatures_erased",
        scale=scale,
    )

    short__water_feature__n100 = generate_file_name_gdb(
        function_name="short",
        description="water_feature",
        scale=scale,
    )

    short__water_feature_centroid__n100 = generate_file_name_gdb(
        function_name="short",
        description="water_feature_centroid",
        scale=scale,
    )

    river_centerline__water_feature_centerline__n100 = generate_file_name_gdb(
        function_name=river_centerline,
        description="water_feature_centerline",
        scale=scale,
    )

    river_centerline__water_feature_collapsed__n100 = generate_file_name_gdb(
        function_name=river_centerline,
        description="water_feature_collapsed",
        scale=scale,
    )

    river_centerline__study_lake__n100 = generate_file_name_gdb(
        function_name=river_centerline,
        description="study_lake",
        scale=scale,
    )

    river_centerline__study_rivers__n100 = generate_file_name_gdb(
        function_name=river_centerline,
        description="study_rivers",
        scale=scale,
    )

    river_centerline__study_centerline__n100 = generate_file_name_gdb(
        function_name=river_centerline,
        description="study_centerline",
        scale=scale,
    )

    river_centerline__study_lake_collapsed__n100 = generate_file_name_gdb(
        function_name=river_centerline,
        description="study_lake_collapsed",
        scale=scale,
    )
    river_centerline__study_dangles__n100 = generate_file_name_gdb(
        function_name=river_centerline,
        description="study_dangles",
        scale=scale,
    )

    centerline_pruning__pruned_centerline__n100 = generate_file_name_gdb(
        function_name=centerline_pruning,
        description="pruned_centerline",
        scale=scale,
    )

    #################################################
    ########### RIVER CENTERLINE PROONING LOOP ###########
    #################################################

    centerline_pruning_loop__centerline_start_end_vertex__n100 = generate_file_name_gdb(
        function_name=centerline_pruning_loop,
        description="centerline_start_end_vertex",
        scale=scale,
    )

    centerline_pruning_loop__centerline_intersection_vertex__n100 = (
        generate_file_name_gdb(
            function_name=centerline_pruning_loop,
            description="centerline_intersection_vertex",
            scale=scale,
        )
    )

    centerline_pruning_loop__river_inlet_dangles__n100 = generate_file_name_gdb(
        function_name=centerline_pruning_loop,
        description="river_inlet_dangles",
        scale=scale,
    )

    centerline_pruning_loop__water_feature_summarized__n100 = generate_file_name_gdb(
        function_name=centerline_pruning_loop,
        description="water_feature_summarized",
        scale=scale,
    )

    centerline_pruning_loop__simple_water_features__n100 = generate_file_name_gdb(
        function_name=centerline_pruning_loop,
        description="simple_water_features",
        scale=scale,
    )

    centerline_pruning_loop__complex_water_features__n100 = generate_file_name_gdb(
        function_name=centerline_pruning_loop,
        description="complex_water_features",
        scale=scale,
    )
