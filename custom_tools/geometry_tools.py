import arcpy
from env_setup import environment_setup
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_rivers import River_N100


class RemovePolygonIslands:
    def __init__(self, input_feature_class):
        self.input_feature_class = input_feature_class
        self.output_feature_class = f"{input_feature_class}_clean"

    def remove_islands(self):
        custom_arcpy.remove_islands(self.input_feature_class, self.output_feature_class)


def remove_polygon_islands(output_feature_class):
    input_feature_class = (
        River_N100.centerline_pruning_loop__water_features_processed__n100.value
    )

    dissolve_output = f"{input_feature_class}_dissolved"
    arcpy.analysis.PairwiseDissolve(
        in_features=input_feature_class,
        out_feature_class=dissolve_output,
        dissolve_field=["shape_Length", "shape_Area"],
        multi_part="MULTI_PART",
    )

    eliminate_polygon_part_output = f"{output_feature_class}_eliminate_polygon_part"

    arcpy.management.EliminatePolygonPart(
        in_features=dissolve_output,
        out_feature_class=eliminate_polygon_part_output,
        condition="PERCENT",
        part_area_percent="99",
        part_option="CONTAINED_ONLY",
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=eliminate_polygon_part_output,
        overlap_type=custom_arcpy.OverlapType.HAVE_THEIR_CENTER_IN.value,
        select_features=River_N100.centerline_pruning_loop__complex_water_features__n100.value,
        output_name=River_N100.centerline_pruning_loop__complex_centerlines__n100.value,
    )
