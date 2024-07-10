import arcpy


from input_data import input_n100

# Importing custom modules
from file_manager.n100.file_manager_buildings import Building_N100
from env_setup import environment_setup
from custom_tools.decorators.partition_io_decorator import partition_io_decorator
from custom_tools.general_tools import custom_arcpy
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values


class BegrensningskurveLandWaterbodies:
    def __init__(
        self,
        input_begrensningskurve: str,
        input_land_features: str,
        water_feature_buffer_width: int,
        output_begrensningskurve: str,
        water_barrier_buffer_width: int = 30,
        write_work_files_to_memory: bool = True,
        keep_work_files: bool = False,
        root_file: str = None,
    ):
        self.input_begrensningskurve = input_begrensningskurve
        self.input_land_features = input_land_features
        self.output_begrensningskurve = output_begrensningskurve

        self.write_work_files_to_memory = write_work_files_to_memory
        self.keep_work_files = keep_work_files
        self.root_file = root_file

        # How far out from land water buffer is created
        self.water_feature_buffer_width = water_feature_buffer_width

        # How wide the water feature buffer will be
        self.water_barrier_buffer_width = water_barrier_buffer_width

        self.waterfeatures_from_begrensningskurve_not_rivers = None
        self.land_features_area = None
        self.selected_land_features = None
        self.land_features_buffer = None
        self.begrensningskurve_waterfeatures_buffer = None
        self.erase_feature_1 = None

        self.working_files_list = []

    def reset_temp_files(self):
        """Reset temporary file attributes."""
        unique_id = id(self)
        temporary_file = "in_memory\\"
        permanent_file = f"{self.root_file}_"
        if self.root_file is None:
            if not self.write_work_files_to_memory:
                raise ValueError(
                    "Need to specify root_file path to write to disk for work files."
                )
            if self.keep_work_files:
                raise ValueError(
                    "Need to specify root_file path and write to disk to keep_work_files."
                )

        if self.write_work_files_to_memory:
            file_location = temporary_file
        else:
            file_location = permanent_file

        self.waterfeatures_from_begrensningskurve_not_rivers = f"{file_location}waterfeatures_from_begrensningskurve_not_rivers_{unique_id}"
        self.land_features_area = f"{file_location}land_features_area_{unique_id}"
        self.selected_land_features = (
            f"{file_location}selected_land_features_{unique_id}"
        )
        self.land_features_buffer = f"{file_location}land_features_buffer_{unique_id}"
        self.begrensningskurve_waterfeatures_buffer = (
            f"{file_location}begrensningskurve_waterfeatures_buffer_{unique_id}"
        )
        self.erase_feature_1 = f"{file_location}erase_feature_1{unique_id}"

        self.working_files_list = [
            self.waterfeatures_from_begrensningskurve_not_rivers,
            self.land_features_area,
            self.selected_land_features,
            self.land_features_buffer,
            self.begrensningskurve_waterfeatures_buffer,
            self.erase_feature_1,
        ]

    def selections(self):
        if self.write_work_files_to_memory:
            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=self.input_begrensningskurve,
                expression="objtype = 'Innsjøkant' Or objtype = 'InnsjøkantRegulert' Or objtype = 'Kystkontur'",
                output_name=self.waterfeatures_from_begrensningskurve_not_rivers,
            )

            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=self.input_land_features,
                expression="""objtype NOT IN ('ElvBekk', 'Havflate', 'Innsjø', 'InnsjøRegulert')""",
                output_name=self.land_features_area,
            )

            custom_arcpy.select_location_and_make_feature_layer(
                input_layer=self.land_features_area,
                overlap_type=custom_arcpy.OverlapType.BOUNDARY_TOUCHES.value,
                select_features=self.waterfeatures_from_begrensningskurve_not_rivers,
                output_name=self.selected_land_features,
            )

        if not self.write_work_files_to_memory:
            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=self.input_begrensningskurve,
                expression="objtype = 'Innsjøkant' Or objtype = 'InnsjøkantRegulert' Or objtype = 'Kystkontur'",
                output_name=self.waterfeatures_from_begrensningskurve_not_rivers,
            )

            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=self.input_land_features,
                expression="""objtype NOT IN ('ElvBekk', 'Havflate', 'Innsjø', 'InnsjøRegulert')""",
                output_name=self.land_features_area,
            )

            custom_arcpy.select_location_and_make_permanent_feature(
                input_layer=self.land_features_area,
                overlap_type=custom_arcpy.OverlapType.BOUNDARY_TOUCHES.value,
                select_features=self.waterfeatures_from_begrensningskurve_not_rivers,
                output_name=self.selected_land_features,
            )

    def creating_buffers(self):
        arcpy.analysis.PairwiseBuffer(
            in_features=self.selected_land_features,
            out_feature_class=self.land_features_buffer,
            buffer_distance_or_field=f"{self.water_feature_buffer_width} Meters",
        )

        self.water_feature_buffer_width += self.water_barrier_buffer_width

        arcpy.analysis.PairwiseBuffer(
            in_features=self.waterfeatures_from_begrensningskurve_not_rivers,
            out_feature_class=self.begrensningskurve_waterfeatures_buffer,
            buffer_distance_or_field=f"{self.water_feature_buffer_width} Meters",
        )

    def erase_buffers(self):
        arcpy.analysis.Erase(
            in_features=self.begrensningskurve_waterfeatures_buffer,
            erase_features=self.land_features_buffer,
            out_feature_class=self.erase_feature_1,
        )

        arcpy.analysis.Erase(
            in_features=self.erase_feature_1,
            erase_features=self.land_features_area,
            out_feature_class=self.output_begrensningskurve,
        )

    def delete_working_files(self, *file_paths):
        """Deletes multiple feature classes or files. Detailed alias and output_type logging is not available here."""
        for file_path in file_paths:
            self.delete_feature_class(file_path)
            print(f"Deleted file: {file_path}")

    @staticmethod
    def delete_feature_class(feature_class_path):
        """Deletes a feature class if it exists."""
        if arcpy.Exists(feature_class_path):
            arcpy.management.Delete(feature_class_path)

    @partition_io_decorator(
        input_param_names=["input_begrensningskurve", "input_land_features"],
        output_param_names=["output_begrensningskurve"],
    )
    def run(self):
        self.reset_temp_files()
        self.selections()
        self.creating_buffers()
        self.erase_buffers()
        if not self.keep_work_files:
            self.delete_working_files(*self.working_files_list)


if __name__ == "__main__":
    environment_setup.main()
    begrensningskurve_land_waterbodies = BegrensningskurveLandWaterbodies(
        input_begrensningskurve=input_n100.BegrensningsKurve,
        input_land_features=input_n100.ArealdekkeFlate,
        water_feature_buffer_width=N100_Values.building_water_intrusion_distance_m.value,
        output_begrensningskurve=Building_N100.begrensingskurve_land_water___begrensingskurve_buffer_in_water___n100_building.value,
        write_work_files_to_memory=False,
        keep_work_files=False,
        root_file=Building_N100.begrensingskurve_land_water___root_file___n100_building.value,
    )
    begrensningskurve_land_waterbodies.run()
