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
            description="visible_features_after_thin_road_network_1_test",
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
            description="visible_features_after_thin_road_network_2_test",
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
            description="visible_features_after_thin_road_network_3_test",
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

    test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=test1,
            description="elveg_and_sti_kommune_singlepart_dissolve",
        )
    )

    test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=test1,
            description="elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads",
        )
    )

    test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd",
    )

    test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_medium_ul___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_medium_ul",
    )

    test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_medium_t___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_medium_t",
    )

    test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss",
    )

    test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_thin_sti___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_thin_sti",
    )

    test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke",
    )

    test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke_thinveg2___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke_thinveg2",
    )

    test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke_thin3vegklasse___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke_thin3vegklasse",
    )

    test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke_thin4vegklasse___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke_thin4vegklasse",
    )

    test1___veg100_bærum___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_bærum",
    )

    test1___veg100_hole___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_hole",
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

    test1___veg100_ringerike___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_ringerike",
    )
