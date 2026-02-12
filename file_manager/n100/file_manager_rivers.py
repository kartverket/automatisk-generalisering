# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager


# Initialize BaseFileManager
scale = global_config.scale_n100
object_name = global_config.object_elv_bekk
file_manager = BaseFileManager(scale=scale, object_name=object_name)


##############################################################################################################################################

# All file and function names in correct order

selecting_water_polygons = "selecting_water_polygons"
unconnected_river_geometry = "unconnected_river_geometry"
extending_river_geometry = "extending_river_geometry"
river_centerline = "river_centerline"
centerline_pruning = "centerline_pruning"
thin_hydrology_lines = "thin_hydrology_lines"
centerline_pruning_loop = "centerline_pruning_loop"
river_connected = "river_connected"
river_cycles = "river_cycles"
river_strahler = "river_strahler"

##############################################################################################################################################


class River_N100(Enum):
    """
    An enumeration for river-related geospatial data file paths within the N100 scale and elv_bekk object context.

    Utilizes the BaseFileManager to generate standardized file paths for geodatabase files, general files, and layer files,
    tailored to river data preparation and analysis tasks.

    Example Syntaxes:
        - For Geodatabase (.gdb) Files:
            the_file_name_of_the_script___the_description_of_the_file___n100_elv_bekk = file_manager.generate_file_name_gdb(
                script_source_name="the_file_name_of_the_script",
                description="the_description_of_the_file",
            )

        - For General Files (e.g., .txt, .csv):
            the_file_name_of_the_script___the_description_of_the_file___n100_elv_bekk_filetype_extension = file_manager.generate_file_name_general_files(
                script_source_name="the_file_name_of_the_script",
                description="the_description_of_the_file",
                file_type="filetype_extension",
            )

        - For ArcGIS Layer Files (.lyrx):
            the_file_name_of_the_script___the_description_of_the_file___n100_elv_bekk_lyrx = file_manager.generate_file_name_lyrx(
                script_source_name="the_file_name_of_the_script",
                description="the_description_of_the_file",
            )

    These examples show how to utilize the BaseFileManager's methods to generate file paths for different types of files,
    reflecting the specific needs and naming conventions of river data management within the project.
    """

    ###########################################
    ########### RIVER DATA PREPARATION ##########
    ###########################################

    selecting_water_polygons__centerline__n100 = file_manager.generate_file_name_gdb(
        script_source_name=selecting_water_polygons,
        description="centerline",
    )

    selecting_water_polygons__geometry_gaps__n100 = file_manager.generate_file_name_gdb(
        script_source_name=selecting_water_polygons,
        description="geometry_gaps",
    )

    #################################################
    ########### UNCONNECTED RIVER GEOMETRY  ###########
    #################################################

    unconnected_river_geometry__river_area_selection__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=unconnected_river_geometry,
            description="river_area_selection",
        )
    )

    unconnected_river_geometry__unsplit_river_features__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=unconnected_river_geometry,
            description="unsplit_river_features",
        )
    )

    unconnected_river_geometry__water_area_features__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=unconnected_river_geometry,
            description="water_area_features",
        )
    )

    unconnected_river_geometry__water_area_features_selected__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=unconnected_river_geometry,
            description="water_area_features_selected",
        )
    )

    unconnected_river_geometry__river_dangles__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=unconnected_river_geometry,
            description="river_dangles",
        )
    )

    unconnected_river_selected_river_dangles__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=unconnected_river_geometry,
            description="selected_river_dangles",
        )
    )

    unconnected_river_geometry__river_end_points__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=unconnected_river_geometry,
            description="river_end_points",
        )
    )
    unconnected_river_geometry__river_dangles_buffer__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=unconnected_river_geometry,
            description="river_dangles_buffer",
        )
    )

    unconnected_river_geometry__problematic_river_lines__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=unconnected_river_geometry,
            description="problematic_river_lines",
        )
    )

    unconnected_river_geometry__problematic_river_dangles__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=unconnected_river_geometry,
            description="problematic_river_dangles",
        )
    )

    ###########################################
    ########### EXTENDING RIVER LINES  ###########
    ###########################################

    extending_river_geometry__input_rivers_copy__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=extending_river_geometry,
            description="input_rivers_copy",
        )
    )

    extending_river_geometry__exluded_objects__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=extending_river_geometry,
            description="exluded_objects",
        )
    )

    extending_river_geometry__near_table__n100 = file_manager.generate_file_name_gdb(
        script_source_name=extending_river_geometry,
        description="near_table",
    )

    extending_river_geometry__new_lines__n100 = file_manager.generate_file_name_gdb(
        script_source_name=extending_river_geometry,
        description="new_lines",
    )

    extending_river_geometry__unsplit_new_lines__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=extending_river_geometry,
            description="unsplit_new_lines",
        )
    )

    extending_river_geometry__merged_lines__n100 = file_manager.generate_file_name_gdb(
        script_source_name=extending_river_geometry,
        description="merged_lines",
    )

    extending_river_geometry__unsplit_merged_lines__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=extending_river_geometry,
            description="unsplit_merged_lines",
        )
    )

    ######################################
    ########### RIVER CENTERLINE ###########
    ######################################

    river_centerline__rivers_near_waterfeatures__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=river_centerline,
            description="rivers_near_waterfeatures",
        )
    )

    river_centerline__rivers_near_waterfeatures_erased__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=river_centerline,
            description="rivers_near_waterfeatures_erased",
        )
    )

    short__water_feature__n100 = file_manager.generate_file_name_gdb(
        script_source_name="short",
        description="water_feature",
    )

    short__water_feature_centroid__n100 = file_manager.generate_file_name_gdb(
        script_source_name="short",
        description="water_feature_centroid",
    )

    river_centerline__water_feature_centerline__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=river_centerline,
            description="water_feature_centerline",
        )
    )

    river_centerline__water_feature_collapsed__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=river_centerline,
            description="water_feature_collapsed",
        )
    )

    river_centerline__study_lake__n100 = file_manager.generate_file_name_gdb(
        script_source_name=river_centerline,
        description="study_lake",
    )

    river_centerline__study_rivers__n100 = file_manager.generate_file_name_gdb(
        script_source_name=river_centerline,
        description="study_rivers",
    )

    river_centerline__study_centerline__n100 = file_manager.generate_file_name_gdb(
        script_source_name=river_centerline,
        description="study_centerline",
    )

    river_centerline__study_lake_collapsed__n100 = file_manager.generate_file_name_gdb(
        script_source_name=river_centerline,
        description="study_lake_collapsed",
    )
    river_centerline__study_dangles__n100 = file_manager.generate_file_name_gdb(
        script_source_name=river_centerline,
        description="study_dangles",
    )

    centerline_pruning__pruned_centerline__n100 = file_manager.generate_file_name_gdb(
        script_source_name=centerline_pruning,
        description="pruned_centerline",
    )

    ######################################
    ######### THIN HYDROLOGY LINES ########
    ######################################

    thin_hydrology_lines__visible_streams__n100 = file_manager.generate_file_name_gdb(
        script_source_name=thin_hydrology_lines,
        description="visible_streams",
    )

    #################################################
    ########### RIVER CENTERLINE PROONING LOOP ###########
    #################################################

    centerline_pruning_loop__lake_features__n100 = file_manager.generate_file_name_gdb(
        script_source_name=centerline_pruning_loop,
        description="lake_features",
    )

    centerline_pruning_loop__rivers_erased_with_lake_features__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="rivers_erased_with_lake_features",
        )
    )

    centerline_pruning_loop__study_area__n100 = file_manager.generate_file_name_gdb(
        script_source_name=centerline_pruning_loop,
        description="study_area",
    )

    centerline_pruning_loop__water_features_study_area__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="water_features_study_area",
        )
    )

    centerline_pruning_loop__water_features_dissolved__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="water_features_dissolved",
        )
    )

    centerline_pruning_loop__water_features_dissolved_river_intersect__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="water_features_dissolved_river_intersect",
        )
    )

    centerline_pruning_loop__water_features_river_final_selection__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="water_features_river_final_selection",
        )
    )

    centerline_pruning_loop__water_features_processed__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="water_features_processed",
        )
    )

    centerline_pruning_loop__polygon_to_line__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="polygon_to_line",
        )
    )

    centerline_pruning_loop__water_features_shared_boundaries__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="water_features_shared_boundaries",
        )
    )

    centerline_pruning_loop__shared_boundaries_midpoint__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="shared_boundaries_midpoint",
        )
    )

    centerline_pruning_loop__river_inlets__n100 = file_manager.generate_file_name_gdb(
        script_source_name=centerline_pruning_loop,
        description="river_inlets",
    )

    centerline_pruning_loop__river_inlets_erased__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="river_inlets_erased",
        )
    )

    centerline_pruning_loop__river_inlets_points_merged__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="river_inlets_points_merged",
        )
    )

    short_name__water__n100 = file_manager.generate_file_name_gdb(
        script_source_name="short_name",
        description="water",
    )

    centerline_pruning_loop__collapsed_hydropolygon__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="collapsed_hydropolygon",
        )
    )

    centerline_pruning_loop__collapsed_hydropolygon_points__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="collapsed_hydropolygon_points",
        )
    )

    centerline_pruning_loop__collapsed_hydropolygon_points_selected__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="collapsed_hydropolygon_points_selected",
        )
    )

    centerline_pruning_loop__closed_centerline_lines__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="closed_centerline_lines",
        )
    )

    centerline_pruning_loop__closed_centerline_point__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="closed_centerline_point",
        )
    )

    centerline_pruning_loop__intersection_points_merged__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="intersection_points_merged",
        )
    )

    centerline_pruning_loop__centerline_start_end_vertex__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="centerline_start_end_vertex",
        )
    )

    centerline_pruning_loop__centerline_intersection_vertex__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="centerline_intersection_vertex",
        )
    )

    centerline_pruning_loop__river_inlet_dangles__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="river_inlet_dangles",
        )
    )

    centerline_pruning_loop__water_feature_summarized__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="water_feature_summarized",
        )
    )

    centerline_pruning_loop__simple_water_features__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="simple_water_features",
        )
    )

    centerline_pruning_loop__complex_water_features__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="complex_water_features",
        )
    )

    centerline_pruning_loop__simple_centerlines__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="simple_centerlines",
        )
    )

    centerline_pruning_loop__complex_centerlines__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="complex_centerlines",
        )
    )

    centerline_pruning_loop__finnished_centerlines__n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=centerline_pruning_loop,
            description="finnished_centerlines",
        )
    )

    #################################################
    ################ RIVER CONNECTED ################
    #################################################

    river_connected___connected_river_lines_root___n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=river_connected,
            description="connected_river_lines_root",
        )
    )

    river_connected___connected_river_lines___n100 = (
        file_manager.generate_file_name_gdb(
            script_source_name=river_connected,
            description="connected_river_lines",
        )
    )

    river_connected___havflate___n100 = file_manager.generate_file_name_gdb(
        script_source_name=river_connected,
        description="havflate",
    )

    #################################################
    ################# RIVER CYCLES ##################
    #################################################

    river_cycles___remove_cycles_root___n100 = file_manager.generate_file_name_gdb(
        script_source_name=river_cycles,
        description="remove_cycles_root",
    )

    river_cycles___partition_root___n100 = file_manager.generate_file_name_gdb(
        script_source_name=river_cycles,
        description="partition_root",
    )

    river_cycles___removed_cycles___n100 = file_manager.generate_file_name_gdb(
        script_source_name=river_cycles,
        description="removed_cycles",
    )

    river_cycles_docu___n100 = file_manager.generate_general_subdirectory(
        description="river_cycles_docu",
    )

    #################################################
    ################ RIVER STRAHLER #################
    #################################################

    river_strahler___root___n100 = file_manager.generate_file_name_gdb(
        script_source_name=river_strahler,
        description="root",
    )

    river_strahler___calculated_strahler___n100 = file_manager.generate_file_name_gdb(
        script_source_name=river_strahler,
        description="calculated_strahler",
    )
