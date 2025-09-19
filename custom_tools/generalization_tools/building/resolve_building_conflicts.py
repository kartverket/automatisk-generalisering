# Importing modules
from dataclasses import dataclass
import arcpy

from typing import (
    Dict,
    List,
    Optional,
    Iterable,
    Union,
    Set,
    Any,
    Callable,
    Mapping,
    Sequence,
)

# Importing custom files
import config
from composition_configs import core_config
import constants.n100_constants
from custom_tools.general_tools import custom_arcpy
from input_data import input_n100
from typing import Union, List, Dict, Tuple
import input_data.input_n50
import input_data.input_n100

from input_data.input_symbology import SymbologyN100
from file_manager.n100.file_manager_buildings import Building_N100
from file_manager.base_file_manager import BaseFileManager

from file_manager import WorkFileManager
from composition_configs import logic_config
from constants.n100_constants import N100_Symbology, N100_Values
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from env_setup import environment_setup
from input_data import input_symbology

# Importing timing decorator

from custom_tools.decorators.partition_io_decorator import partition_io_decorator


@dataclass
class _RbcRecord:
    spec: logic_config.SymbologyLayerSpec
    feature_copy: str
    lyrx_output: str


def build_barrier_rules(
    specs: List[logic_config.SymbologyLayerSpec],
    building_names: Union[str, Iterable[str]],
    default: logic_config.BarrierDefault,
    overrides: Optional[List[logic_config.BarrierRule]] = None,
) -> List[logic_config.BarrierRule]:
    """
    Build barrier rules for all specs that are *not* buildings.

    - `building_names` can be a single name or an iterable of names.
    - `overrides` must reference existing non-building spec names and be unique per name.
    - Output preserves the order of `specs`.
    """
    if isinstance(building_names, str):
        building_set: Set[str] = {building_names}
    else:
        building_set = set(building_names)

    spec_names = {s.unique_name for s in specs}

    missing = building_set - spec_names
    if missing:
        raise ValueError(f"Building spec(s) missing: {sorted(missing)}")

    override_index: dict[str, logic_config.BarrierRule] = {}
    if overrides:
        for r in overrides:
            if r.name in override_index:
                raise ValueError(f"Duplicate barrier override for '{r.name}'.")
            override_index[r.name] = r

        bad = [n for n in override_index if n not in spec_names or n in building_set]
        if bad:
            raise ValueError(
                f"Barrier overrides refer to unknown or non-barrier names: {bad}"
            )

    rules_out: List[logic_config.BarrierRule] = []
    for s in specs:
        if s.unique_name in building_set:
            continue
        rules_out.append(
            override_index.get(s.unique_name)
            or logic_config.BarrierRule(
                name=s.unique_name,
                gap_meters=default.gap_meters,
                use_turn_orientation=default.use_turn_orientation,
            )
        )
    return rules_out


class ResolveBuildingConflictsPoints:
    """

    What:
        This class handles the resolution of building conflicts based on specified symbology, gap distances,
        and input barriers. The workflow involves multiple steps, including symbology application, conflict resolution,
        and transformation of invisible building polygons to squares for further analysis.

    How:
        Symbology Application: This function applies symbology to layers such as building points,
        building polygons, and barriers to standardize visualization and prepare for conflict resolution.

        Conflict Resolution (RBC Stages): Building conflicts are resolved in two stages.

        RBC 1: This stage processes building polygons and squares, resolving conflicts with respect
        to road and rail barriers.

        RBC 2: This stage refines the results from RBC 1, adjusting for any unresolved conflicts.

        Invisible Polygons: Any invisible polygons resulting from the conflict resolution process
        are transformed into points and then converted to squares, ensuring that all relevant features
        are considered in further analysis.

    Why:
        Resolve building conflicts for a cleaner map look.

    Args:
        building_inputs (Dict[str, str]):
            Dictionary containing paths to building points and polygons.
        building_gap_distance (int):
            The gap distance (in meters) used for resolving building conflicts.
        barrier_inputs (Dict[str, str]):
            Dictionary containing paths to various barrier inputs such as roads and railways.
        barrier_gap_distances (Dict[str, int]):
            Dictionary containing gap distances for each barrier type (e.g., road, railway).
        building_symbol_dimension (Dict[int, tuple]):
            Dictionary mapping building symbols to their respective dimensions.
        lyrx_files (Dict[str, str]):
            Dictionary containing paths to lyrx files used for applying symbology to the features.
        base_path_for_lyrx (str):
            The base path for storing lyrx files for the processing workflow.
        base_path_for_features (str):
            The base path for storing feature files during processing.
        output_files (Dict[str, str]):
            Dictionary containing paths for storing the final output of  building points and polygons.
        write_work_files_to_memory (bool, optional):
            If True, work files are written to memory during the process. Default is False.
        keep_work_files (bool, optional):
            If True, work files are retained after processing is complete. Default is False.
    """

    def __init__(
        self,
        rbc_input_config: logic_config.RbcPointsInitKwargs,
    ):
        self.output_points = rbc_input_config.output_points_after_rbc
        self.output_polygons = rbc_input_config.output_polygons_after_rbc
        self.barrier_default = rbc_input_config.barrier_default
        self.barrier_overrides = rbc_input_config.barrier_overrides
        self.building_gap_distance_m = rbc_input_config.building_gap_distance_m
        self.map_scale = rbc_input_config.map_scale

        self.building_polygons_unique_name = (
            rbc_input_config.building_polygons_unique_name
        )
        self.building_points_unique_name = rbc_input_config.building_points_unique_name
        self.building_symbol_dimension = rbc_input_config.building_symbol_dimension

        self.specs: List[logic_config.SymbologyLayerSpec] = (
            rbc_input_config.input_data_structure
        )
        names = {s.unique_name for s in self.specs}
        missing = {
            rbc_input_config.building_points_unique_name,
            rbc_input_config.building_polygons_unique_name,
        } - names
        if missing:
            raise ValueError(f"Building spec(s) missing: {sorted(missing)}")

        self.wfm = WorkFileManager(config=rbc_input_config.work_file_manager_config)

        records: List[_RbcRecord] = []
        for s in self.specs:
            feature_copy = self.wfm.build_file_path(
                file_name=f"{s.unique_name}_feature_copy", file_type="gdb"
            )
            lyrx_output = self.wfm.build_file_path(
                f"{s.unique_name}_lyrx_output", "lyrx"
            )
            records.append(
                _RbcRecord(spec=s, feature_copy=feature_copy, lyrx_output=lyrx_output)
            )
        self.records = records
        self._index = {r.spec.unique_name: r for r in self.records}

        self.results_rbc1_squares = self.wfm.build_file_path(
            file_name="results_rbc1_squares", file_type="gdb"
        )
        self.results_rbc1_polygons = self.wfm.build_file_path(
            file_name="results_rbc1_polygons", file_type="gdb"
        )
        self.invisible_polygons = self.wfm.build_file_path(
            file_name="invisible_polygons_after_rbc1", file_type="gdb"
        )
        self.invisible_to_points = self.wfm.build_file_path(
            file_name="invisible_polygons_to_points_after_rbc1", file_type="gdb"
        )
        self.polygons_to_points_to_squares = self.wfm.build_file_path(
            file_name="polygons_to_points_to_squares_rbc1", file_type="gdb"
        )
        self.merged_squares_rbc1 = self.wfm.build_file_path(
            file_name="merged_squares_rbc1", file_type="gdb"
        )
        self.squares_into_rbc2_lyrx = self.wfm.build_file_path(
            file_name="squares_into_rbc2", file_type="lyrx"
        )
        self.polygons_into_rbc2_lyrx = self.wfm.build_file_path(
            file_name="polygons_into_rbc2", file_type="lyrx"
        )

    def _by_name(self, name: str) -> _RbcRecord:
        for r in self.records:
            if r.spec.unique_name == name:
                return r
        raise KeyError(f"Layer '{name}' not found.")

    def _rbc(
        self,
        buildings_lyrx: list[str],
        barrier_rules: List[logic_config.BarrierRule],
        building_gap_m: int,
        hierarchy_field: Optional[str] = None,
    ):
        barriers = [
            [
                self._by_name(r.name).lyrx_output,
                str(r.use_turn_orientation).lower(),
                f"{r.gap_meters} Meters",
            ]
            for r in barrier_rules
        ]
        arcpy.cartography.ResolveBuildingConflicts(
            in_buildings=buildings_lyrx,
            invisibility_field="invisibility",
            in_barriers=barriers,
            building_gap=f"{building_gap_m} Meters",
            minimum_size="1 Meters",
            hierarchy_field=hierarchy_field,
        )

    def _apply_symbology(self) -> None:
        for r in self.records:
            arcpy.management.CopyFeatures(
                in_features=r.spec.input_feature,
                out_feature_class=r.feature_copy,
            )
            if r.spec.grouped_lyrx:
                custom_arcpy.apply_symbology(
                    input_layer=r.feature_copy,
                    in_symbology_layer=r.spec.input_lyrx,
                    output_name=r.lyrx_output,
                    grouped_lyrx=True,
                    target_layer_name=r.spec.target_layer_name,
                )
            else:
                custom_arcpy.apply_symbology(
                    input_layer=r.feature_copy,
                    in_symbology_layer=r.spec.input_lyrx,
                    output_name=r.lyrx_output,
                )

    def resolve_building_conflicts_stage1(self):
        poly = self._by_name(self.building_polygons_unique_name)
        pts = self._by_name(self.building_points_unique_name)

        rules = build_barrier_rules(
            specs=self.specs,
            building_names={
                self.building_polygons_unique_name,
                self.building_points_unique_name,
            },
            default=self.barrier_default,
            overrides=self.barrier_overrides,
        )

        self._rbc(
            buildings_lyrx=[poly.lyrx_output, pts.lyrx_output],
            barrier_rules=rules,
            building_gap_m=self.building_gap_distance_m,
            hierarchy_field="hierarchy",
        )

    def select_visible_after_rbc1(self):
        # Squares (points kept or special symbols)
        sql_squares = (
            "(invisibility = 0) OR (symbol_val IN (1, 2, 3)) OR (byggtyp_nbr = 956)"
        )
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self._by_name(self.building_points_unique_name).feature_copy,
            expression=sql_squares,
            output_name=self.results_rbc1_squares,
        )
        # Polygons (visible only)
        sql_polys = "invisibility = 0"
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self._by_name(self.building_polygons_unique_name).feature_copy,
            expression=sql_polys,
            output_name=self.results_rbc1_polygons,
        )

    def transform_invisible_polygons_to_squares(self):
        # Pick polygons with invisibility = 1
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self._by_name(self.building_polygons_unique_name).feature_copy,
            expression="invisibility = 1",
            output_name=self.invisible_polygons,
        )
        # Polygons -> points
        arcpy.management.FeatureToPoint(
            in_features=self.invisible_polygons,
            out_feature_class=self.invisible_to_points,
            point_location="INSIDE",
        )
        # Points -> squares via PolygonProcessor
        PolygonProcessor(
            input_building_points=self.invisible_to_points,
            output_polygon_feature_class=self.polygons_to_points_to_squares,
            building_symbol_dimensions=self.building_symbol_dimension,
            symbol_field_name="symbol_val",
            index_field_name="OBJECTID",
        ).run()

        # Merge squares from (kept points) + (polygons→points→squares)
        arcpy.management.Merge(
            inputs=[self.results_rbc1_squares, self.polygons_to_points_to_squares],
            output=self.merged_squares_rbc1,
        )

    def normalize_symbol_fields(self):
        # same two CalculateField calls you already have
        code_block_val_to_nbr = (
            "def symbol_val_to_nbr(symbol_val, byggtyp_nbr):\n"
            "    if symbol_val == -99:\n"
            "        return 729\n"
            "    return byggtyp_nbr"
        )
        arcpy.CalculateField_management(
            in_table=self.merged_squares_rbc1,
            field="byggtyp_nbr",
            expression="symbol_val_to_nbr(!symbol_val!, !byggtyp_nbr!)",
            expression_type="PYTHON3",
            code_block=code_block_val_to_nbr,
        )
        code_block_update_val = (
            "def update_symbol_val(symbol_val):\n"
            "    if symbol_val == -99:\n"
            "        return 8\n"
            "    return symbol_val"
        )
        arcpy.CalculateField_management(
            in_table=self.merged_squares_rbc1,
            field="symbol_val",
            expression="update_symbol_val(!symbol_val!)",
            expression_type="PYTHON3",
            code_block=code_block_update_val,
        )

    def apply_symbology_for_rbc2_inputs(self):
        # Squares into RBC2
        custom_arcpy.apply_symbology(
            input_layer=self.merged_squares_rbc1,
            in_symbology_layer=self._by_name(
                self.building_points_unique_name
            ).spec.input_lyrx,
            output_name=self.squares_into_rbc2_lyrx,
        )
        # Polygons into RBC2
        custom_arcpy.apply_symbology(
            input_layer=self.results_rbc1_polygons,
            in_symbology_layer=self._by_name(
                self.building_polygons_unique_name
            ).spec.input_lyrx,
            output_name=self.polygons_into_rbc2_lyrx,
        )

    def resolve_building_conflicts_stage2(self):
        # Same barriers/rules as RBC1 (unless you want separate defaults/overrides)
        rules = build_barrier_rules(
            specs=self.specs,
            building_names={
                self.building_polygons_unique_name,
                self.building_points_unique_name,
            },
            default=self.barrier_default,
            overrides=self.barrier_overrides,
        )
        self._rbc(
            buildings_lyrx=[self.squares_into_rbc2_lyrx, self.polygons_into_rbc2_lyrx],
            barrier_rules=rules,
            building_gap_m=self.building_gap_distance_m,
            hierarchy_field="hierarchy",
        )

    def export_final_outputs(self):
        # squares -> points
        squares_back_to_points = self.wfm.build_file_path(
            file_name="squares_back_to_points_after_rbc2", file_type="gdb"
        )
        arcpy.management.FeatureToPoint(
            in_features=self.merged_squares_rbc1,
            out_feature_class=squares_back_to_points,
            point_location="INSIDE",
        )
        arcpy.management.CopyFeatures(squares_back_to_points, self.output_points)
        arcpy.management.CopyFeatures(self.results_rbc1_polygons, self.output_polygons)

    def run(self):
        arcpy.env.referenceScale = self.map_scale
        environment_setup.main()

        self._apply_symbology()

        # stage 1
        self.resolve_building_conflicts_stage1()
        self.select_visible_after_rbc1()
        self.transform_invisible_polygons_to_squares()
        self.normalize_symbol_fields()

        # stage 2
        self.apply_symbology_for_rbc2_inputs()
        self.resolve_building_conflicts_stage2()

        # outputs
        self.export_final_outputs()
        self.wfm.delete_created_files()


class ResolveBuildingConflictsPolygon:
    def __init__(
        self,
        rbc_polygon_config: logic_config.RbcPolygonInitKwargs,
    ):
        self.barrier_default = rbc_polygon_config.barrier_default
        self.barrier_overrides = rbc_polygon_config.barrier_overrides

        self.output_building_polygons = rbc_polygon_config.output_building_polygons
        self.output_building_points = rbc_polygon_config.output_collapsed_polygon_points

        self.building_name = rbc_polygon_config.building_unique_name

        self.work_file_manager = WorkFileManager(
            config=rbc_polygon_config.work_file_manager_config
        )

        self.specs: List[logic_config.SymbologyLayerSpec] = (
            rbc_polygon_config.input_data_structure
        )

        if self.building_name not in {s.unique_name for s in self.specs}:
            raise ValueError(
                f"Building layer '{self.building_name}' not found in specs."
            )

        records: List[_RbcRecord] = []
        for s in self.specs:
            feature_copy = self.work_file_manager.build_file_path(
                file_name=f"{s.unique_name}_feature_copy", file_type="gdb"
            )
            lyrx_output = self.work_file_manager.build_file_path(
                file_name=f"{s.unique_name}_lyrx_output", file_type="lyrx"
            )
            records.append(
                _RbcRecord(spec=s, feature_copy=feature_copy, lyrx_output=lyrx_output)
            )
        self.records = records
        self._index = {r.spec.unique_name: r for r in self.records}

        self.building_polygon_rbc_output = "building_polygon_rbc_output"
        self.invisible_polygons = "invisible_polygons"
        self.feature_to_points = "feature_to_points"

        self.gdb_files_list = [
            self.building_polygon_rbc_output,
            self.invisible_polygons,
            self.feature_to_points,
        ]

        self.gdb_files_list = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.gdb_files_list,
        )

    def copy_input_layers(self):
        for r in self.records:
            arcpy.management.CopyFeatures(
                in_features=r.spec.input_feature,
                out_feature_class=r.feature_copy,
            )

    def apply_symbology(self):
        for record in self.records:
            if record.spec.grouped_lyrx:
                custom_arcpy.apply_symbology(
                    input_layer=record.feature_copy,
                    in_symbology_layer=record.spec.input_lyrx,
                    output_name=record.lyrx_output,
                    grouped_lyrx=True,
                    target_layer_name=record.spec.target_layer_name,
                )
            else:
                custom_arcpy.apply_symbology(
                    input_layer=record.feature_copy,
                    in_symbology_layer=record.spec.input_lyrx,
                    output_name=record.lyrx_output,
                )

    def _by_name(self, name: str) -> _RbcRecord:
        for r in self.records:
            if r.spec.unique_name == name:
                return r
        raise KeyError(f"Layer '{name}' not found.")

    def resolve_building_conflicts(self):
        building = self._by_name(self.building_name)

        # If no explicit rules: all non-building specs become barriers with defaults
        rules = build_barrier_rules(
            specs=self.specs,
            building_names=self.building_name,
            default=self.barrier_default,
            overrides=self.barrier_overrides,
        )

        resolved_barriers = [
            [
                self._by_name(r.name).lyrx_output,
                str(r.use_turn_orientation).lower(),
                f"{r.gap_meters} Meters",
            ]
            for r in rules
        ]

        arcpy.cartography.ResolveBuildingConflicts(
            in_buildings=building.lyrx_output,
            invisibility_field="invisibility",
            in_barriers=resolved_barriers,
            building_gap=f"{N100_Values.rbc_building_clearance_distance_m.value} Meters",
            minimum_size="1 meters",
        )

        arcpy.management.Copy(
            in_data=building.feature_copy,
            out_data=self.building_polygon_rbc_output,
        )

    def invisibility_selections(self):

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.building_polygon_rbc_output,
            expression="invisibility = 1",
            output_name=self.invisible_polygons,
        )

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.building_polygon_rbc_output,
            expression="invisibility = 0",
            output_name=self.output_building_polygons,
        )

        arcpy.management.FeatureToPoint(
            in_features=self.invisible_polygons,
            out_feature_class=self.feature_to_points,
        )

        arcpy.management.Copy(
            in_data=self.feature_to_points,
            out_data=self.output_building_points,
        )

    def run(self):
        arcpy.env.referenceScale = "100000"
        environment_setup.main()
        self.copy_input_layers()
        self.apply_symbology()
        self.resolve_building_conflicts()
        self.invisibility_selections()


if __name__ == "__main__":
    input_data_structure = [
        {
            "unique_alias": "building_points",
            "input_feature": Building_N100.point_displacement_with_buffer___merged_buffer_displaced_points___n100_building.value,
            "lyrx_file": input_symbology.SymbologyN100.squares.value,
            "grouped_lyrx": False,
            "target_layer_name": "",
        },
        {
            "unique_alias": "building_polygons",
            "input_feature": Building_N100.polygon_resolve_building_conflicts___building_polygons_final___n100_building.value,
            "lyrx_file": input_symbology.SymbologyN100.building_polygon.value,
            "grouped_lyrx": False,
            "target_layer_name": "",
        },
        {
            "unique_alias": "road",
            "input_feature": Building_N100.data_preparation___unsplit_roads___n100_building.value,
            "lyrx_file": config.symbology_samferdsel,
            "grouped_lyrx": True,
            "target_layer_name": "N100_Samferdsel_senterlinje_veg_bru_L2",
        },
        {
            "unique_alias": "railroad",
            "input_feature": input_data.input_n100.Bane,
            "lyrx_file": config.symbology_samferdsel,
            "grouped_lyrx": True,
            "target_layer_name": "N100_Samferdsel_senterlinje_jernbane_terreng_sort_maske",
        },
        {
            "unique_alias": "railroad_station",
            "input_feature": Building_N100.data_preparation___railway_stations_to_polygons___n100_building.value,
            "lyrx_file": input_symbology.SymbologyN100.railway_station_squares.value,
            "grouped_lyrx": False,
            "target_layer_name": "",
        },
        {
            "unique_alias": "begrensningskurve",
            "input_feature": Building_N100.data_preparation___begrensningskurve_buffer_erase_2___n100_building.value,
            "lyrx_file": input_symbology.SymbologyN100.begrensningskurve_polygon.value,
            "grouped_lyrx": False,
            "target_layer_name": "",
        },
        {
            "unique_alias": "power_grid_lines",
            "input_feature": Building_N100.data_preparation___power_grid_lines___n100_building.value,
            "lyrx_file": config.symbology_samferdsel,
            "grouped_lyrx": True,
            "target_layer_name": "AnleggsLinje_maske_sort",
        },
    ]

    resolve_building_conflicts = ResolveBuildingConflictsPoints(
        input_list_of_dicts_data_structure=input_data_structure,
        building_inputs={
            "building_points": Building_N100.point_displacement_with_buffer___merged_buffer_displaced_points___n100_building.value,
            "building_polygons": Building_N100.polygon_resolve_building_conflicts___building_polygons_final___n100_building.value,
        },
        building_gap_distance=30,
        barrier_inputs={
            "begrensningskurve": Building_N100.data_preparation___begrensningskurve_buffer_erase_2___n100_building.value,
            "road": Building_N100.data_preparation___unsplit_roads___n100_building.value,
            "railway_station": Building_N100.data_preparation___railway_stations_to_polygons___n100_building.value,
            "railway": input_data.input_n100.Bane,
        },
        barrier_gap_distances={
            "begrensningskurve": 45,
            "road": 45,
            "railway_station": 45,
            "railway": 45,
        },
        building_symbol_dimension=N100_Symbology.building_symbol_dimensions.value,
        lyrx_files={
            "building_squares": input_symbology.SymbologyN100.squares.value,
            "building_polygons": input_symbology.SymbologyN100.building_polygon.value,
            "begrensningskurve": input_symbology.SymbologyN100.begrensningskurve_polygon.value,
            "road": input_symbology.SymbologyN100.road.value,
            "railway_station": input_symbology.SymbologyN100.railway_station_squares.value,
            "railway": input_symbology.SymbologyN100.railway.value,
        },
        base_path_for_lyrx=Building_N100.point_resolve_building_conflicts___lyrx_root___n100_building.value,
        root_path=Building_N100.point_resolve_building_conflicts___root_path___n100_building.value,
        output_files={
            "building_points": Building_N100.point_resolve_building_conflicts___POINT_OUTPUT___n100_building.value,
            "building_polygons": Building_N100.point_resolve_building_conflicts___POLYGON_OUTPUT___n100_building.value,
        },
        map_scale="100000",
    )

    resolve_building_conflicts.run()
    # resolve_building_conflicts.barriers_for_rbc()
