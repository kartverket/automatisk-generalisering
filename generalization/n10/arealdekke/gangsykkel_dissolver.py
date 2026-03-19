import arcpy

from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from env_setup import environment_setup
from custom_tools.general_tools.partition_iterator import PartitionIterator
from composition_configs import core_config, logic_config
from generalization.n10.arealdekke.arealdekke_dissolver import ArealdekkeDissolver
from collections import defaultdict
from pathlib import Path
from custom_tools.general_tools.param_utils import initialize_params
from parameters.parameter_dataclasses import GangSykkelDissolverParameters


class GangSykkelDissolver:
    """
    Dissolved gang og sykkel vei polygons that are adjecent to other samferdsel polygons into samferdsel.
    Iteratively buffer 5m, clip, split by length and dissolve until no more dissolving is done.
    dissolve gang og sykkel over a certain length into samferdsel, and keep the rest as gang og sykkel.
    """

    def __init__(
        self, gang_sykkel_dissolver_config: logic_config.GangSykkelDissolverInitKwargs
    ):
        self.input_gangsykkel = gang_sykkel_dissolver_config.input_feature
        self.output_feature = gang_sykkel_dissolver_config.output_feature

        self.index_col = gang_sykkel_dissolver_config.index_column_name

        self.wfm = WorkFileManager(
            config=gang_sykkel_dissolver_config.work_file_manager_config
        )
        self.files = self._create_wfm_gdbs(self.wfm)

        self.map_scale = gang_sykkel_dissolver_config.map_scale
        params_path = Path(__file__).parent / "parameters" / "parameters.yml"
        self.scale_parameters = initialize_params(
            params_path=params_path,
            class_name="GangSykkelDissolver",
            map_scale=self.map_scale,
            dataclass=GangSykkelDissolverParameters,
        )

    def _create_wfm_gdbs(self, wfm: WorkFileManager) -> dict:
        gangsykkel_input = wfm.build_file_path(
            file_name="gangsykkel_input", file_type="gdb"
        )
        gangsykkel_samferdsel = wfm.build_file_path(
            file_name="gangsykkel_samferdsel", file_type="gdb"
        )
        gangsykkel_samferdsel_buffer = wfm.build_file_path(
            file_name="gangsykkel_samferdsel_buffer", file_type="gdb"
        )
        gangsykkel_gangsykkel = wfm.build_file_path(
            file_name="gangsykkel_gangsykkel", file_type="gdb"
        )
        gangsykkel_gangsykkel_dissolved = wfm.build_file_path(
            file_name="gangsykkel_gangsykkel_dissolved", file_type="gdb"
        )
        gangsykkel_gangsykkel_clipped = wfm.build_file_path(
            file_name="gangsykkel_gangsykkel_clipped", file_type="gdb"
        )
        gangsykkel_gangsykkel_erased = wfm.build_file_path(
            file_name="gangsykkel_gangsykkel_erased", file_type="gdb"
        )
        gangsykkel_gangsykkel_clipped_dissolved = wfm.build_file_path(
            file_name="gangsykkel_gangsykkel_clipped_dissolved", file_type="gdb"
        )
        gangsykkel_samferdsel_gangsykkel_dissolved = wfm.build_file_path(
            file_name="gangsykkel_samferdsel_gangsykkel_dissolved", file_type="gdb"
        )
        gangsykkel_ikke_samferdsel = wfm.build_file_path(
            file_name="gangsykkel_ikke_samferdsel", file_type="gdb"
        )
        gangsykkel_gangsykkel_clipped_singlepart = wfm.build_file_path(
            file_name="gangsykkel_gangsykkel_clipped_singlepart", file_type="gdb"
        )
        gangsykkel_final_merge = wfm.build_file_path(
            file_name="gangsykkel_final_merge", file_type="gdb"
        )
        gangsykkel_final_merge_singlepart = wfm.build_file_path(
            file_name="gangsykkel_final_merge_singlepart", file_type="gdb"
        )
        gangsykkel_final_gangsykkel_dissolved = wfm.build_file_path(
            file_name="gangsykkel_final_gangsykkel_dissolved", file_type="gdb"
        )
        not_grown = wfm.build_file_path(file_name="not_grown", file_type="gdb")
        not_grown_dissolved = wfm.build_file_path(
            file_name="not_grown_dissolved", file_type="gdb"
        )

        return {
            "gangsykkel_input": gangsykkel_input,
            "gangsykkel_samferdsel": gangsykkel_samferdsel,
            "gangsykkel_samferdsel_buffer": gangsykkel_samferdsel_buffer,
            "gangsykkel_gangsykkel": gangsykkel_gangsykkel,
            "gangsykkel_gangsykkel_dissolved": gangsykkel_gangsykkel_dissolved,
            "gangsykkel_gangsykkel_clipped": gangsykkel_gangsykkel_clipped,
            "gangsykkel_gangsykkel_erased": gangsykkel_gangsykkel_erased,
            "gangsykkel_gangsykkel_clipped_dissolved": gangsykkel_gangsykkel_clipped_dissolved,
            "gangsykkel_samferdsel_gangsykkel_dissolved": gangsykkel_samferdsel_gangsykkel_dissolved,
            "gangsykkel_ikke_samferdsel": gangsykkel_ikke_samferdsel,
            "gangsykkel_gangsykkel_clipped_singlepart": gangsykkel_gangsykkel_clipped_singlepart,
            "gangsykkel_final_merge": gangsykkel_final_merge,
            "gangsykkel_final_merge_singlepart": gangsykkel_final_merge_singlepart,
            "gangsykkel_final_gangsykkel_dissolved": gangsykkel_final_gangsykkel_dissolved,
            "not_grown": not_grown,
            "not_grown_dissolved": not_grown_dissolved,
        }

    def _fetch_data(self):
        """Fetch data and create initial layers for samferdsel, gangsykkel and not samferdsel."""
        arcpy.management.CopyFeatures(
            in_features=self.input_gangsykkel,
            out_feature_class=self.files["gangsykkel_input"],
        )

        samferdsel = "layer_samferdsel"
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["gangsykkel_input"],
            out_layer=samferdsel,
            where_clause="arealdekke = 'Samferdsel' AND arealbruk_underklasse <> 'GangSykkelVeg'",
        )
        arcpy.management.CopyFeatures(
            in_features=samferdsel,
            out_feature_class=self.files["gangsykkel_samferdsel"],
        )

        gangsykkel = "layer_gangsykkel"
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["gangsykkel_input"],
            out_layer=gangsykkel,
            where_clause="arealdekke = 'Samferdsel' AND arealbruk_underklasse = 'GangSykkelVeg'",
        )
        arcpy.management.CopyFeatures(
            in_features=gangsykkel,
            out_feature_class=self.files["gangsykkel_gangsykkel"],
        )

        self._dissolve_and_restore(
            in_feature=self.files["gangsykkel_gangsykkel"],
            out_feature=self.files["gangsykkel_gangsykkel_dissolved"],
            dissolve_fields=["arealdekke", "arealbruk_underklasse", self.index_col],
            restore_source=self.files["gangsykkel_gangsykkel"],
            restore_field="arealbruk_underklasse",
            index_col=self.index_col,
        )

        ikke_samferdsel = "layer_ikke_samferdsel"
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["gangsykkel_input"],
            out_layer=ikke_samferdsel,
            where_clause="arealdekke <> 'Samferdsel'",
        )
        arcpy.management.CopyFeatures(
            in_features=ikke_samferdsel,
            out_feature_class=self.files["gangsykkel_ikke_samferdsel"],
        )

    @timing_decorator
    def _dissolve_looping(self, buffer_distance: str = "5 Meters"):
        """
        Iteratively buffer roads 5m, clip gangvei, split by length 45m and dissolve until no more dissolving is done.
        We split by length to avoid dissolving gang og sykkel polygons that connect to samferdsel but arent adjecent.
        """
        current_samferdsel = self.files["gangsykkel_samferdsel"]
        current_gangsykkel = self.files["gangsykkel_gangsykkel_dissolved"]
        final_ikke_samferdsel = self.files["gangsykkel_ikke_samferdsel"]

        prev_areas = {}
        i = 0
        dissolving = True
        while dissolving:
            i += 1

            paths = self._build_iteration_paths(i)
            current_areas = self._compute_area_by_index(
                current_samferdsel, self.index_col
            )
            grown_ids = self._get_grown_ids(prev_areas, current_areas)

            if not grown_ids:
                break

            grown_layer = f"layer_grown_{i}"
            not_grown_layer = f"layer_not_grown_{i}"
            self._create_grown_layers(
                current_samferdsel, grown_ids, grown_layer, not_grown_layer
            )

            self._create_buffer_and_clip(
                buffer_source=grown_layer,
                current_gangsykkel=current_gangsykkel,
                buffer_distance=buffer_distance,
                paths=paths,
            )

            dissolving = self._split_by_length_and_append(
                clipped_path=paths["singlepart_clipped_path"],
                grown_layer=grown_layer,
                erased_path=paths["singlepart_erased_path"],
                iteration=i,
            )

            if not arcpy.Exists(self.files["not_grown"]):
                arcpy.management.CopyFeatures(not_grown_layer, self.files["not_grown"])
            else:
                arcpy.management.Append(
                    inputs=[not_grown_layer],
                    target=self.files["not_grown"],
                )

            prev_areas = current_areas

            current_samferdsel = grown_layer
            current_gangsykkel = paths["singlepart_erased_path"]

        # after loop
        arcpy.management.Append(
            inputs=current_samferdsel,
            target=self.files["not_grown"],
        )

        self._dissolve_and_restore(
            in_feature=self.files["not_grown"],
            out_feature=self.files["not_grown_dissolved"],
            dissolve_fields=["arealdekke", self.index_col],
            restore_source=self.files["not_grown"],
            restore_field="arealdekke",
            index_col=self.index_col,
        )

        self._dissolve_and_restore(
            in_feature=current_gangsykkel,
            out_feature=self.files["gangsykkel_final_gangsykkel_dissolved"],
            dissolve_fields=["arealdekke", "arealbruk_underklasse", self.index_col],
            restore_source=self.files["gangsykkel_gangsykkel"],
            restore_field="arealbruk_underklasse",
            index_col=self.index_col,
        )

        arcpy.management.Merge(
            inputs=[
                self.files["not_grown_dissolved"],
                self.files["gangsykkel_final_gangsykkel_dissolved"],
                final_ikke_samferdsel,
            ],
            output=self.files["gangsykkel_final_merge"],
        )

        arcpy.management.MultipartToSinglepart(
            in_features=self.files["gangsykkel_final_merge"],
            out_feature_class=self.files["gangsykkel_final_merge_singlepart"],
        )

        arcpy.management.RepairGeometry(self.files["gangsykkel_final_merge_singlepart"])

        gangsykkel_final_merge_singlepart_lyr = (
            "layer_gangsykkel_final_merge_singlepart_lyr"
        )
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["gangsykkel_final_merge_singlepart"],
            out_layer=gangsykkel_final_merge_singlepart_lyr,
            where_clause=f"arealbruk_underklasse = 'GangSykkelVeg' AND Shape_Length < {self.scale_parameters.length_divide}",
        )

        arcpy.management.Eliminate(
            in_features=gangsykkel_final_merge_singlepart_lyr,
            out_feature_class=self.output_feature,
            selection="LENGTH",
        )

    def _build_iteration_paths(self, i: int) -> dict:
        """Create and return iteration-specific file paths"""
        buf_name = f"gangsykkel_samferdsel_buffer_{i}"
        clip_name = f"gangsykkel_gangsykkel_clipped_{i}"
        singlepart_clipped_name = f"gangsykkel_gangsykkel_clipped_singlepart_{i}"
        singlepart_erased_name = f"gangsykkel_gangsykkel_erased_singlepart_{i}"
        erased_name = f"gangsykkel_gangsykkel_erased_{i}"
        dissolved_name = f"gangsykkel_samferdsel_gangsykkel_dissolved_{i}"

        return {
            "buf_path": self.wfm.build_file_path(file_name=buf_name, file_type="gdb"),
            "clip_path": self.wfm.build_file_path(file_name=clip_name, file_type="gdb"),
            "singlepart_clipped_path": self.wfm.build_file_path(
                file_name=singlepart_clipped_name, file_type="gdb"
            ),
            "erased_path": self.wfm.build_file_path(
                file_name=erased_name, file_type="gdb"
            ),
            "singlepart_erased_path": self.wfm.build_file_path(
                file_name=singlepart_erased_name, file_type="gdb"
            ),
            "dissolved_path": self.wfm.build_file_path(
                file_name=dissolved_name, file_type="gdb"
            ),
        }

    def _create_grown_layers(
        self,
        current_samferdsel: str,
        grown_ids: list,
        grown_layer: str,
        not_grown_layer: str,
    ) -> str:
        """Create layers splitting the features from current_samferdsel that have grown (based on grown_ids)"""
        where_clause_in = f"{self.index_col} IN ({','.join(map(str, grown_ids))})"
        arcpy.management.MakeFeatureLayer(
            in_features=current_samferdsel,
            out_layer=grown_layer,
            where_clause=where_clause_in,
        )

        where_clause_not_in = (
            f"{self.index_col} NOT IN ({','.join(map(str, grown_ids))})"
        )
        arcpy.management.MakeFeatureLayer(
            in_features=current_samferdsel,
            out_layer=not_grown_layer,
            where_clause=where_clause_not_in,
        )

    def _create_buffer_and_clip(
        self,
        buffer_source: str,
        current_gangsykkel: str,
        buffer_distance: str,
        paths: dict,
    ) -> tuple:
        """
        Buffer samferdel, clip and erase gangsykkel, repair geometry is necassary befor and after singlepart
        """
        arcpy.analysis.Buffer(
            in_features=buffer_source,
            out_feature_class=paths["buf_path"],
            buffer_distance_or_field=buffer_distance,
        )

        arcpy.analysis.Clip(
            in_features=current_gangsykkel,
            clip_features=paths["buf_path"],
            out_feature_class=paths["clip_path"],
        )

        arcpy.management.RepairGeometry(in_features=paths["clip_path"])

        arcpy.management.MultipartToSinglepart(
            in_features=paths["clip_path"],
            out_feature_class=paths["singlepart_clipped_path"],
        )

        arcpy.management.RepairGeometry(in_features=paths["singlepart_clipped_path"])

        arcpy.analysis.Erase(
            in_features=current_gangsykkel,
            erase_features=paths["buf_path"],
            out_feature_class=paths["erased_path"],
        )

        arcpy.management.RepairGeometry(in_features=paths["erased_path"])

        arcpy.management.MultipartToSinglepart(
            in_features=paths["erased_path"],
            out_feature_class=paths["singlepart_erased_path"],
        )

        arcpy.management.RepairGeometry(in_features=paths["singlepart_erased_path"])

        return (
            paths["buf_path"],
            paths["clip_path"],
            paths["singlepart_clipped_path"],
            paths["singlepart_erased_path"],
            paths["erased_path"],
        )

    def _split_by_length_and_append(
        self,
        clipped_path: str,
        grown_layer: str,
        erased_path: str,
        iteration: int,
    ) -> bool:
        """Split clipped gang sykkel by length and append long -> samferdsel, short -> erased. if no long pieces, return False to stop dissolving loop."""
        long_layer = f"layer_gangsykkel_length_25_{iteration}"
        short_layer = f"layer_gangsykkel_length_not_25_{iteration}"
        arcpy.management.MakeFeatureLayer(
            in_features=clipped_path,
            out_layer=long_layer,
            where_clause=f'"Shape_Length" > {self.scale_parameters.length_divide}',
        )
        arcpy.management.MakeFeatureLayer(
            in_features=clipped_path,
            out_layer=short_layer,
            where_clause=f'"Shape_Length" <= {self.scale_parameters.length_divide}',
        )

        arcpy.management.Append(
            inputs=[long_layer],
            target=grown_layer,
        )
        arcpy.management.Append(
            inputs=[short_layer],
            target=erased_path,
        )

        if int(arcpy.management.GetCount(long_layer)[0]) == 0:
            return False
        else:
            return True

    def _dissolve_and_restore(
        self,
        in_feature: str,
        out_feature: str,
        dissolve_fields: list,
        restore_source: str,
        restore_field: str,
        index_col: str,
    ) -> str:
        """Dissolve a feature class and restore attributes via ArealdekkeDissolver."""
        arcpy.management.Dissolve(
            in_features=in_feature,
            out_feature_class=out_feature,
            dissolve_field=dissolve_fields,
            multi_part="SINGLE_PART",
        )

        ArealdekkeDissolver.restore_data_polygon_without_feature_to_point(
            out_feature, restore_source, restore_field, index_col, index_bool=True
        )

        return out_feature

    def _compute_area_by_index(self, feature_class: str, index_col: str) -> dict:
        """Return dict {index_value: area} for feature_class. Uses geometry area attribute."""
        # Ensure geometry area attribute exists on features (field name depends on workspace units)
        # Use a search cursor on the geometry object to compute area robustly
        areas = defaultdict(float)
        with arcpy.da.SearchCursor(feature_class, [index_col, "SHAPE@AREA"]) as cursor:
            for idx, geom_area in cursor:
                areas[idx] += geom_area
        return areas

    def _get_grown_ids(self, prev_areas: dict, current_areas: dict) -> list:
        """Return list of index_col values where current area > prev area."""
        grown = []
        for idx, cur_area in current_areas.items():
            prev_area = prev_areas.get(idx, 0.0)
            if cur_area > prev_area:
                grown.append(idx)
        return grown

    @timing_decorator
    def run(self) -> None:
        environment_setup.main()
        self._fetch_data()
        self._dissolve_looping(
            buffer_distance=f"{self.scale_parameters.buffer_distance} Meters"
        )
        self.wfm.delete_created_files()


def partition_call(input_fc: str, output_fc: str, map_scale: str):
    gangsykkel = "gangsykkel"
    dissolved_gangsykkel = "dissolved_gangsykkel"
    partition_input_config = core_config.PartitionInputConfig(
        entries=[
            core_config.InputEntry.processing_input(
                object=gangsykkel,
                path=input_fc,
            )
        ]
    )

    partition_output_config = core_config.PartitionOutputConfig(
        entries=[
            core_config.OutputEntry.vector_output(
                object=gangsykkel,
                tag=dissolved_gangsykkel,
                path=output_fc,
            )
        ]
    )

    partiton_area_io_config = core_config.PartitionIOConfig(
        input_config=partition_input_config,
        output_config=partition_output_config,
        documentation_directory=Arealdekke_N10.areal_dissolve_documentation.value,
    )

    # Method Config:

    partiton_input = core_config.InjectIO(object=gangsykkel, tag="input")
    partition_output = core_config.InjectIO(object=gangsykkel, tag=dissolved_gangsykkel)

    gangsykkel_init_config = logic_config.GangSykkelDissolverInitKwargs(
        input_feature=partiton_input,
        output_feature=partition_output,
        index_column_name="FID_Fishnet_500m",
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Arealdekke_N10.dissolve_arealdekke_root.value
        ),
        map_scale=map_scale,
    )
    arealdekke_method = core_config.ClassMethodEntryConfig(
        class_=GangSykkelDissolver,
        method=GangSykkelDissolver.run,
        init_params=gangsykkel_init_config,
    )
    partition_method_config = core_config.MethodEntriesConfig(
        entries=[arealdekke_method]
    )

    # Run Config:
    partiton_run_config = core_config.PartitionRunConfig(
        max_elements_per_partition=50_000,
        context_radius_meters=0,
        run_partition_optimization=False,
    )

    # WorkFileConfig:
    partiton_workfile_config = core_config.WorkFileConfig(
        root_file=Arealdekke_N10.dissolve_arealdekke_partition_root.value
    )

    # PartitionIterator Config:
    partition_gangsykkel_dissolve = PartitionIterator(
        partition_io_config=partiton_area_io_config,
        partition_method_inject_config=partition_method_config,
        partition_iterator_run_config=partiton_run_config,
        work_file_manager_config=partiton_workfile_config,
    )

    partition_gangsykkel_dissolve.run()


if __name__ == "__main__":
    partition_call(
        input_fc=Arealdekke_N10.elim_output.value,
        output_fc=Arealdekke_N10.dissolve_gangsykkel.value,
        map_scale="N10",
    )
