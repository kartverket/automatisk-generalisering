import arcpy

from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from env_setup import environment_setup
from custom_tools.general_tools.geometry_tools import GeometryValidator
from custom_tools.general_tools.partition_iterator import PartitionIterator
from composition_configs import core_config, logic_config
from generalization.n10.arealdekke.parameters.parameter_dataclasses import (
    EliminateSmallPolygonsParameters,
)
from pathlib import Path
from custom_tools.general_tools.param_utils import initialize_params
import os


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

        self.map_scale = eliminate_small_polygons_config.map_scale
        params_path = Path(__file__).parent.parent / "parameters" / "parameters.yml"
        self.scale_parameters = initialize_params(
            params_path=params_path,
            class_name="EliminateSmallPolygons",
            map_scale=self.map_scale,
            dataclass=EliminateSmallPolygonsParameters,
        )

        self.files = self._create_wfm_gdbs(self.wfm)

        self.geometry_validator = GeometryValidator()

    def _create_wfm_gdbs(self, wfm: WorkFileManager) -> dict:
        eliminate_input = wfm.build_file_path(
            file_name="eliminate_input", file_type="gdb"
        )
        eliminate_input_include = wfm.build_file_path(
            file_name="eliminate_input_include", file_type="gdb"
        )
        eliminate_input_exclude = wfm.build_file_path(
            file_name="eliminate_input_exclude", file_type="gdb"
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
        eliminate_final_elim_merged = wfm.build_file_path(
            file_name="eliminate_final_elim_merged", file_type="gdb"
        )

        return {
            "eliminate_input": eliminate_input,
            "eliminate_input_include": eliminate_input_include,
            "eliminate_input_exclude": eliminate_input_exclude,
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
            "eliminate_final_elim_merged": eliminate_final_elim_merged,
        }

    def _fetch_data(self):
        arcpy.management.CopyFeatures(
            in_features=self.input_eliminate,
            out_feature_class=self.files["eliminate_input"],
        )

    def _exlude(self):
        """
        Removes certain arealdekke types to exclude them from being eliminated and eliminated into
        """
        include = "layer_include"
        exclude = "layer_exclude"
        quoted = ", ".join(f"'{v}'" for v in self.scale_parameters.exclude)
        exclusion_sql = f"arealdekke NOT IN ({quoted})"
        not_exclusion_sql = f"arealdekke IN ({quoted})"

        arcpy.management.MakeFeatureLayer(
            self.files["eliminate_input"],
            include,
            where_clause=exclusion_sql,
        )
        arcpy.management.CopyFeatures(include, self.files["eliminate_input_include"])
        arcpy.management.MakeFeatureLayer(
            self.files["eliminate_input"],
            exclude,
            where_clause=not_exclusion_sql,
        )
        arcpy.management.CopyFeatures(exclude, self.files["eliminate_input_exclude"])

    def _merge_excluded(self):
        """
        Merge excluded data to output
        """
        arcpy.management.Merge(
            [self.files["eliminate_input_exclude"], self.files["eliminate_final_elim"]],
            self.files["eliminate_final_elim_merged"],
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
        quoted = ", ".join(f"'{v}'" for v in self.scale_parameters.dont_eliminate)
        exclusion_sql = f"arealdekke NOT IN ({quoted})"
        numeric_clauses = []
        numeric_clauses.append(f"area < {self.scale_parameters.max_area_b_iq}")
        numeric_clauses.append(
            f"iq_adjusted_area < {self.scale_parameters.min_iq_area}"
        )

        # combine all parts into one where clause
        where_parts = [exclusion_sql] + numeric_clauses
        where_clause = " AND ".join(where_parts)

        arcpy.management.MakeFeatureLayer(
            in_features=input_fc, out_layer=layer, where_clause=where_clause
        )

        arcpy.management.Eliminate(
            in_features=layer,
            out_feature_class=output_fc,
            selection="LENGTH",
        )

        self.geometry_validator.check_repair_sequence(
            input_fc=output_fc, max_iterations=5
        )

    @timing_decorator
    def _buffer_potential_spikes(self):
        """Buffer all polygons except water and samferdsel to remove spikes"""
        layer = "eliminate_after_elim_layer"
        quoted = ", ".join(f"'{v}'" for v in self.scale_parameters.dont_remove_spikes)
        exclusion_sql = f"arealdekke NOT IN ({quoted})"

        arcpy.management.MakeFeatureLayer(
            in_features=self.files["eliminate_after_elim"],
            out_layer=layer,
            where_clause=exclusion_sql,
        )
        arcpy.analysis.Buffer(
            in_features=layer,
            out_feature_class=self.files["eliminate_selected_negative_buffers"],
            buffer_distance_or_field=f"-{self.scale_parameters.spike_size} Meters",
        )
        arcpy.analysis.Buffer(
            in_features=self.files["eliminate_selected_negative_buffers"],
            out_feature_class=self.files["eliminate_selected_positive_buffers"],
            buffer_distance_or_field=f"{self.scale_parameters.spike_size} Meters",
        )

    @timing_decorator
    def _clip_and_erase(self):
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
        self.geometry_validator.check_repair_sequence(
            input_fc=self.files["eliminate_clipped"], max_iterations=5
        )
        self.geometry_validator.check_repair_sequence(
            input_fc=self.files["eliminate_erased"], max_iterations=5
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

        self.geometry_validator.check_repair_sequence(
            input_fc=self.files["eliminate_merged_clipped_erased"], max_iterations=5
        )

        quoted = ", ".join(f"'{v}'" for v in self.scale_parameters.dont_remove_spikes)
        exclusion_sql = f"arealdekke NOT IN ({quoted})"
        numeric_clauses = []
        numeric_clauses.append(f"area < {self.scale_parameters.min_area}")
        where_parts = [exclusion_sql] + numeric_clauses
        where_clause = " AND ".join(where_parts)

        layer = "eliminate_merged_clipped_erased_layer"
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["eliminate_merged_clipped_erased"],
            out_layer=layer,
            where_clause=where_clause,
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
            cluster_tolerance=f"{self.scale_parameters.integrate_tolerance} Meters",
        )

    @staticmethod
    def remove_fields(input_fc):
        """Remove area, length, isoperimetric quotient and iq_adjusted_area fields"""
        arcpy.management.DeleteField(
            input_fc, ["area", "length", "isoperimetric_quotient", "iq_adjusted_area"]
        )

    def eliminate_holes(
        self, input_fc: str, output_fc: str, selection: str, wfm: WorkFileManager
    ):
        """
        Eliminates polygons that are holes inside polygons in selection defined in selection parameter, if they are within elim parameters
        """
        input_copy = wfm.build_file_path(
            file_name="eliminate_holes_input_copy", file_type="gdb"
        )
        lines = wfm.build_file_path(file_name="eliminate_holes_lines", file_type="gdb")
        singlepart = wfm.build_file_path(
            file_name="eliminate_holes_singlepart", file_type="gdb"
        )
        potential_holes_lines = wfm.build_file_path(
            file_name="eliminate_holes_potential_holes_lines", file_type="gdb"
        )
        potential_holes_polygons = wfm.build_file_path(
            file_name="eliminate_holes_potential_holes_polygons", file_type="gdb"
        )
        eliminated = wfm.build_file_path(
            file_name="eliminate_holes_eliminated", file_type="gdb"
        )
        input_copy_layer_selection = "eliminate_holes_input_copy_layer_selection"
        input_copy_layer_potential_elims = (
            "eliminate_holes_input_copy_layer_potential_elims"
        )
        singlepart_layer = "eliminate_holes_singlepart_layer"

        arcpy.management.CopyFeatures(
            in_features=input_fc, out_feature_class=input_copy
        )
        self.add_fields(input_copy)
        arcpy.management.MakeFeatureLayer(
            in_features=input_copy,
            out_layer=input_copy_layer_selection,
            where_clause=selection,
        )
        arcpy.management.PolygonToLine(
            in_features=input_copy_layer_selection,
            out_feature_class=lines,
            neighbor_option="IGNORE_NEIGHBORS",
        )
        arcpy.management.MultipartToSinglepart(
            in_features=lines, out_feature_class=singlepart
        )

        sr = arcpy.Describe(lines).spatialReference
        path, name = os.path.split(potential_holes_lines)
        arcpy.management.CreateFeatureclass(
            out_path=path, out_name=name, geometry_type="POLYLINE", spatial_reference=sr
        )
        with arcpy.da.SearchCursor(lines, ["SHAPE@"]) as scur, arcpy.da.InsertCursor(
            potential_holes_lines, ["SHAPE@"]
        ) as icur:
            for row in scur:
                poly = row[0]
                # parts: index 0 = exterior; indexes 1..n-1 = holes
                for i in range(1, poly.partCount):
                    part = poly.getPart(i)
                    # build a Polyline from the part points
                    pl = arcpy.Polyline(arcpy.Array([p for p in part]), sr)
                    icur.insertRow([pl])

        arcpy.management.FeatureToPolygon(
            in_features=potential_holes_lines,
            out_feature_class=potential_holes_polygons,
        )

        quoted = ", ".join(f"'{v}'" for v in self.scale_parameters.dont_eliminate)
        exclusion_sql = f"arealdekke NOT IN ({quoted})"
        numeric_clauses = []
        numeric_clauses.append(f"area < {self.scale_parameters.max_area_b_iq}")
        numeric_clauses.append(
            f"iq_adjusted_area < {self.scale_parameters.min_iq_area}"
        )
        where_parts = [exclusion_sql] + numeric_clauses
        where_clause = " AND ".join(where_parts)

        arcpy.management.MakeFeatureLayer(
            in_features=input_copy, out_layer=input_copy_layer_potential_elims
        )
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=input_copy_layer_potential_elims,
            selection_type="NEW_SELECTION",
            where_clause=where_clause,
        )
        arcpy.management.SelectLayerByLocation(
            in_layer=input_copy_layer_potential_elims,
            overlap_type="INTERSECT",
            select_features=potential_holes_polygons,
            selection_type="REMOVE_FROM_SELECTION",
            invert_spatial_relationship="INVERT",
        )

        arcpy.management.Eliminate(
            in_features=input_copy_layer_potential_elims,
            out_feature_class=output_fc,
            selection="LENGTH",
        )
        self.remove_fields(output_fc)

    @timing_decorator
    def run(self):
        environment_setup.main()

        self._fetch_data()
        self.add_fields(self.files["eliminate_input"])
        self._exlude()
        self.eliminate(
            self.files["eliminate_input_include"], self.files["eliminate_after_elim"]
        )
        self._buffer_potential_spikes()
        self._clip_and_erase()
        self.eliminate(
            self.files["eliminate_clip_erase_eliminated"],
            self.files["eliminate_final_elim"],
        )
        self._merge_excluded()
        self._integrate(self.files["eliminate_final_elim_merged"])
        self.remove_fields(self.files["eliminate_final_elim_merged"])

        arcpy.management.CopyFeatures(
            in_features=self.files["eliminate_final_elim_merged"],
            out_feature_class=self.output_feature,
        )
        self.geometry_validator.check_repair_sequence(
            input_fc=self.output_feature, max_iterations=5
        )

        self.wfm.delete_created_files()


def normal_call(input_fc: str, output_fc: str, map_scale: str):

    eliminate_config = logic_config.EliminateSmallPolygonsInitKwargs(
        input_feature=input_fc,
        output_feature=output_fc,
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Arealdekke_N10.dissolve_arealdekke_root.value
        ),
        map_scale=map_scale,
    )
    EliminateSmallPolygons(eliminate_small_polygons_config=eliminate_config).run()


def partition_call(input_fc: str, output_fc: str, map_scale: str):
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
        map_scale=map_scale,
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
        map_scale="N10",
    )
