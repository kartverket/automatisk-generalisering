import arcpy
from typing import Union

from input_data import input_n50
from input_data import input_n100
from input_data import input_other

from env_setup import environment_setup
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values
from file_manager.n100.file_manager_buildings import Building_N100
from custom_tools.general_tools import custom_arcpy
from custom_tools.decorators.partition_io_decorator import partition_io_decorator


class StudyAreaSelector:
    def __init__(
        self,
        input_output_file_dict: dict,
        selecting_file: str,
        select_local: bool = False,
        selecting_sql_expression: str = None,
    ):
        self.input_output_file_dict = input_output_file_dict
        self.selecting_file = selecting_file
        self.selecting_sql_expression = selecting_sql_expression
        self.select_local = select_local

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

    def use_global_files(self):
        for input_file, output_file in self.input_output_file_dict.items():
            arcpy.management.CopyFeatures(
                in_features=input_file,
                out_feature_class=output_file,
            )

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
        if self.select_local:
            self.select_study_area()
        else:
            self.use_global_files()
        self.delete_working_files(*self.working_files_list)


if __name__ == "__main__":
    environment_setup.main()

    input_output_file_dict = {
        input_n100.JernbaneStasjon: f"{Building_N100.data_preparation___railway_station_points_from_n100___n100_building.value}_test",
        input_n100.Bane: f"{Building_N100.data_preparation___railway_station_points_from_n100___n100_building.value}_test2",
    }

    selector = StudyAreaSelector(
        input_output_file_dict=input_output_file_dict,
        selecting_file=input_n100.AdminFlate,
        selecting_sql_expression="navn IN ('Asker', 'Oslo', 'Trondheim', 'Ringerike')",
        select_local=False,
    )

    selector.run()
