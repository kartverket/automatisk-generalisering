import arcpy

from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from env_setup import environment_setup
from custom_tools.general_tools.partition_iterator import PartitionIterator
from composition_configs import core_config, logic_config


class EliminateSmallPolygons:
    """
    Eliminates small polygons based on area times isoperimetric quotient, while excluding rivers and samferdsel.
    Also removes narrow polygon parts using buffer.
    """

    def __init__(
        self,
        eliminate_small_polygons_config: logic_config.EliminateSmallPolygonsInitKwargs,
    ):
        self.input_eliminate = eliminate_small_polygons_config.input_feature
        self.output_feature = eliminate_small_polygons_config.output_feature

        self.wfm = WorkFileManager(
            config=eliminate_small_polygons_config.work_file_manager_config
        )
        self.files = self.create_wfm_gdbs(self.wfm)

    def create_wfm_gdbs(self, wfm: WorkFileManager) -> dict:
        eliminate_input = wfm.build_file_path(
            file_name="eliminate_input", file_type="gdb"
        )
        eliminate_eliminated = wfm.build_file_path(
            file_name="eliminate_eliminated", file_type="gdb"
        )
        eliminate_after_elim = wfm.build_file_path(
            file_name="eliminate_after_elim", file_type="gdb"
        )
        eliminate_selected_negative_buffers = wfm.build_file_path(
            file_name="eliminate_selected_negative_buffers", file_type="gdb"
        )
        eliminate_selected_positive_buffers = wfm.build_file_path(
            file_name="eliminate_selected_positive_buffers", file_type="gdb"
        )
        eliminate_clipped = wfm.build_file_path(
            file_name="eliminate_clipped", file_type="gdb"
        )
        eliminate_erased = wfm.build_file_path(
            file_name="eliminate_erased", file_type="gdb"
        )
        eliminate_erased_singlepart = wfm.build_file_path(
            file_name="eliminate_erased_singlepart", file_type="gdb"
        )
        eliminate_merged_clipped_erased = wfm.build_file_path(
            file_name="eliminate_merged_clipped_erased", file_type="gdb"
        )
        eliminate_clip_erase_eliminated = wfm.build_file_path(
            file_name="eliminate_clip_erase_eliminated", file_type="gdb"
        )
        eliminate_final_elim = wfm.build_file_path(
            file_name="eliminate_final_elim", file_type="gdb"
        )
        eliminate_clipped_singlepart = wfm.build_file_path(
            file_name="eliminate_clipped_singlepart", file_type="gdb"
        )

        return {
            "eliminate_input": eliminate_input,
            "eliminate_eliminated": eliminate_eliminated,
            "eliminate_after_elim": eliminate_after_elim,
            "eliminate_selected_negative_buffers": eliminate_selected_negative_buffers,
            "eliminate_selected_positive_buffers": eliminate_selected_positive_buffers,
            "eliminate_clipped": eliminate_clipped,
            "eliminate_erased": eliminate_erased,
            "eliminate_erased_singlepart": eliminate_erased_singlepart,
            "eliminate_clipped_singlepart": eliminate_clipped_singlepart,
            "eliminate_merged_clipped_erased": eliminate_merged_clipped_erased,
            "eliminate_clip_erase_eliminated": eliminate_clip_erase_eliminated,
            "eliminate_final_elim": eliminate_final_elim,
        }

    def fetch_data(self):
        arcpy.management.CopyFeatures(
            in_features=self.input_eliminate,
            out_feature_class=self.files["eliminate_input"],
        )

    @timing_decorator
    def add_fields(self, input_fc):
        """Add area, length, isoperimetric quotient and iq_adjusted_area fields to the input feature class, and populate them with values."""
        fields = [f.name for f in arcpy.ListFields(input_fc)]
        if "area" in fields:
            arcpy.management.DeleteField(input_fc, "area")
        if "length" in fields:
            arcpy.management.DeleteField(input_fc, "length")
        if "isoperimetric_quotient" in fields:
            arcpy.management.DeleteField(input_fc, "isoperimetric_quotient")
        if "iq_adjusted_area" in fields:
            arcpy.management.DeleteField(input_fc, "iq_adjusted_area")

        arcpy.management.AddField(
            in_table=input_fc, field_name="area", field_type="DOUBLE"
        )
        arcpy.management.CalculateField(
            in_table=input_fc,
            field="area",
            expression="!shape.area!",
            expression_type="PYTHON3",
        )
        arcpy.management.AddField(
            in_table=input_fc, field_name="length", field_type="DOUBLE"
        )
        arcpy.management.CalculateField(
            in_table=input_fc,
            field="length",
            expression="!shape.length!",
            expression_type="PYTHON3",
        )

        arcpy.management.AddField(
            in_table=input_fc, field_name="isoperimetric_quotient", field_type="DOUBLE"
        )
        arcpy.management.CalculateField(
            in_table=input_fc,
            field="isoperimetric_quotient",
            expression="(4 * 3.141592653589793 * !area!) / (!length! ** 2)",
            expression_type="PYTHON3",
        )
        arcpy.management.AddField(
            in_table=input_fc, field_name="iq_adjusted_area", field_type="DOUBLE"
        )
        arcpy.management.CalculateField(
            in_table=input_fc,
            field="iq_adjusted_area",
            expression="!area! * !isoperimetric_quotient!",
            expression_type="PYTHON3",
        )

    @timing_decorator
    def eliminate(self, input_fc, output_fc):
        """Eliminate small polygons based on area times isoperimetric quotient, while excluding rivers and samferdsel."""
        layer = "eliminate_layer"
        arcpy.management.MakeFeatureLayer(
            in_features=input_fc,
            out_layer=layer,
            where_clause="arealdekke <> 'Samferdsel' AND arealdekke <> 'Ferskvann_elv_bekk' AND arealdekke <> 'Ferskvann_kanal' AND area < 1500 AND iq_adjusted_area < 150",
        )

        arcpy.management.Eliminate(
            in_features=layer,
            out_feature_class=output_fc,
            selection="LENGTH",
        )

    @timing_decorator
    def buffer_potential_spikes(self):
        """Buffer all polygons except water and samferdsel to remove spikes"""
        layer = "eliminate_after_elim_layer"
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["eliminate_after_elim"],
            out_layer=layer,
            where_clause="arealdekke <> 'Samferdsel' AND arealdekke <> 'Ferskvann_elv_bekk' AND arealdekke <> 'Ferskvann_kanal' AND arealdekke <> 'Ferskvann_innsjo_tjern_regulert' AND arealdekke <> 'Ferskvann_innsjo_tjern'",  # AND isoperimetric_quotient < 0.3 takes longer without this but if we add this there will definetively be spikes that are missed
        )
        arcpy.analysis.Buffer(
            in_features=layer,
            out_feature_class=self.files["eliminate_selected_negative_buffers"],
            buffer_distance_or_field="-4 Meters",
        )
        arcpy.analysis.Buffer(
            in_features=self.files["eliminate_selected_negative_buffers"],
            out_feature_class=self.files["eliminate_selected_positive_buffers"],
            buffer_distance_or_field="4 Meters",
        )

    @timing_decorator
    def clip_and_erase(self):
        """Clip and erase the buffered features, to remove narrow parts of polygons, and then merge the clipped and erased features back together. And run a final eliminate on anything smaller than 100 sqm that is not water or samferdsel."""
        arcpy.analysis.Clip(
            in_features=self.files["eliminate_after_elim"],
            clip_features=self.files["eliminate_selected_positive_buffers"],
            out_feature_class=self.files["eliminate_clipped"],
        )
        arcpy.analysis.Erase(
            in_features=self.files["eliminate_after_elim"],
            erase_features=self.files["eliminate_selected_positive_buffers"],
            out_feature_class=self.files["eliminate_erased"],
        )
        print("Repairing geometry...")
        arcpy.management.RepairGeometry(
            in_features=self.files["eliminate_erased"],
            delete_null="DELETE_NULL",
            validation_method="ESRI",
        )
        arcpy.management.RepairGeometry(
            in_features=self.files["eliminate_clipped"],
            delete_null="DELETE_NULL",
            validation_method="ESRI",
        )

        arcpy.management.MultipartToSinglepart(
            in_features=self.files["eliminate_erased"],
            out_feature_class=self.files["eliminate_erased_singlepart"],
        )
        arcpy.management.MultipartToSinglepart(
            in_features=self.files["eliminate_clipped"],
            out_feature_class=self.files["eliminate_clipped_singlepart"],
        )

        arcpy.management.Merge(
            inputs=[
                self.files["eliminate_clipped_singlepart"],
                self.files["eliminate_erased_singlepart"],
            ],
            output=self.files["eliminate_merged_clipped_erased"],
        )

        self.add_fields(self.files["eliminate_merged_clipped_erased"])

        arcpy.management.RepairGeometry(
            in_features=self.files["eliminate_merged_clipped_erased"],
            delete_null="DELETE_NULL",
            validation_method="ESRI",
        )

        layer = "eliminate_merged_clipped_erased_layer"
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["eliminate_merged_clipped_erased"],
            out_layer=layer,
            where_clause="area < 100 AND arealdekke <> 'Samferdsel' AND arealdekke <> 'Ferskvann_elv_bekk' AND arealdekke <> 'Ferskvann_kanal' AND arealdekke <> 'Ferskvann_innsjo_tjern_regulert' AND arealdekke <> 'Ferskvann_innsjo_tjern'",
        )

        arcpy.management.Eliminate(
            in_features=layer,
            out_feature_class=self.files["eliminate_clip_erase_eliminated"],
            selection="LENGTH",
        )

    @timing_decorator
    def _integrate(self, input_fc):
        arcpy.management.Integrate(
            in_features=input_fc,
            cluster_tolerance="0.09 Meters",
        )

    def _remove_fields(self, input_fc):
        """Remove area, length, isoperimetric quotient and iq_adjusted_area fields"""
        arcpy.management.DeleteField(
            input_fc, ["area", "length", "isoperimetric_quotient", "iq_adjusted_area"]
        )

    @timing_decorator
    def run(self):
        environment_setup.main()
        self.fetch_data()
        self.add_fields(self.files["eliminate_input"])
        self.eliminate(
            self.files["eliminate_input"], self.files["eliminate_after_elim"]
        )
        self.buffer_potential_spikes()
        self.clip_and_erase()
        self.eliminate(
            self.files["eliminate_clip_erase_eliminated"],
            self.files["eliminate_final_elim"],
        )

        self._integrate(self.files["eliminate_final_elim"])
        self._remove_fields(self.files["eliminate_final_elim"])

        arcpy.management.CopyFeatures(
            in_features=self.files["eliminate_final_elim"],
            out_feature_class=self.output_feature,
        )

        self.wfm.delete_created_files()


def normal_call(input_fc: str, output_fc: str):

    eliminate_config = logic_config.EliminateSmallPolygonsInitKwargs(
        input_feature=input_fc,
        output_feature=output_fc,
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Arealdekke_N10.dissolve_arealdekke_root.value
        ),
    )
    EliminateSmallPolygons(eliminate_small_polygons_config=eliminate_config).run()


def partition_call(input_fc: str, output_fc: str):
    eliminate = "eliminate"
    elim_small_polygon = "elim_small_polygon"
    partition_input_config = core_config.PartitionInputConfig(
        entries=[
            core_config.InputEntry.processing_input(
                object=eliminate,
                path=input_fc,
            )
        ]
    )

    partition_output_config = core_config.PartitionOutputConfig(
        entries=[
            core_config.OutputEntry.vector_output(
                object=eliminate,
                tag=elim_small_polygon,
                path=output_fc,
            )
        ]
    )

    partiton_area_io_config = core_config.PartitionIOConfig(
        input_config=partition_input_config,
        output_config=partition_output_config,
        documentation_directory=Arealdekke_N10.elim_documentation.value,
    )

    # Method Config:

    partiton_input = core_config.InjectIO(object=eliminate, tag="input")
    partition_output = core_config.InjectIO(object=eliminate, tag=elim_small_polygon)

    elim_init_config = logic_config.EliminateSmallPolygonsInitKwargs(
        input_feature=partiton_input,
        output_feature=partition_output,
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Arealdekke_N10.elim_root.value
        ),
    )
    elim_method = core_config.ClassMethodEntryConfig(
        class_=EliminateSmallPolygons,
        method=EliminateSmallPolygons.run,
        init_params=elim_init_config,
    )
    partition_method_config = core_config.MethodEntriesConfig(entries=[elim_method])

    # Run Config:
    partiton_run_config = core_config.PartitionRunConfig(
        max_elements_per_partition=50_000,
        context_radius_meters=0,
        run_partition_optimization=False,
    )

    # WorkFileConfig:
    partiton_workfile_config = core_config.WorkFileConfig(
        root_file=Arealdekke_N10.elim_root.value
    )

    # PartitionIterator Config:
    partition_elim = PartitionIterator(
        partition_io_config=partiton_area_io_config,
        partition_method_inject_config=partition_method_config,
        partition_iterator_run_config=partiton_run_config,
        work_file_manager_config=partiton_workfile_config,
    )

    partition_elim.run()


if __name__ == "__main__":
    partition_call(
        input_fc=Arealdekke_N10.dissolve_arealdekke.value,
        output_fc=Arealdekke_N10.elim_output.value,
    )
