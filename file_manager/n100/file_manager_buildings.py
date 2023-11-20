from enum import Enum
import config

relative_path = rf"{config.output_folder}\n100\building.gdb"
scale = "n100"


def generate_file_name(function_name, description, scale):
    return rf"{relative_path}\{function_name}__{description}__{scale}"


# Function name definition:
selecting_grunnriss_for_generalization = "selecting_grunnriss_for_generalization"


class Building_N100(Enum):
    selecting_grunnriss_for_generalization__grunnriss_selection_not_church__n100 = (
        generate_file_name(
            function_name=selecting_grunnriss_for_generalization,
            description="grunnriss_selection_not_church",
            scale=scale,
        )
    )


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
    simplified_grunnriss_n100 = "simplified_grunnriss_n100"

    # create_points_from_polygon

    merged_points_final = "merged_points_final"

    reduced_hospital_church_points = "reduced_hospital_church_points"


class PermanentFiles(Enum):
    n100_building_points_undefined_nbr_values = (
        "n100_building_points_undefined_nbr_values"
    )
