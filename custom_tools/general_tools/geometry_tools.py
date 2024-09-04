import arcpy
from typing import Union, Dict

from xarray.backends.common import NONE_VAR_NAME

from custom_tools.general_tools import custom_arcpy
from custom_tools.decorators.partition_io_decorator import partition_io_decorator
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


class GeometryValidator:
    def __init__(
        self,
        input_features: Union[Dict[str, str], str],
        output_table_path: str,
    ):
        self.input_features = input_features
        self.output_table_path = output_table_path
        self.generated_out_table_path = None
        self.problematic_features = {}
        self.non_problematic_features = {}
        self.iteration = 0

    def check_geometry(self):
        """Check the geometry of the input features."""
        self.problematic_features.clear()

        if isinstance(self.input_features, dict):
            for alias, path in self.input_features.items():
                # Skip if this feature was previously validated as non-problematic
                if alias in self.non_problematic_features:
                    continue

                self.generated_out_table_path = (
                    f"{self.output_table_path}_{alias}_validation_{self.iteration}"
                )
                result = arcpy.management.CheckGeometry(
                    in_features=path, out_table=self.generated_out_table_path
                )
                problems_found = result[1] == "true"
                if problems_found:
                    self.problematic_features[alias] = path
                    print(f"Geometry issues found in feature: {alias}")
                else:
                    self.non_problematic_features[alias] = path
                    print(f"No geometry issues found in feature: {alias}")
        elif isinstance(self.input_features, str):
            if self.input_features in self.non_problematic_features:
                print(
                    f"Feature {self.input_features} previously validated as non-problematic, skipping."
                )
                return

            self.generated_out_table_path = (
                f"{self.output_table_path}_iter{self.iteration}"
            )
            result = arcpy.management.CheckGeometry(
                in_features=self.input_features, out_table=self.generated_out_table_path
            )
            problems_found = result[1] == "true"
            if problems_found:
                self.problematic_features[self.input_features] = self.input_features
                print(f"Geometry issues found in feature: {self.input_features}")
            else:
                self.non_problematic_features[self.input_features] = self.input_features
                print(f"No geometry issues found in feature: {self.input_features}")
        else:
            raise TypeError("input_features must be either a dictionary or a string.")

    def repair_geometry(self, delete_null="DELETE_NULL", validation_method="ESRI"):
        """Repair the geometry of the features identified with issues."""
        if not self.problematic_features:
            print("No problematic features to repair.")
            return

        for alias, path in self.problematic_features.items():
            arcpy.management.RepairGeometry(
                in_features=path,
                delete_null=delete_null,
                validation_method=validation_method,
            )
            print(f"Repaired geometry for feature: {alias}")

    @partition_io_decorator(
        input_param_names=["input_features"],
        output_param_names=None,
    )
    def check_repair_sequence(self, max_iterations=2):
        """Run the check-repair-check sequence until no issues remain or max iterations reached."""
        self.iteration = 0
        while self.iteration < max_iterations:
            print(f"--- Iteration {self.iteration + 1} ---")
            self.check_geometry()
            if not self.problematic_features:
                print("No further geometry issues detected.")
                break
            self.repair_geometry()
            self.iteration += 1

        if self.iteration == max_iterations:
            problematic_aliases = ", ".join(self.problematic_features.keys())
            print(
                f"Maximum iterations ({max_iterations}) reached. Manual inspection may be required for the following features: {problematic_aliases}"
            )
