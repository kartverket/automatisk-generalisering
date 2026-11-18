import arcpy

from composition_configs import logic_config
from generalization.n100.road.ramps import correct_ramp_id_after_merge_divided_roads


def merge_divided_roads_with_ramp_ids(
    merge_config: logic_config.MergeDividedRoadsKwargs,
) -> None:
    """
    What:
        Merges divided roads into single centrelines and restores the ramp ids of every
        merged input road on the merged output.

    Why:
        The ramp id correction joins the merge table, the merge input and the merge
        output by object id. Those ids are only consistent within one run of
        MergeDividedRoads, so the correction must run directly after it on the same
        data, which keeps both steps inside one partition iteration.
    """
    arcpy.cartography.MergeDividedRoads(
        in_features=merge_config.input_road_line,
        merge_field=merge_config.merge_field,
        merge_distance=f"{merge_config.merge_distance_m} Meters",
        out_features=merge_config.output_road_line,
        out_displacement_features=merge_config.output_displacement_features,
        character_field=merge_config.character_field,
        out_table=merge_config.output_merge_table,
    )

    correct_ramp_id_after_merge_divided_roads(
        merge_input=merge_config.input_road_line,
        merge_output=merge_config.output_road_line,
        merge_out_table=merge_config.output_merge_table,
    )
