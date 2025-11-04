import arcpy
from typing import List, Dict
from dataclasses import dataclass

from file_manager import WorkFileManager
from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy
from custom_tools.decorators.partition_io_decorator import partition_io_decorator
from file_manager.n100.file_manager_roads import Road_N100
from file_manager.n100.file_manager_buildings import Building_N100
import config
from input_data.input_symbology import SymbologyN100
from composition_configs import core_config, logic_config


@dataclass
class _RrcRecord:
    spec: logic_config.SymbologyLayerSpec
    line_copy: str
    lyrx_output: str


class ResolveRoadConflicts:
    def __init__(self, resolve_road_config: logic_config.RrcInitKwargs):
        self.cfg = resolve_road_config
        self.wfm = WorkFileManager(config=resolve_road_config.work_file_manager_config)

        self.specs: List[logic_config.SymbologyLayerSpec] = (
            resolve_road_config.input_data_structure
        )
        names = {s.unique_name for s in self.specs}
        if resolve_road_config.primary_road_unique_name not in names:
            raise ValueError(
                f"Primary road layer '{resolve_road_config.primary_road_unique_name}' not found in specs."
            )

        # Build per-spec work paths
        records: List[_RrcRecord] = []
        for s in self.specs:
            line_copy = self.wfm.build_file_path(f"{s.unique_name}_line_copy", "gdb")
            lyrx_output = self.wfm.build_file_path(
                f"{s.unique_name}_lyrx_output", "lyrx"
            )
            records.append(
                _RrcRecord(spec=s, line_copy=line_copy, lyrx_output=lyrx_output)
            )
        self.records = records
        self._index = {r.spec.unique_name: r for r in self.records}

        # Working GDB artifacts
        self.displacement_feature = self.wfm.build_file_path(
            "displacement_feature", "gdb"
        )
        self.displacement_feature_selection = self.wfm.build_file_path(
            "displacement_feature_selection", "gdb"
        )
        self.displacement_spatial_join = self.wfm.build_file_path(
            "displacement_spatial_join", "gdb"
        )

        # Outputs
        self.output_road_feature = resolve_road_config.output_road_feature
        self.output_displacement_feature = (
            resolve_road_config.output_displacement_feature
        )

    def _by_name(self, name: str) -> _RrcRecord:
        try:
            return self._index[name]
        except KeyError:
            # keep the nice message, hide the original KeyError context
            raise KeyError(f"Layer '{name}' not found.") from None

    def copy_input_layers(self) -> None:
        for r in self.records:
            arcpy.management.CopyFeatures(
                in_features=r.spec.input_feature,
                out_feature_class=r.line_copy,
            )

    def apply_symbology(self) -> None:
        for r in self.records:
            if r.spec.grouped_lyrx:
                custom_arcpy.apply_symbology(
                    input_layer=r.line_copy,
                    in_symbology_layer=r.spec.input_lyrx,
                    output_name=r.lyrx_output,
                    grouped_lyrx=True,
                    target_layer_name=r.spec.target_layer_name,
                )
            else:
                custom_arcpy.apply_symbology(
                    input_layer=r.line_copy,
                    in_symbology_layer=r.spec.input_lyrx,
                    output_name=r.lyrx_output,
                )

    def resolve_road_conflicts(self) -> None:
        in_layers = [r.lyrx_output for r in self.records]

        arcpy.cartography.ResolveRoadConflicts(
            in_layers=in_layers,
            hierarchy_field=self.cfg.hierarchy_field,
            out_displacement_features=self.displacement_feature,
        )

        # Export the primary road layer after conflict resolution.
        main = self._by_name(self.cfg.primary_road_unique_name)
        arcpy.management.CopyFeatures(
            in_features=main.lyrx_output,
            out_feature_class=self.output_road_feature,
        )

    def displacement_feature_processing(self) -> None:
        # Select displacement features intersecting the final road output
        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=self.displacement_feature,
            overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
            select_features=self.output_road_feature,
            output_name=self.displacement_feature_selection,
        )

        # Spatial join for attribution
        arcpy.analysis.SpatialJoin(
            target_features=self.displacement_feature_selection,
            join_features=self.output_road_feature,
            out_feature_class=self.displacement_spatial_join,
            join_operation="JOIN_ONE_TO_MANY",
            match_option="INTERSECT",
        )

        # Final displacement output
        arcpy.management.CopyFeatures(
            in_features=self.displacement_spatial_join,
            out_feature_class=self.output_displacement_feature,
        )

    def run(self) -> None:
        arcpy.env.referenceScale = self.cfg.map_scale
        environment_setup.main()

        self.copy_input_layers()
        self.apply_symbology()
        self.resolve_road_conflicts()
        self.displacement_feature_processing()

        self.wfm.delete_created_files()


if __name__ == "__main__":
    environment_setup.main()
