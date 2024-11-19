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

    data_selection___nvdb_roads___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="nvdb_roads",
    )

    data_selection___railroad___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="railroad",
    )

    data_selection___begrensningskurve___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="begrensningskurve",
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

    data_preparation___feature_to_line___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="feature_to_line",
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

    data_preparation___thin_road_network_selection___n100_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_preparation,
            description="thin_road_network_selection",
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

    test1___veg100_nordrefollo0___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_nordrefollo0",
    )

    test1___veg100_nordrefollo1___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_nordrefollo1",
    )

    test1___veg100_nordrefollo2___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_nordrefollo2",
    )

    test1___veg100_enebakk0___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_enebakk0",
    )

    test1___veg100_enebakk1___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_enebakk1",
    )

    test1___veg100_enebakk2___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_enebakk2",
    )

    test1___veg100_lørenskog0___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_lørenskog0",
    )

    test1___veg100_lørenskog1___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_lørenskog1",
    )

    test1___veg100_lørenskog2___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_lørenskog2",
    )

    test1___veg100_oslo0___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_oslo0",
    )

    test1___veg100_oslo1___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_oslo1",
    )

    test1___veg100_oslo2___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_oslo2",
    )

    test1___veg100_bærum0___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_bærum0",
    )

    test1___veg100_bærum1___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_bærum1",
    )

    test1___veg100_bærum2___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_bærum2",
    )

    test1___veg100_ringerike0___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_ringerike0",
    )

    test1___veg100_ringerike1___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_ringerike1",
    )

    test1___veg100_ringerike2___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=test1,
        description="veg100_ringerike2",
    )
