# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager


# Initialize BaseFileManager
scale = global_config.scale_n250
object_name = global_config.object_veg_sti
file_manager = BaseFileManager(scale=scale, object_name=object_name)


# All scripts
data_selection = "data_selection"
data_preparation = "data_preparation"
roundabout_file = "roundabout"
dam_file = "dam"
road_triangles = "road_triangles"
major_road_crossings = "major_road_crossings"
vegsperring_file = "vegsperring"
ramps_file = "ramps"

""""
# gdb
    data_selection___example___n250_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="example",
    )
    
# csv
    data_selection___example_csv___n250_road = (
        file_manager.generate_file_name_general_files(
            script_source_name="data_selection",
            description="example_csv",
            file_type="csv",
        )
    )
# lyrx
    data_selection___example_lyrx___n250_road_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name="data_selection",
            description="example_lyrx___n250_road",
        )
    )
# final output
    Road = file_manager.generate_final_outputs(
        file_name="Road",
    )
    
# lyrx directory
    data_selection___lyrx_root___n250_road= (
        file_manager.generate_file_lyrx_directory(
            script_source_name=data_selection, description="lyrx_root"
        )
    )

"""


class Road_N250(Enum):
    # ========================================
    #                           DATA SELECTION
    # ========================================

    data_selection___nvdb_roads___n250_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="nvdb_roads",
    )

    data_selection___vegsperring___n250_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="vegsperring",
    )

    data_selection___railroad___n250_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="railroad",
    )

    data_selection___admin_boundary___n250_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="admin_boundary",
    )

    data_selection___begrensningskurve___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="begrensningskurve",
        )
    )

    data_selection___new_road_symbology___n250_road_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=data_selection,
            description="new_road_symbology",
        )
    )

    # ========================================
    #                         DATA PREPARATION
    # ========================================

    data_preparation___geometry_validation___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="geometry_validation",
        )
    )

    data_preparation___water_feature_outline___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="water_feature_outline",
        )
    )

    data_preparation___road_single_part___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="road_single_part",
        )
    )

    data_preparation___road_single_part_2___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="road_single_part_2",
        )
    )

    data_preparation___car_raod___n250_road = file_manager.generate_file_name_gdb(
        script_source_name=data_preparation,
        description="car_raod",
    )

    data_preparation___road_dangle___n250_road = file_manager.generate_file_name_gdb(
        script_source_name=data_preparation,
        description="road_dangle",
    )

    data_preparation___boarder_road_dangle___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="boarder_road_dangle",
        )
    )

    data_preparation___boarder_road___n250_road = file_manager.generate_file_name_gdb(
        script_source_name=data_preparation,
        description="boarder_road",
    )

    data_preparation___on_surface_selection___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="on_surface_selection",
        )
    )

    data_preparation___bridge_selection___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="bridge_selection",
        )
    )

    data_preparation___tunnel_selection___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="tunnel_selection",
        )
    )

    data_preparation___dissolved_road_feature___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="dissolved_road_feature",
        )
    )

    data_preparation___intersections_root___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="intersections_root",
        )
    )

    data_preparation___dissolved_road_feature_2___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="dissolved_road_feature_2",
        )
    )

    data_preparation___dissolved_intersections___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="dissolved_intersections",
        )
    )

    data_preparation___country_boarder___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="country_boarder",
        )
    )

    data_preparation___country_boarder_buffer___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="country_boarder_buffer",
        )
    )

    data_preparation___roads_near_boarder___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="roads_near_boarder",
        )
    )

    data_preparation___removed_roads_near_boarder___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="removed_roads_near_boarder",
        )
    )

    data_preparation___intersections_root_2___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="intersections_root_2",
        )
    )

    data_preparation___intersections_root_3___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="intersections_root_3",
        )
    )

    data_preparation___intersections_root_4___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="intersections_root_4",
        )
    )

    data_preparation___intersections_root_5___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="intersections_root_5",
        )
    )

    data_preparation___dissolved_intersections_2___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="dissolved_intersections_2",
        )
    )

    data_preparation___dissolved_intersections_3___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="dissolved_intersections_3",
        )
    )

    data_preparation___root_calculate_boarder_hierarchy___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="root_calculate_boarder_hierarchy",
        )
    )

    data_preparation___calculated_boarder_hierarchy___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="calculated_boarder_hierarchy",
        )
    )

    data_preparation___dissolved_intersections_4___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="dissolved_intersections_4",
        )
    )

    data_preparation___dissolved_intersections_5___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="dissolved_intersections_5",
        )
    )

    data_preparation___merge_divided_roads___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="merge_divided_roads",
        )
    )

    data_preparation___merge_divided_roads_displacement_feature___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="merge_divided_roads_displacement_feature",
        )
    )

    data_preparation___divided_roads_merged_outputs___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="divided_roads_merged_outputs",
        )
    )

    data_preparation___remove_small_road_lines___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="remove_small_road_lines",
        )
    )

    data_preparation___collapse_road_detail___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="collapse_road_detail",
        )
    )

    data_preparation___road_bridge_and_tunnel_selection___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="road_bridge_and_tunnel_selection",
        )
    )

    data_preparation___road_on_surface_selection___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="road_on_surface_selection",
        )
    )
    data_preparation___on_surface_feature_to_line___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="on_surface_feature_to_line",
        )
    )

    data_preparation___simplified_road___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="simplified_road",
        )
    )

    data_preparation___thin_road_sti_root___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_sti_root",
        )
    )

    data_preparation___thin_sti_partition_root___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_sti_partition_root",
        )
    )

    thin_sti_docu___n250_road = file_manager.generate_general_subdirectory(
        description="thin_sti_docu",
    )

    data_preparation___thin_road_sti_output___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_sti_output",
        )
    )

    data_preparation___thin_road_root___n250_road = file_manager.generate_file_name_gdb(
        script_source_name=data_preparation,
        description="thin_road_root",
    )

    data_preparation___thin_road_root_2___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_root_2",
        )
    )

    data_preparation___thin_road_root_3___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_root_3",
        )
    )

    data_preparation___thin_road_partition_root___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_partition_root",
        )
    )

    data_preparation___thin_road_partition_root_2___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_partition_root_2",
        )
    )

    data_preparation___thin_road_partition_root_3___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_partition_root_3",
        )
    )

    thin_road_docu___n250_road = file_manager.generate_general_subdirectory(
        description="thin_road_docu",
    )

    collapse_road_docu___n250_road = file_manager.generate_general_subdirectory(
        description="collapse_road_docu",
    )

    data_preparation___thin_road_docu_2___n250_road = (
        file_manager.generate_file_name_general_files(
            script_source_name=data_preparation,
            description="thin_road_docu_2",
            file_type="json",
        )
    )

    data_preparation___thin_road_docu_3___n250_road = (
        file_manager.generate_file_name_general_files(
            script_source_name=data_preparation,
            description="thin_road_docu_3",
            file_type="json",
        )
    )

    data_preparation___thin_road_output___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_output",
        )
    )

    data_preparation___thin_road_output_2___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_output_2",
        )
    )

    data_preparation___thin_road_output_3___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_output_3",
        )
    )

    data_preparation___final_merged_thin_iteration_output___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="final_merged_thin_iteration_output",
        )
    )

    data_preparation___smooth_road___n250_road = file_manager.generate_file_name_gdb(
        script_source_name=data_preparation,
        description="smooth_road",
    )

    data_preparation___road_single_part_3___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="road_single_part_3",
        )
    )

    data_preparation___calculated_boarder_hierarchy_2___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="calculated_boarder_hierarchy_2",
        )
    )

    data_preparation___root_calculate_boarder_hierarchy_2___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="root_calculate_boarder_hierarchy_2",
        )
    )

    data_preparation___railroad_single_part___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="railroad_single_part",
        )
    )

    data_preparation___water_feature_outline_single_part___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="water_feature_outline_single_part",
        )
    )

    data_preparation___resolve_road_conflicts___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="resolve_road_conflicts",
        )
    )

    data_preparation___road_final_output___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="road_final_output",
        )
    )

    data_preparation___resolve_road_partition_root___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="resolve_road_partition_root",
        )
    )

    resolve_road_docu___n250_road = file_manager.generate_general_subdirectory(
        description="resolve_road_docu",
    )

    data_preparation___resolve_road_root___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="resolve_road_root",
        )
    )

    data_preparation___resolve_road_conflicts_displacement_feature___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="resolve_road_conflicts_displacement_feature",
        )
    )

    data_preperation___paths_n50___n250_road = file_manager.generate_file_name_gdb(
        script_source_name=data_preparation,
        description="paths_n50",
    )

    data_preperation___selecting_vegtrase_and_kjorebane_nvdb___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="selecting_vegtrase_and_kjorebane_nvdb",
        )
    )

    data_preperation___selecting_everything_but_rampe_nvdb___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="selecting_everything_but_rampe_nvdb",
        )
    )

    data_preperation___selecting_everything_but_rampe_with_calculated_fields_nvdb___n250_road = file_manager.generate_file_name_gdb(
        script_source_name=data_preparation,
        description="selecting_everything_but_rampe_with_calculated_fields_nvdb",
    )

    # ========================================
    #                           ROAD TRIANGLES
    # ========================================

    road_triangles_output = file_manager.generate_file_name_gdb(
        script_source_name=road_triangles, description="road_triangles_output"
    )

    road_triangles___roads_copy___n250_road = file_manager.generate_file_name_gdb(
        script_source_name=road_triangles,
        description="roads_copy",
    )

    road_triangles___graph_root___n250_road = file_manager.generate_file_name_gdb(
        script_source_name=road_triangles,
        description="graph_root",
    )

    road_triangles___remove_triangles_root___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=road_triangles,
            description="remove_triangles_root",
        )
    )

    road_triangles___removed_triangles___n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=road_triangles,
            description="removed_triangles",
        )
    )

    # ========================================
    #                               ROUNDABOUT
    # ========================================

    roundabout__roundabout__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=roundabout_file, description="roundabout"
    )

    roundabout__centroids__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=roundabout_file, description="centroids"
    )

    roundabout__cleaned_road__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=roundabout_file, description="cleaned_road"
    )

    # ========================================
    #                                      DAM
    # ========================================

    dam__relevant_roads__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="relevant_roads"
    )

    dam__relevant_dam__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="relevant_dam"
    )

    dam__relevant_water__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="relevant_water"
    )

    dam__dam_buffer_35m__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="dam_buffer_35m"
    )

    dam__roads_inside_with_data__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="roads_inside_with_data"
    )

    dam__roads_outside__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="roads_outside"
    )

    dam__water_clipped__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="water_clipped"
    )

    dam__water_center__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="water_center"
    )

    dam__buffer_water__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="buffer_water"
    )

    dam__water_singleparts__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="water_singleparts"
    )

    dam__dam_buffer_sti__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="dam_buffer_sti"
    )

    dam__roads_clipped_sti__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="roads_clipped_sti"
    )

    dam__roads_moved__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="roads_moved"
    )

    dam__roads_shifted__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="roads_shifted"
    )

    dam__dam_buffer_150m__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="dam_buffer_150m"
    )

    dam__dam_buffer_60m_flat__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="dam_buffer_60m_flat"
    )

    dam__dam_buffer_5m_flat__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="dam_buffer_5m_flat"
    )

    dam__dam_buffer_60m__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="dam_buffer_60m"
    )

    dam__water_buffer_55m__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="water_buffer_55m"
    )

    dam__dam_buffer_60m_line__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="dam_buffer_60m_line"
    )

    dam__roads_intermediate__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="roads_intermediate"
    )

    dam__paths_in_dam__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="paths_in_dam"
    )

    dam__paths_in_dam_valid__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="paths_in_dam_valid"
    )

    dam__cleaned_roads__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="cleaned_roads"
    )

    # ========================================
    #                     MAJOR ROAD CROSSINGS
    # ========================================

    major_road_crossing__road_u__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="road_u"
    )

    major_road_crossing__road_u_buffer__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="road_u_buffer"
    )

    major_road_crossing__road_u_buffer_shrunked__n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=major_road_crossings,
            description="road_u_buffer_shrunked",
        )
    )

    major_road_crossing__road_l__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="road_l"
    )

    major_road_crossing__road_l_buffer__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="road_l_buffer"
    )

    major_road_crossing__road_l_buffer_shrunked__n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=major_road_crossings,
            description="road_l_buffer_shrunked",
        )
    )

    major_road_crossing__ER__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="ER"
    )

    major_road_crossing__ER_bridge__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="ER_bridge"
    )

    major_road_crossing__ER_bridge_buffer__n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=major_road_crossings, description="ER_bridge_buffer"
        )
    )

    major_road_crossing__ER_bridge_shrunked__n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=major_road_crossings, description="ER_bridge_shrunked"
        )
    )

    major_road_crossing__road_t__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="road_t"
    )

    major_road_crossing__ER_t__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="ER_t"
    )

    major_road_crossing__bridge_cross_ER__n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=major_road_crossings, description="bridge_cross_ER"
        )
    )

    major_road_crossing__underpass_cross_ER__n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=major_road_crossings, description="underpass_cross_ER"
        )
    )

    major_road_crossing__surface_under_ER__n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=major_road_crossings, description="surface_under_ER"
        )
    )

    major_road_crossing__keep_bru_ERFKP__n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=major_road_crossings, description="keep_bru_ERFKP"
        )
    )

    major_road_crossing__keep_underpass_ERFKP__n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=major_road_crossings, description="keep_underpass_ERFKP"
        )
    )

    major_road_crossing__keep_surface_ERFKP__n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=major_road_crossings, description="keep_surface_FKP"
        )
    )

    major_road_crossing__merged_keep__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="merged_keep"
    )

    major_road_crossing__output__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="output"
    )

    # ========================================
    #                              VEGSPERRING
    # ========================================

    vegsperring__veg_uten_bom__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=vegsperring_file, description="veg_uten_bom"
    )
    # ========================================
    #                                    RAMPS
    # ========================================

    ramps__ramps__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=ramps_file, description="ramps"
    )

    ramps__collapsed_roundabouts__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=ramps_file, description="collapsed_roundabouts"
    )

    ramps__small_roundabouts__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=ramps_file, description="small_roundabouts"
    )

    ramps__roads_with_cleaned_roundabouts__n250_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=ramps_file, description="roads_with_cleaned_roundabouts"
        )
    )

    ramps__buffered_ramps__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=ramps_file, description="buffered_ramps"
    )

    ramps__buffered_ramps_100__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=ramps_file, description="buffered_ramps_100"
    )

    ramps__roads_near_ramp__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=ramps_file, description="roads_near_ramp"
    )

    ramps__endpoints__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=ramps_file, description="endpoints"
    )

    ramps__dissolved_ramps__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=ramps_file, description="dissolved_ramps"
    )

    ramps__intermediate_ramps__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=ramps_file, description="intermediate_ramps"
    )

    ramps__merged_ramps__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=ramps_file, description="merged_ramps"
    )

    ramps__closest_points__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=ramps_file, description="closest_points"
    )

    ramps__generalized_ramps__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=ramps_file, description="generalized_ramps"
    )

    ramps__dissolved_group__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=ramps_file, description="dissolved_group"
    )

    ramps__splitted_group__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=ramps_file, description="splitted_group"
    )

    ramps__ramp_points__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=ramps_file, description="ramp_points"
    )

    ramps__ramp_points_moved__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=ramps_file, description="ramp_points_moved"
    )

    ramps__ramp_points_moved_2__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=ramps_file, description="ramp_points_moved_2"
    )

    ramps__test__n250_road = file_manager.generate_file_name_gdb(
        script_source_name=ramps_file, description="test"
    )
