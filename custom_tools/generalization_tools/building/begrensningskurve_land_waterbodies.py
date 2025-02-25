import arcpy

from input_data import input_n100

# Importing custom modules
from file_manager.n100.file_manager_buildings import Building_N100
from env_setup import environment_setup
from custom_tools.decorators.partition_io_decorator import partition_io_decorator
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.file_utilities import WorkFileManager
from constants.n100_constants import N100_Values


class BegrensningskurveLandWaterbodies:
    def __init__(
        self,
        input_begrensningskurve: str,
        input_land_cover_features: str,
        water_feature_buffer_width: int,
        output_begrensningskurve: str,
        water_barrier_buffer_width: int = 30,
        write_work_files_to_memory: bool = True,
        keep_work_files: bool = False,
        root_file: str = None,
    ):
        self.input_begrensningskurve = input_begrensningskurve
        self.input_land_cover_features = input_land_cover_features
        self.output_begrensningskurve = output_begrensningskurve

        self.write_work_files_to_memory = write_work_files_to_memory
        self.keep_work_files = keep_work_files
        self.root_file = root_file

        # How far out from land water buffer is created
        self.water_feature_buffer_width = water_feature_buffer_width

        # How wide the water feature buffer will be
        self.water_barrier_buffer_width = water_barrier_buffer_width

        self.area_length_ratio_field_name = "area_length_ratio"

        self.work_file_manager = WorkFileManager(
            unique_id=id(self),
            root_file=root_file,
            write_to_memory=write_work_files_to_memory,
            keep_files=keep_work_files,
        )

        self.waterfeatures_from_begrensningskurve = (
            "waterfeatures_from_begrensningskurve"
        )
        self.waterfeatures_from_begrensningskurve_selection = (
            "waterfeatures_from_begrensningskurve_selection"
        )
        self.land_features_area = "land_features_area"
        self.water_features_area = "water_features_area"
        self.water_features_area_narrow = "water_features_area_narrow"
        self.water_features_area_wide = "water_features_area_wide"
        self.selected_land_features = "selected_land_features"
        self.land_features_buffer = "land_features_buffer"
        self.begrensningskurve_waterfeatures_buffer = (
            "begrensningskurve_waterfeatures_buffer"
        )
        self.erase_feature_1 = "erase_feature_1"
        self.erase_feature_2 = "erase_feature_2"

        self.work_file_list = [
            self.waterfeatures_from_begrensningskurve,
            self.waterfeatures_from_begrensningskurve_selection,
            self.land_features_area,
            self.water_features_area,
            self.water_features_area_narrow,
            self.water_features_area_wide,
            self.selected_land_features,
            self.land_features_buffer,
            self.begrensningskurve_waterfeatures_buffer,
            self.erase_feature_1,
            self.erase_feature_2,
        ]

    def selections(self):
        if self.write_work_files_to_memory:
            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=self.input_begrensningskurve,
                expression="""objtype IN ('Innsjøkant', 'InnsjøkantRegulert', 'Kystkontur', 'ElvBekkKant')""",
                output_name=self.waterfeatures_from_begrensningskurve,
            )

            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=self.input_land_cover_features,
                expression="""objtype IN ('ElvBekk', 'Havflate', 'Innsjø', 'InnsjøRegulert')""",
                output_name=self.water_features_area,
            )

            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=self.input_land_cover_features,
                expression="""objtype NOT IN ('ElvBekk', 'Havflate', 'Innsjø', 'InnsjøRegulert')""",
                output_name=self.land_features_area,
            )

            custom_arcpy.select_location_and_make_feature_layer(
                input_layer=self.land_features_area,
                overlap_type=custom_arcpy.OverlapType.BOUNDARY_TOUCHES.value,
                select_features=self.waterfeatures_from_begrensningskurve,
                output_name=self.selected_land_features,
            )

        if not self.write_work_files_to_memory:
            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=self.input_begrensningskurve,
                expression="""objtype IN ('Innsjøkant', 'InnsjøkantRegulert', 'Kystkontur', 'ElvBekkKant')""",
                output_name=self.waterfeatures_from_begrensningskurve,
            )

            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=self.input_land_cover_features,
                expression="""objtype IN ('ElvBekk', 'Havflate', 'Innsjø', 'InnsjøRegulert')""",
                output_name=self.water_features_area,
            )

            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=self.input_land_cover_features,
                expression="""objtype NOT IN ('ElvBekk', 'Havflate', 'Innsjø', 'InnsjøRegulert')""",
                output_name=self.land_features_area,
            )

            custom_arcpy.select_location_and_make_permanent_feature(
                input_layer=self.land_features_area,
                overlap_type=custom_arcpy.OverlapType.BOUNDARY_TOUCHES.value,
                select_features=self.waterfeatures_from_begrensningskurve,
                output_name=self.selected_land_features,
            )

    def field_management(self):
        arcpy.management.AddField(
            in_table=self.water_features_area,
            field_name=self.area_length_ratio_field_name,
            field_type="FLOAT",
        )

        sql_expr = "!shape.area! / !shape.length!"
        arcpy.management.CalculateField(
            in_table=self.water_features_area,
            field=self.area_length_ratio_field_name,
            expression=sql_expr,
        )

    def finding_narrow_or_not(self):
        sql_expression_narrow = f'"{self.area_length_ratio_field_name}" < 100'
        sql_expression_wide = f'"{self.area_length_ratio_field_name}" >= 100'

        if self.write_work_files_to_memory:
            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=self.water_features_area,
                expression=sql_expression_narrow,
                output_name=self.water_features_area_narrow,
            )

            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=self.water_features_area,
                expression=sql_expression_wide,
                output_name=self.water_features_area_wide,
            )

            custom_arcpy.select_location_and_make_feature_layer(
                input_layer=self.waterfeatures_from_begrensningskurve,
                overlap_type=custom_arcpy.OverlapType.BOUNDARY_TOUCHES.value,
                select_features=self.water_features_area_wide,
                output_name=self.waterfeatures_from_begrensningskurve_selection,
            )

        if not self.write_work_files_to_memory:
            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=self.water_features_area,
                expression=sql_expression_narrow,
                output_name=self.water_features_area_narrow,
            )

            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=self.water_features_area,
                expression=sql_expression_wide,
                output_name=self.water_features_area_wide,
            )

            custom_arcpy.select_location_and_make_permanent_feature(
                input_layer=self.waterfeatures_from_begrensningskurve,
                overlap_type=custom_arcpy.OverlapType.BOUNDARY_TOUCHES.value,
                select_features=self.water_features_area_wide,
                output_name=self.waterfeatures_from_begrensningskurve_selection,
            )

    def creating_buffers(self):
        arcpy.analysis.PairwiseBuffer(
            in_features=self.selected_land_features,
            out_feature_class=self.land_features_buffer,
            buffer_distance_or_field=f"{self.water_feature_buffer_width} Meters",
        )

        self.water_feature_buffer_width += self.water_barrier_buffer_width

        arcpy.analysis.PairwiseBuffer(
            in_features=self.waterfeatures_from_begrensningskurve_selection,
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
            out_feature_class=self.erase_feature_2,
        )

    def merge_water_features(self):
        arcpy.management.Merge(
            inputs=[
                self.water_features_area_narrow,
                self.erase_feature_2,
            ],
            output=self.output_begrensningskurve,
        )

    @partition_io_decorator(
        input_param_names=["input_begrensningskurve", "input_land_cover_features"],
        output_param_names=["output_begrensningskurve"],
    )
    def run(self):
        environment_setup.main()

        self.work_file_list = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.work_file_list,
        )

        self.selections()
        self.field_management()
        self.finding_narrow_or_not()
        self.creating_buffers()
        self.erase_buffers()
        self.merge_water_features()

        self.work_file_manager.delete_created_files()


if __name__ == "__main__":
    environment_setup.main()
    begrensningskurve_land_waterbodies = BegrensningskurveLandWaterbodies(
        input_begrensningskurve=Building_N100.data_selection___begrensningskurve_n100_input_data___n100_building.value,
        input_land_cover_features=Building_N100.data_selection___land_cover_n100_input_data___n100_building.value,
        water_feature_buffer_width=N100_Values.building_water_intrusion_distance_m.value,
        output_begrensningskurve=Building_N100.begrensingskurve_land_water___begrensingskurve_buffer_in_water___n100_building.value,
        write_work_files_to_memory=False,
        keep_work_files=False,
        root_file=Building_N100.begrensingskurve_land_water___root_file___n100_building.value,
    )
    begrensningskurve_land_waterbodies.run()
