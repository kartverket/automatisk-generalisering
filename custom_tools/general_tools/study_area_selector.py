import arcpy

from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.create_partition_features import (
    HALO_FIELD,
    PARTITION_INDEX_FIELD,
)


class StudyAreaSelector:
    def __init__(
        self,
        input_output_file_dict: dict,
        selecting_file: str,
        select_local: bool = False,
        selecting_sql_expression: str = None,
        partition_feature: str | None = None,
        partition_index: int | None = None,
        halo_m: int | None = None,
    ):
        self.input_output_file_dict = input_output_file_dict
        self.selecting_file = selecting_file
        self.selecting_sql_expression = selecting_sql_expression
        self.select_local = select_local
        self.partition_feature = partition_feature
        self.partition_index = partition_index
        self.halo_m = halo_m

        self.selecting_feature = None
        self.working_files_list = []

    def select_study_area(self):
        self.selecting_feature = f"{self.selecting_file}_selection"
        self.working_files_list.append(self.selecting_feature)

        custom_arcpy.select_attribute_and_make_feature_layer(
            input_layer=self.selecting_file,
            expression=self.selecting_sql_expression,
            output_name=self.selecting_feature,
        )

        for input_file, output_file in self.input_output_file_dict.items():
            custom_arcpy.select_location_and_make_permanent_feature(
                input_layer=input_file,
                overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
                select_features=self.selecting_feature,
                output_name=output_file,
            )

    def select_partition(self):
        """
        What:
            Selects the inputs within halo_m of the partition with partition_index
            in the fan-out partition feature.

        Why:
            Uses arcpy directly rather than the custom_arcpy helpers, which swallow
            errors. A pod that silently selects nothing would produce an empty
            partition instead of failing.
        """
        if not arcpy.Exists(self.partition_feature):
            raise FileNotFoundError(
                f"Partition feature not found: {self.partition_feature}"
            )

        partition_count = int(arcpy.management.GetCount(self.partition_feature)[0])
        if not 0 <= self.partition_index < partition_count:
            raise ValueError(
                f"Partition index {self.partition_index} is out of range: "
                f"{self.partition_feature} has partitions 0 to {partition_count - 1}"
            )

        partition_layer = "study_area_partition_layer"
        self.working_files_list.append(partition_layer)
        arcpy.management.MakeFeatureLayer(
            in_features=self.partition_feature,
            out_layer=partition_layer,
            where_clause=f"{PARTITION_INDEX_FIELD} = {self.partition_index}",
        )
        if int(arcpy.management.GetCount(partition_layer)[0]) != 1:
            raise ValueError(
                f"Expected exactly one partition with {PARTITION_INDEX_FIELD} = "
                f"{self.partition_index} in {self.partition_feature}"
            )
        with arcpy.da.SearchCursor(partition_layer, [HALO_FIELD]) as cursor:
            (feature_halo_m,) = next(cursor)
        if feature_halo_m != self.halo_m:
            raise ValueError(
                f"{self.partition_feature} was created with {HALO_FIELD} = "
                f"{feature_halo_m}, but this run uses {self.halo_m}"
            )

        for i, (input_file, output_file) in enumerate(
            self.input_output_file_dict.items()
        ):
            input_layer = f"study_area_partition_input_{i}"
            self.working_files_list.append(input_layer)
            arcpy.management.MakeFeatureLayer(
                in_features=input_file, out_layer=input_layer
            )
            arcpy.management.SelectLayerByLocation(
                in_layer=input_layer,
                overlap_type="WITHIN_A_DISTANCE",
                select_features=partition_layer,
                search_distance=f"{self.halo_m} Meters",
                selection_type="NEW_SELECTION",
            )
            arcpy.management.CopyFeatures(
                in_features=input_layer, out_feature_class=output_file
            )
            print(f"Selected partition {self.partition_index} into {output_file}")

    def use_global_files(self):
        for input_file, output_file in self.input_output_file_dict.items():
            arcpy.management.CopyFeatures(
                in_features=input_file,
                out_feature_class=output_file,
            )
            print(f"Copied {output_file}")

    def delete_working_files(self, *file_paths):
        """
        Deletes multiple feature classes or files.
        """
        for file_path in file_paths:
            self.delete_feature_class(file_path)
            print(f"Deleted file: {file_path}")

    def delete_feature_class(self, feature_class_path):
        """
        Deletes a feature class if it exists.
        """
        if arcpy.Exists(feature_class_path):
            arcpy.management.Delete(feature_class_path)

    def run(self):
        if self.partition_feature is not None:
            self.select_partition()
        elif self.select_local:
            self.select_study_area()
        else:
            self.use_global_files()
        self.delete_working_files(*self.working_files_list)
