# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager


# Initialize BaseFileManager
scale = global_config.scale_n100
object_name = global_config.object_veg_sti
file_manager = BaseFileManager(scale=scale, object_name=object_name)


# All scripts
data_selection = "data_selection"
data_preparation = "data_preparation"
first_generalization = "first_generalization"
test1 = "test1"
testing_file = "testing_file"
roundabout_file = "roundabout"
dam_file = "dam"
major_road_crossings = "major_road_crossings"
vegsperring_file = "vegsperring"
test2 = "test2"
test3 = "test3"


""""
# gdb
    data_selection___example___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="example",
    )
    
# csv
    data_selection___example_csv___n100_road = (
        file_manager.generate_file_name_general_files(
            script_source_name="data_selection",
            description="example_csv",
            file_type="csv",
        )
    )
# lyrx
    data_selection___example_lyrx___n100_road_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name="data_selection",
            description="example_lyrx___n100_road",
        )
    )
# final output
    Road = file_manager.generate_final_outputs(
        file_name="Road",
    )
    
# lyrx directory
    data_selection___lyrx_root___n100_road= (
        file_manager.generate_file_lyrx_directory(
            script_source_name=data_selection, description="lyrx_root"
        )
    )

"""


class Road_N100(Enum):
    # ========================================
    #                                DATA PREPARATION
    # ========================================

    data_selection___nvdb_roads___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="nvdb_roads",
    )

    data_selection___vegsperring___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="vegsperring",
    )

    data_selection___railroad___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="railroad",
    )

    data_selection___admin_boundary___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="admin_boundary",
    )

    data_selection___begrensningskurve___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="begrensningskurve",
        )
    )

    data_selection___new_road_symbology___n100_road_lyrx = (
        file_manager.generate_file_name_lyrx(
            script_source_name=data_selection,
            description="new_road_symbology",
        )
    )

    data_preparation___geometry_validation___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="geometry_validation",
        )
    )

    data_preparation___water_feature_outline___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="water_feature_outline",
        )
    )

    data_preparation___road_single_part___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="road_single_part",
        )
    )

    data_preparation___road_single_part_2___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="road_single_part_2",
        )
    )

    data_preparation___car_raod___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=data_preparation,
        description="car_raod",
    )

    data_preparation___road_dangle___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=data_preparation,
        description="road_dangle",
    )

    data_preparation___boarder_road_dangle___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="boarder_road_dangle",
        )
    )

    data_preparation___boarder_road___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=data_preparation,
        description="boarder_road",
    )

    data_preparation___on_surface_selection___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="on_surface_selection",
        )
    )

    data_preparation___bridge_selection___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="bridge_selection",
        )
    )

    data_preparation___tunnel_selection___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="tunnel_selection",
        )
    )

    data_preparation___dissolved_road_feature___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="dissolved_road_feature",
        )
    )

    data_preparation___intersections_root___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="intersections_root",
        )
    )

    data_preparation___dissolved_road_feature_2___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="dissolved_road_feature_2",
        )
    )

    data_preparation___dissolved_intersections___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="dissolved_intersections",
        )
    )

    data_preparation___country_boarder___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="country_boarder",
        )
    )

    data_preparation___country_boarder_buffer___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="country_boarder_buffer",
        )
    )

    data_preparation___roads_near_boarder___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="roads_near_boarder",
        )
    )

    data_preparation___removed_roads_near_boarder___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="removed_roads_near_boarder",
        )
    )

    data_preparation___intersections_root_2___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="intersections_root_2",
        )
    )

    data_preparation___intersections_root_3___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="intersections_root_3",
        )
    )

    data_preparation___intersections_root_4___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="intersections_root_4",
        )
    )

    data_preparation___intersections_root_5___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="intersections_root_5",
        )
    )

    data_preparation___dissolved_intersections_2___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="dissolved_intersections_2",
        )
    )

    data_preparation___dissolved_intersections_3___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="dissolved_intersections_3",
        )
    )

    data_preparation___root_calculate_boarder_hierarchy___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="root_calculate_boarder_hierarchy",
        )
    )

    data_preparation___calculated_boarder_hierarchy___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="calculated_boarder_hierarchy",
        )
    )

    data_preparation___dissolved_intersections_4___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="dissolved_intersections_4",
        )
    )

    data_preparation___dissolved_intersections_5___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="dissolved_intersections_5",
        )
    )

    data_preparation___merge_divided_roads___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="merge_divided_roads",
        )
    )

    data_preparation___merge_divided_roads_displacement_feature___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="merge_divided_roads_displacement_feature",
        )
    )

    data_preparation___divided_roads_merged_outputs___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="divided_roads_merged_outputs",
        )
    )

    data_preparation___remove_small_road_lines___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="remove_small_road_lines",
        )
    )

    data_preparation___collapse_road_detail___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="collapse_road_detail",
        )
    )

    data_preparation___road_bridge_and_tunnel_selection___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="road_bridge_and_tunnel_selection",
        )
    )

    data_preparation___road_on_surface_selection___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="road_on_surface_selection",
        )
    )
    data_preparation___on_surface_feature_to_line___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="on_surface_feature_to_line",
        )
    )

    data_preparation___simplified_road___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="simplified_road",
        )
    )

    data_preparation___thin_road_sti_root___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_sti_root",
        )
    )

    data_preparation___thin_sti_partition_root___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_sti_partition_root",
        )
    )

    thin_sti_docu___n100_road = file_manager.generate_general_subdirectory(
        description="thin_sti_docu",
    )

    data_preparation___thin_road_sti_output___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_sti_output",
        )
    )

    data_preparation___thin_road_root___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=data_preparation,
        description="thin_road_root",
    )

    data_preparation___thin_road_root_2___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_root_2",
        )
    )

    data_preparation___thin_road_root_3___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_root_3",
        )
    )

    data_preparation___thin_road_partition_root___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_partition_root",
        )
    )

    data_preparation___thin_road_partition_root_2___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_partition_root_2",
        )
    )

    data_preparation___thin_road_partition_root_3___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_partition_root_3",
        )
    )

    thin_road_docu___n100_road = file_manager.generate_general_subdirectory(
        description="thin_road_docu",
    )

    collapse_road_docu___n100_road = file_manager.generate_general_subdirectory(
        description="collapse_road_docu",
    )

    data_preparation___thin_road_docu_2___n100_road = (
        file_manager.generate_file_name_general_files(
            script_source_name=data_preparation,
            description="thin_road_docu_2",
            file_type="json",
        )
    )

    data_preparation___thin_road_docu_3___n100_road = (
        file_manager.generate_file_name_general_files(
            script_source_name=data_preparation,
            description="thin_road_docu_3",
            file_type="json",
        )
    )

    data_preparation___thin_road_output___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_output",
        )
    )

    data_preparation___thin_road_output_2___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_output_2",
        )
    )

    data_preparation___thin_road_output_3___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_output_3",
        )
    )

    data_preparation___final_merged_thin_iteration_output___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="final_merged_thin_iteration_output",
        )
    )

    data_preparation___smooth_road___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=data_preparation,
        description="smooth_road",
    )

    data_preparation___road_single_part_3___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="road_single_part_3",
        )
    )

    data_preparation___calculated_boarder_hierarchy_2___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="calculated_boarder_hierarchy_2",
        )
    )

    data_preparation___root_calculate_boarder_hierarchy_2___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="root_calculate_boarder_hierarchy_2",
        )
    )

    data_preparation___railroad_single_part___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="railroad_single_part",
        )
    )

    data_preparation___water_feature_outline_single_part___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="water_feature_outline_single_part",
        )
    )

    data_preparation___resolve_road_conflicts___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="resolve_road_conflicts",
        )
    )

    data_preparation___road_final_output___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="road_final_output",
        )
    )

    data_preparation___resolve_road_partition_root___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="resolve_road_partition_root",
        )
    )

    resolve_road_docu___n100_road = file_manager.generate_general_subdirectory(
        description="resolve_road_docu",
    )

    data_preparation___resolve_road_root___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="resolve_road_root",
        )
    )

    data_preparation___resolve_road_conflicts_displacement_feature___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="resolve_road_conflicts_displacement_feature",
        )
    )

    data_preperation___paths_n50___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=data_preparation,
        description="paths_n50",
    )

    data_preperation___selecting_vegtrase_and_kjorebane_nvdb___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="selecting_vegtrase_and_kjorebane_nvdb",
        )
    )

    data_preperation___selecting_everything_but_rampe_nvdb___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="selecting_everything_but_rampe_nvdb",
        )
    )

    data_preperation___selecting_everything_but_rampe_with_calculated_fields_nvdb___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=data_preparation,
        description="selecting_everything_but_rampe_with_calculated_fields_nvdb",
    )

    # ========================================
    #                                FIRST GENERALIZATION
    # ========================================

    first_generalization___paths_in_study_area___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="paths_in_study_area",
        )
    )
    first_generalization____nvdb_roads_in_study_area___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="nvdb_roads_in_study_area",
        )
    )

    first_generalization____merged_roads_and_paths___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="merged_roads_and_paths",
        )
    )

    first_generalization____multipart_to_singlepart___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="multipart_to_singlepart",
        )
    )

    first_generalization____merge_divided_roads_features___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="merge_divided_roads_features",
        )
    )

    first_generalization____merge_divided_roads_displacement_feature___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="merge_divided_roads_displacement_feature",
        )
    )

    first_generalization____visible_features_after_thin_road_network_1___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="visible_features_after_thin_road_network_1",
        )
    )

    first_generalization____collapse_road_detail___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="collapse_road_detail",
        )
    )

    first_generalization____visible_features_after_thin_road_network_2___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="visible_features_after_thin_road_network_2",
        )
    )

    data_preperation___paths_n50_with_calculated_fields___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="paths_n50_with_calculated_fields",
        )
    )

    first_generalization____visible_features_after_thin_road_network_3___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="visible_features_after_thin_road_network_3",
        )
    )

    data_preperation___going_into_spatial_join___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="going_into_spatial_join",
        )
    )

    data_preperation___functional_road_class_dataset___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="functional_road_class_dataset",
        )
    )

    data_preperation___spatial_join_completed___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="spatial_join_completed",
        )
    )

    first_generalization____visible_features_after_thin_road_network_4___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="visible_features_after_thin_road_network_4",
        )
    )

    first_generalization____selecting_rundkjoring___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="selecting_rundkjoring",
        )
    )

    first_generalization____polygon_created_from_line___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="polygon_created_from_line",
        )
    )

    first_generalization____polygon_feature_class___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="polygon_feature_class",
        )
    )

    first_generalization____selecting_all_road_parts_except_rundkjoring___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="selecting_all_road_parts_except_rundkjoring",
        )
    )

    first_generalization____dissolving_rundkjoring___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="dissolving_rundkjoring",
        )
    )

    first_generalization____feature_to_point___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="feature_to_point",
        )
    )

    first_generalization____roads_going_into_extend_line___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="roads_going_into_extend_line",
        )
    )

    first_generalization____roads_after_snap___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="roads_after_snap",
        )
    )

    first_generalization____rundkjoring_buffer___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="rundkjoring_buffer",
        )
    )

    first_generalization____rundkjoring_buffer_multipart_to_singlepart___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=first_generalization,
            description="rundkjoring_buffer_multipart_to_singlepart",
        )
    )
    # ========================================
    #                                TEST1
    # ========================================

    test1___kommune___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="kommune",
    )

    test1___kommune_buffer___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="kommune_buffer",
    )

    test1___elveg_and_sti_kommune___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="elveg_and_sti_kommune",
    )

    test1___elveg_and_sti_kommune_singlepart___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=test1,
            description="elveg_and_sti_kommune_singlepart",
        )
    )

    test1___rsl___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="rsl",
    )

    test1___rsl_mdr_crd60___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="rsl_mdr_crd60",
    )

    test1___rsl_crd60___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="rsl_crd60",
    )

    test1___diss0___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="diss0",
    )

    test1___medium_ul0___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="medium_ul0",
    )

    test1___medium_t0___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="medium_t0",
    )

    test1___kryss0___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="kryss0",
    )

    test1___diss1___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="diss1",
    )

    test1___medium_ul1___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="medium_ul1",
    )
    test1___medium_t1___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="medium_t1",
    )
    test1___kryss1___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="kryss1",
    )

    test1___simplified___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="simplified",
    )
    test1___integrate___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="integrate",
    )

    test1___thin1___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="thin1",
    )

    test1___thin2___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="thin2",
    )

    test1___thin3___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="thin3",
    )

    test1___thin4___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="thin4",
    )

    test1___thin5___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="thin5",
    )

    test1___thin6___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="thin6",
    )

    test1___thin7___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="thin7",
    )

    test1___thin8___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="thin8",
    )

    test1___thin9___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="thin9",
    )

    test1___thin10___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="thin10",
    )

    test1___mdr0___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="mdr0",
    )
    test1___mdr___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="mdr",
    )
    test1___mdr2___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="mdr2",
    )
    test1___mdr3___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="mdr3",
    )
    test1___sm300___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="sm300",
    )

    test1___dissx___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="dissx",
    )

    test1___veg100_Kristiansand_modell3___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=test1,
            description="veg100_Kristiansand_modell3",
        )
    )

    # ========================================
    #                                TESTING FILE
    # ========================================

    testing_file___roads_copy___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=testing_file,
        description="roads_copy",
    )

    testing_file___graph_root___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=testing_file,
        description="graph_root",
    )

    testing_file___remove_triangles_root___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="remove_triangles_root",
        )
    )

    testing_file___removed_triangles___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=testing_file,
        description="removed_triangles",
    )

    testing_file___multipart_to_singlepart___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="multipart_to_singlepart",
        )
    )

    testing_file___merge_divided_roads_displacement_feature___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="merge_divided_roads_displacement_feature",
        )
    )

    testing_file___merge_divided_roads_output___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="merge_divided_roads_output",
        )
    )

    testing_file___thin_road_network_3000_1___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="thin_road_network_3000_1",
        )
    )

    testing_file___thin_road_network_2___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="thin_road_network_2",
        )
    )

    testing_file___thin_road_network_2_visible_features___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="thin_road_network_2_visible_features",
        )
    )

    testing_file___road_input_500_straight_to_3000___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="road_input_500_straight_to_3000",
        )
    )

    testing_file___thin_road_network_3___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="thin_road_network_3",
        )
    )

    testing_file___thin_road_network_3_visible_features___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="thin_road_network_3_visible_features",
        )
    )

    testing_file___thin_road_network_4___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="thin_road_network_4",
        )
    )

    testing_file___thin_road_network_500_visible_features___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="thin_road_network_500_visible_features",
        )
    )

    testing_file___road_input_500_1000_2000_3000___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="road_input_500_1000_2000_3000",
        )
    )

    testing_file___thin_road_network_1000___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="thin_road_network_1000",
        )
    )

    testing_file___thin_road_network_2000___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="thin_road_network_2000",
        )
    )

    testing_file___thin_road_network_3000_2___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="thin_road_network_3000_2",
        )
    )

    testing_file___thinning_kommunal_veg___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="thinning_kommunal_veg",
        )
    )

    testing_file___thinning_kommunal_veg_visible_roads___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="thinning_kommunal_veg_visible_roads",
        )
    )

    testing_file___thinning_all_roads_a_lot___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="thinning_all_roads_a_lot",
        )
    )

    testing_file___thinning_all_roads_a_lot_visible_features___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="thinning_all_roads_a_lot_visible_features",
        )
    )

    testing_file___roads_without_rundkjoring___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="roads_without_rundkjoring",
        )
    )

    testing_file___thinning_kommunal_veg_visible_roads_copy___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="thinning_kommunal_veg_visible_roads_copy",
        )
    )

    testing_file___collapse_road_detail___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="collapse_road_detail",
        )
    )

    testing_file___begrensningskurve_vann___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="begrensningskurve_vann",
        )
    )

    testing_file___displacement_feature_after_resolve_road_conflict___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="displacement_feature_after_resolve_road_conflict",
        )
    )

    test1___root_file___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="root_file",
    )

    testing_file___begrensningskurve_water_area___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="begrensningskurve_water_area",
        )
    )

    testing_file___railway_area___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=testing_file,
        description="railway_area",
    )

    testing_file___roads_area___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=testing_file,
        description="roads_area",
    )

    testing_file___begrensningskurve_water_area_lyrx___n100_road = (
        file_manager.generate_file_name_lyrx(
            script_source_name=testing_file,
            description="begrensningskurve_water_area_lyrx",
        )
    )

    testing_file___railway_area_lyrx___n100_road = file_manager.generate_file_name_lyrx(
        script_source_name=testing_file,
        description="railway_area_lyrx",
    )

    testing_file___roads_area_lyrx___n100_road = file_manager.generate_file_name_lyrx(
        script_source_name=testing_file,
        description="roads_area_lyrx",
    )

    testing_file___resolve_road_conflict_output___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="resolve_road_conflict_output",
        )
    )

    testing_file___begrensningskurve_water_area_copy___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="begrensningskurve_water_area_copy",
        )
    )

    testing_file___railway_area_copy___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=testing_file,
        description="railway_area_copy",
    )

    testing_file___roads_area_copy___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=testing_file,
        description="roads_area_copy",
    )

    testing_file___dissolve_roads___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=testing_file,
        description="dissolve_roads",
    )

    testing_file____begrensningskurve_water_area_multipart_to_singlepart___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="begrensningskurve_water_area_multipart_to_singlepart",
        )
    )

    testing_file___railway_area_multipart_to_singlepart___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="railway_area_multipart_to_singlepart",
        )
    )

    testing_file___roads_area_multipart_to_singlepart___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="roads_area_multipart_to_singlepart",
        )
    )

    testing_file___road_input_functional_roadclass___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="road_input_functional_roadclass",
        )
    )

    testing_file___visible_functional_roadclass___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="visible_functional_roadclass",
        )
    )

    testing_file___road_input_functional_roadclass_studyarea_selector___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=testing_file,
            description="road_input_functional_roadclass_studyarea_selector",
        )
    )

    # ========================================
    #                               ROUNDABOUT
    # ========================================

    roundabout__roundabout__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=roundabout_file, description="roundabout"
    )

    roundabout__centroids__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=roundabout_file, description="centroids"
    )

    roundabout__cleaned_road__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=roundabout_file, description="cleaned_road"
    )

    # ========================================
    #                                      DAM
    # ========================================

    dam__relevant_roads__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="relevant_roads"
    )

    dam__relevant_dam__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="relevant_dam"
    )

    dam__relevant_water__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="relevant_water"
    )

    dam__dam_buffer_35m__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="dam_buffer_35m"
    )

    dam__roads_inside_with_data__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="roads_inside_with_data"
    )

    dam__roads_outside__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="roads_outside"
    )

    dam__water_clipped__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="water_clipped"
    )

    dam__water_center__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="water_center"
    )

    dam__buffer_water__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="buffer_water"
    )

    dam__water_singleparts__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="water_singleparts"
    )

    dam__dam_buffer_sti__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="dam_buffer_sti"
    )

    dam__roads_clipped_sti__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="roads_clipped_sti"
    )

    dam__roads_moved__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="roads_moved"
    )

    dam__roads_shifted__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="roads_shifted"
    )

    dam__dam_buffer_150m__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="dam_buffer_150m"
    )

    dam__dam_buffer_60m_flat__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="dam_buffer_60m_flat"
    )

    dam__dam_buffer_5m_flat__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="dam_buffer_5m_flat"
    )

    dam__dam_buffer_60m__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="dam_buffer_60m"
    )

    dam__water_buffer_55m__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="water_buffer_55m"
    )

    dam__dam_buffer_60m_line__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="dam_buffer_60m_line"
    )

    dam__roads_intermediate__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="roads_intermediate"
    )

    dam__paths_in_dam__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="paths_in_dam"
    )

    dam__paths_in_dam_valid__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="paths_in_dam_valid"
    )

    dam__cleaned_roads__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=dam_file, description="cleaned_roads"
    )

    # ========================================
    #                     MAJOR ROAD CROSSINGS
    # ========================================

    major_road_crossing__road_u__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="road_u"
    )

    major_road_crossing__road_u_buffer__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="road_u_buffer"
    )

    major_road_crossing__road_u_buffer_shrunked__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="road_u_buffer_shrunked"
    )

    major_road_crossing__road_l__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="road_l"
    )

    major_road_crossing__road_l_buffer__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="road_l_buffer"
    )

    major_road_crossing__road_l_buffer_shrunked__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="road_l_buffer_shrunked"
    )

    major_road_crossing__ER__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="ER"
    )

    major_road_crossing__ER_bridge__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="ER_bridge"
    )

    major_road_crossing__ER_bridge_buffer__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="ER_bridge_buffer"
    )

    major_road_crossing__ER_bridge_shrunked__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="ER_bridge_shrunked"
    )

    major_road_crossing__road_t__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="road_t"
    )

    major_road_crossing__ER_t__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="ER_t"
    )

    major_road_crossing__bridge_cross_ER__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="bridge_cross_ER"
    )

    major_road_crossing__underpass_cross_ER__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="underpass_cross_ER"
    )

    major_road_crossing__surface_under_ER__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="surface_under_ER"
    )

    major_road_crossing__keep_bru_ERFKP__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="keep_bru_ERFKP"
    )

    major_road_crossing__keep_underpass_ERFKP__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="keep_underpass_ERFKP"
    )

    major_road_crossing__keep_surface_ERFKP__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="keep_surface_FKP"
    )

    major_road_crossing__merged_keep__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="merged_keep"
    )

    major_road_crossing__output__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=major_road_crossings, description="output"
    )

    # ========================================
    #                              VEGSPERRING
    # ========================================

    vegsperring__veg_uten_bom__n100_road = file_manager.generate_file_name_gdb(
        script_source_name=vegsperring_file, description="veg_uten_bom"
    )

    # ========================================
    #                                TEST2
    # ========================================

    test2___veg_u___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="veg_u",
    )

    test2___veg_u_poly100___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="veg_u_poly100",
    )

    test2___veg_u_poly100_shrunked___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="veg_u_poly100_shrunked",
    )

    test2___veg_l___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="veg_l",
    )
    test2___veg_l_poly100___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="veg_l_poly100",
    )

    test2___veg_l_poly100_shrunked___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="veg_l_poly100_shrunked",
    )

    test2___veg_t___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="veg_t",
    )
    test2___vegsenterlinje_t_buff100___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="vegsenterlinje_t_buff100",
    )

    test2___shrunk_surface_road___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="shrunk_surface_road",
    )

    test2___ER___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="ER",
    )

    test2___ER_bridge___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="ER_bridge",
    )

    test2___ER_bridge_poly100___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="ER_bridge_poly100",
    )

    test2___ER_bridge_shrunked___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="ER_bridge_shrunked",
    )

    test2___ER_t___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="ER_t",
    )

    test2___bridge_cross_ER___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="bridge_cross_ER",
    )

    test2___underpass_cross_ER___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="underpass_cross_ER",
    )
    test2___surface_under_ER___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="surface_under_ER",
    )

    test2___keep_bru_ERFKP___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="keep_bru_ERFKP",
    )

    test2___keep_underpass_ERFKP___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="keep_underpass_ERFKP",
    )

    test2___keep_surface_FKP___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="keep_surface_FKP",
    )

    test2___keep_surface_ERFKP___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="keep_surface_ERFKP",
    )

    test2___merged_keep___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="merged_keep",
    )

    test2___rampe___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="rampe",
    )

    test2___rampe_poly___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="rampe_poly",
    )

    test2___rampe_poly_diss___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="rampe_poly_diss",
    )

    test2___rampe_poly_epp___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test2,
        description="rampe_poly_diss_epp",
    )
    # ========================================
    #                                test3
    # ========================================

    test3___rampe_poly___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test3,
        description="rampe_poly",
    )

    test3___rampe_poly_diss___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test3,
        description="rampe_poly_diss",
    )

    test3___rampe_epp___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test3,
        description="rampe_epp",
    )

    test3___veg_unsplit___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test3,
        description="veg_unsplit",
    )

    test3___kryss___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test3,
        description="kryss",
    )
    test3___kryss_symbol___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test3,
        description="kryss_symbol",
    )
