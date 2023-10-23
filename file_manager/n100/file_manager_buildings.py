from enum import Enum


class TemporaryFiles(Enum):
    begrensningskurve_buffer_waterfeatures = (
        "begrensningskurve_waterfeatures_20m_buffer"
    )
    unsplit_veg_sti_n100 = "unsplit_veg_sti_n100"
    matrikkel_bygningspunkt = "matrikkel_bygningspunkt"
    grunnriss_selection_n50 = "grunnriss_selection_n50"
    kirke_sykehus_points_n50 = "kirke_sykehus_points_n50"
    bygningspunkt_pre_symbology = "bygningspunkt_pre_symbology"
    small_grunnriss_points_n50 = "small_grunnriss_points_n50"
    output_collapsed_points_simplified_building = (
        "simplified_building_points_simplified_building"
    )
    output_collapsed_points_simplified_building2 = (
        "simplified_building_points_simplified_building2"
    )
    output_collapsed_points_simplified_polygon = (
        "simplified_building_points_simplified_polygon"
    )

    output_aggregate_polygon = "aggregated_polygon"

    select_location_make_feature_layer_aggregated_polygon = "aggregated_polygon_select_by_location_grunnriss"

    feature_to_point = "feature_to_point"

    merged = "merged_features" 

    final_merge ="final_merge"


class PermanentFiles(Enum):
    n100_building_points_undefined_nbr_values = (
        "n100_building_points_undefined_nbr_values"
    )
