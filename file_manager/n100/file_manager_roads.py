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

    test1___komm___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="komm",
    )

    test1___komm_buff___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="komm_buff",
    )

    test1___roads_komm___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="roads_komm",
    )

    test1___roads_komm_single___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="roads_komm_single",
    )

    test1___roads_komm_diss___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="roads_komm_diss",
    )

    test1___diss_T___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="diss_T",
    )

    test1___kryss_T___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="kryss_T",
    )

    test1___diss_UL___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="diss_UL",
    )

    test1___merge0___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="merge0",
    )

    test1___roads_komm_merge1___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="roads_komm_merge1",
    )

    test1___komm_sti_thin1___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="komm_sti_thin1",
    )

    test1___komm_bilveg___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="komm_bilveg",
    )

    test1___komm_thin2___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="komm_thin2",
    )

    test1___komm_thin3___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="komm_thin3",
    )

    test1___komm_crd1___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="komm_crd1",
    )

    test1___veg100_bærum___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_bærum",
    )
    test1___veg100_asker___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_asker",
    )

    test1___veg100_lier___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_lier",
    )

    test1___veg100_drammen___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_drammen",
    )

    test1___veg100_oslo___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_oslo",
    )

    test1___veg1___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg1",
    )
    test1___veg1_bil___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg1_bil",
    )
    test1___veg1_sti___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg1_sti",
    )

    test1___sti2___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="sti2",
    )

    test1___veg2_bil___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg2_bil",
    )

    test1___veg3_diss___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg3_diss",
    )

    test1___veg4___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg4",
    )

    test1___CDR0___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="CDR0",
    )

    test1___CDR1___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="CDR1",
    )

    test1___veg5___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg5",
    )

    test1___MDR1_bilnum___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="MDR1_bilnum",
    )

    test1___MDR2_bilnum___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="MDR2_bilnum",
    )

    test1___MDR3_bilmed___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="MDR3_bilmed",
    )
