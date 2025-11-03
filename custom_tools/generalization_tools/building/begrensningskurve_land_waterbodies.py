import arcpy


# Importing custom modules
from file_manager.n100.file_manager_buildings import Building_N100
from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy
from file_manager import WorkFileManager
from composition_configs import logic_config
from constants.n100_constants import N100_Values


class BegrensningskurveLandWaterbodies:
    def __init__(
        self,
        land_water_config: logic_config.BegrensningskurveLandWaterKwargs,
    ):
        self.input_begrensningskurve = land_water_config.input_begrensningskurve
        self.input_land_cover_features = land_water_config.input_land_cover_features
        self.output_begrensningskurve = land_water_config.output_begrensningskurve

        self.write_work_files_to_memory = (
            land_water_config.work_file_manager_config.write_to_memory
        )
        self.keep_work_files = land_water_config.work_file_manager_config.keep_files
        self.root_file = land_water_config.work_file_manager_config.root_file

        # How far out from land water buffer is created
        self.water_feature_buffer_width = land_water_config.water_feature_buffer_width

        # How wide the water feature buffer will be
        self.water_barrier_buffer_width = land_water_config.water_barrier_buffer_width

        self.area_length_ratio_field_name = "area_length_ratio"

        self.wfm = WorkFileManager(config=land_water_config.work_file_manager_config)

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

    def run(self):
        environment_setup.main()

        self.work_file_list = self.wfm.setup_work_file_paths(
            instance=self,
            file_structure=self.work_file_list,
        )

        self.selections()
        self.field_management()
        self.finding_narrow_or_not()
        self.creating_buffers()
        self.erase_buffers()
        self.merge_water_features()

        self.wfm.delete_created_files()


if __name__ == "__main__":
    environment_setup.main()
