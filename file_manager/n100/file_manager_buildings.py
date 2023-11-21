from enum import Enum
import config
from env_setup import setup_directory_structure

scale = setup_directory_structure.scale_n100
object = setup_directory_structure.object_bygning


relative_path = (
    rf"{config.output_folder}\automatic_generalization_outputs\{scale}\{object}.gdb"
)


def generate_file_name(function_name, description, scale):
    return rf"{relative_path}\{function_name}__{description}__{scale}"


# Function name definition:
preparation_begrensningskurve = "preparation_begrensningskurve"
preperation_veg_sti = "preperation_veg_sti"
adding_matrikkel_as_points = "adding_matrikkel_as_points"
selecting_grunnriss_for_generalization = "selecting_grunnriss_for_generalization"


class Building_N100(Enum):
    preparation_begrensningskurve__selected_waterfeatures_from_begrensningskurve__n100 = generate_file_name(
        function_name=preparation_begrensningskurve,
        description="selected_waterfeatures_from_begrensningskurve",
        scale=scale,
    )

    preparation_begrensningskurve__begrensningskurve_buffer_waterfeatures__n100 = (
        generate_file_name(
            function_name=preparation_begrensningskurve,
            description="begrensningskurve_buffer_waterfeatures",
            scale=scale,
        )
    )

    preperation_veg_sti__unsplit_veg_sti__n100 = generate_file_name(
        function_name=preperation_veg_sti,
        description="unsplit_veg_sti",
        scale=scale,
    )

    adding_matrikkel_as_points__urban_area_selection_n100__n100 = generate_file_name(
        function_name=adding_matrikkel_as_points,
        description="urban_area_selection_n100",
        scale=scale,
    )

    adding_matrikkel_as_points__urban_area_selection_n50__n100 = generate_file_name(
        function_name=adding_matrikkel_as_points,
        description="urban_area_selection_n50",
        scale=scale,
    )

    adding_matrikkel_as_points__urban_area_selection_n100_buffer__n100 = (
        generate_file_name(
            function_name=adding_matrikkel_as_points,
            description="urban_area_selection_n100_buffer",
            scale=scale,
        )
    )

    adding_matrikkel_as_points__no_longer_urban_areas__n100 = generate_file_name(
        function_name=adding_matrikkel_as_points,
        description="no_longer_urban_areas",
        scale=scale,
    )

    adding_matrikkel_as_points__matrikkel_bygningspunkt__n100 = generate_file_name(
        function_name=adding_matrikkel_as_points,
        description="matrikkel_bygningspunkt",
        scale=scale,
    )

    selecting_grunnriss_for_generalization__selected_grunnriss_not_church__n100 = (
        generate_file_name(
            function_name=selecting_grunnriss_for_generalization,
            description="selected_grunnriss_not_church",
            scale=scale,
        )
    )

    selecting_grunnriss_for_generalization__large_enough_grunnriss__n100 = (
        generate_file_name(
            function_name=selecting_grunnriss_for_generalization,
            description="large_enough_grunnriss",
            scale=scale,
        )
    )

    selecting_grunnriss_for_generalization__too_small_grunnriss__n100 = (
        generate_file_name(
            function_name=selecting_grunnriss_for_generalization,
            description="too_small_grunnriss",
            scale=scale,
        )
    )

    selecting_grunnriss_for_generalization__points_created_from_small_grunnriss__n100 = generate_file_name(
        function_name=selecting_grunnriss_for_generalization,
        description="points_created_from_small_grunnriss",
        scale=scale,
    )

    selecting_grunnriss_for_generalization__grunnriss_kirke__n100 = generate_file_name(
        function_name=selecting_grunnriss_for_generalization,
        description="grunnriss_kirke",
        scale=scale,
    )

    selecting_grunnriss_for_generalization__kirke_points_created_from_grunnriss__n100 = generate_file_name(
        function_name=selecting_grunnriss_for_generalization,
        description="kirke_points_created_from_grunnriss",
        scale=scale,
    )

    bygningspunkt_pre_symbology = "bygningspunkt_pre_symbology"

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
