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


    # create_simplified_building_polygons

    output_aggregate_polygon = "aggregated_polygon"

    output_collapsed_points_simplified_building = (
        "simplified_building_points_simplified_building"
    )
    output_collapsed_points_simplified_building2 = (
        "simplified_building_points_simplified_building2"
    )
    output_collapsed_points_simplified_polygon = (
        "simplified_building_points_simplified_polygon"
    )
    simplified_grunnriss_n50 = "simplified_grunnriss_n50"

    # create_points_from_polygon

    merged_points_final ="merged_points_final"

class PermanentFiles(Enum):
    n100_building_points_undefined_nbr_values = (
        "n100_building_points_undefined_nbr_values"
    )
