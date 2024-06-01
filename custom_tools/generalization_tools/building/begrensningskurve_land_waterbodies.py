import arcpy

from input_data import input_n50
from input_data import input_n100
from input_data import input_other

# Importing custom modules
from file_manager.n100.file_manager_buildings import Building_N100
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.decorators.partition_io_decorator import partition_io_decorator
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from input_data import input_symbology
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values


class BegrensningskurveLandWaterbodies:
    def __init__(
        self,
        input_begrensningskurve,
        input_land_features,
        water_feature_buffer_width,
        output_begrensningskurve,
    ):
        self.input_begrensningskurve = input_begrensningskurve
        self.input_land_features = input_land_features
        self.water_feature_buffer_width = water_feature_buffer_width
        self.output_begrensningskurve = output_begrensningskurve

        self.working_files_list = []

    def selections(self):
        self.waterfeatures_from_begrensningskurve_not_rivers = (
            "in_memory/waterfeatures_from_begrensningskurve_not_rivers"
        )
        self.working_files_list.append(
            self.waterfeatures_from_begrensningskurve_not_rivers
        )
        custom_arcpy.select_attribute_and_make_feature_layer(
            input_layer=self.input_begrensningskurve,
            expression="objtype = 'Innsjøkant' Or objtype = 'InnsjøkantRegulert' Or objtype = 'Kystkontur'",
            output_name=self.waterfeatures_from_begrensningskurve_not_rivers,
        )

        self.land_features_area = "in_memory/land_features_area"
        self.working_files_list.append(self.land_features_area)
        custom_arcpy.select_attribute_and_make_feature_layer(
            input_layer=self.input_land_features,
            expression="""objtype NOT IN ('ElvBekk', 'Havflate', 'Innsjø', 'InnsjøRegulert')""",
            output_name=self.land_features_area,
        )

        self.selected_land_features = "in_memory/selected_land_features_area"
        self.working_files_list.append(self.selected_land_features)

        custom_arcpy.select_location_and_make_feature_layer(
            input_layer=self.land_features_area,
            overlap_type=custom_arcpy.OverlapType.BOUNDARY_TOUCHES.value,
            select_features=self.waterfeatures_from_begrensningskurve_not_rivers,
            output_name=self.selected_land_features,
        )

    def creating_buffers(self):
        self.land_features_buffer = "in_memory/land_features_buffer"
        self.working_files_list.append(self.land_features_buffer)

        arcpy.analysis.PairwiseBuffer(
            in_features=self.selected_land_features,
            out_feature_class=self.land_features_buffer,
            buffer_distance_or_field=f"{self.water_feature_buffer_width} Meters",
        )

        self.water_feature_buffer_width += 30

        self.begrensningskurve_waterfeatures_buffer = (
            "in_memory/begrensningskurve_waterfeatures_buffer"
        )
        self.working_files_list.append(self.begrensningskurve_waterfeatures_buffer)
        arcpy.analysis.PairwiseBuffer(
            in_features=self.waterfeatures_from_begrensningskurve_not_rivers,
            out_feature_class=self.begrensningskurve_waterfeatures_buffer,
            buffer_distance_or_field=f"{self.water_feature_buffer_width} Meters",
        )

    def erase_buffers(self):
        self.erase_feature_1 = "in_memory/erase_feature_1"
        self.working_files_list.append(self.erase_feature_1)
        arcpy.analysis.PairwiseErase(
            in_features=self.begrensningskurve_waterfeatures_buffer,
            erase_features=self.selected_land_features,
            out_feature_class=self.erase_feature_1,
        )

        arcpy.analysis.PairwiseErase(
            in_features=self.erase_feature_1,
            erase_features=self.land_features_buffer,
            out_feature_class=self.output_begrensningskurve,
        )

    def delete_working_files(self, *file_paths):
        """Deletes multiple feature classes or files. Detailed alias and output_type logging is not available here."""
        for file_path in file_paths:
            self.delete_feature_class(file_path)
            print(f"Deleted file: {file_path}")

    def delete_feature_class(self, feature_class_path):
        """Deletes a feature class if it exists."""
        if arcpy.Exists(feature_class_path):
            arcpy.management.Delete(feature_class_path)

    @partition_io_decorator(
        input_param_names=["input_begrensningskurve", "input_land_features"],
        output_param_names=["output_begrensningskurve"],
    )
    def run(self):
        self.selections()
        self.creating_buffers()
        self.erase_buffers()
        self.delete_working_files(*self.working_files_list)


if __name__ == "__main__":
    environment_setup.main()
    begrensningskurve_land_waterbodies = BegrensningskurveLandWaterbodies(
        input_begrensningskurve=input_n100.BegrensningsKurve,
        input_land_features=input_n100.ArealdekkeFlate,
        water_feature_buffer_width=N100_Values.building_water_intrusion_distance_m.value,
        output_begrensningskurve=Building_N100.begrensingskurve_land_water___begrensingskurve_buffer_in_water___n100_building.value,
    )
    begrensningskurve_land_waterbodies.run()
