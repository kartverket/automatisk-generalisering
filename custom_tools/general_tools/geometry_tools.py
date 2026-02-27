from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import atan2, degrees
from typing import Optional, Union, Dict

import arcpy

from composition_configs.logic_config import AngleToolConfig, LineAngleMode

from xarray.backends.common import NONE_VAR_NAME

from custom_tools.general_tools import custom_arcpy
from custom_tools.decorators.partition_io_decorator import partition_io_decorator
from file_manager.n100.file_manager_rivers import River_N100


class RemovePolygonIslands:
    def __init__(self, input_feature_class):
        self.input_feature_class = input_feature_class
        self.output_feature_class = f"{input_feature_class}_clean"

    def remove_islands(self):
        custom_arcpy.remove_islands(self.input_feature_class, self.output_feature_class)


def remove_polygon_islands(output_feature_class):
    input_feature_class = (
        River_N100.centerline_pruning_loop__water_features_processed__n100.value
    )

    dissolve_output = f"{input_feature_class}_dissolved"
    arcpy.analysis.PairwiseDissolve(
        in_features=input_feature_class,
        out_feature_class=dissolve_output,
        dissolve_field=["shape_Length", "shape_Area"],
        multi_part="MULTI_PART",
    )

    eliminate_polygon_part_output = f"{output_feature_class}_eliminate_polygon_part"

    arcpy.management.EliminatePolygonPart(
        in_features=dissolve_output,
        out_feature_class=eliminate_polygon_part_output,
        condition="PERCENT",
        part_area_percent="99",
        part_option="CONTAINED_ONLY",
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=eliminate_polygon_part_output,
        overlap_type=custom_arcpy.OverlapType.HAVE_THEIR_CENTER_IN.value,
        select_features=River_N100.centerline_pruning_loop__complex_water_features__n100.value,
        output_name=River_N100.centerline_pruning_loop__complex_centerlines__n100.value,
    )


class GeometryValidator:
    def __init__(
        self,
        input_features: Union[Dict[str, str], str],
        output_table_path: str,
    ):
        self.input_features = input_features
        self.output_table_path = output_table_path
        self.generated_out_table_path = None
        self.problematic_features = {}
        self.non_problematic_features = {}
        self.iteration = 0

    def check_geometry(self):
        """Check the geometry of the input features."""
        self.problematic_features.clear()

        if isinstance(self.input_features, dict):
            for alias, path in self.input_features.items():
                # Skip if this feature was previously validated as non-problematic
                if alias in self.non_problematic_features:
                    continue

                self.generated_out_table_path = (
                    f"{self.output_table_path}_{alias}_validation_{self.iteration}"
                )
                result = arcpy.management.CheckGeometry(
                    in_features=path, out_table=self.generated_out_table_path
                )
                problems_found = result[1] == "true"
                if problems_found:
                    self.problematic_features[alias] = path
                    print(f"Geometry issues found in feature: {alias}")
                else:
                    self.non_problematic_features[alias] = path
                    print(f"No geometry issues found in feature: {alias}")
        elif isinstance(self.input_features, str):
            if self.input_features in self.non_problematic_features:
                print(
                    f"Feature {self.input_features} previously validated as non-problematic, skipping."
                )
                return

            self.generated_out_table_path = (
                f"{self.output_table_path}_iter{self.iteration}"
            )
            result = arcpy.management.CheckGeometry(
                in_features=self.input_features, out_table=self.generated_out_table_path
            )
            problems_found = result[1] == "true"
            if problems_found:
                self.problematic_features[self.input_features] = self.input_features
                print(f"Geometry issues found in feature: {self.input_features}")
            else:
                self.non_problematic_features[self.input_features] = self.input_features
                print(f"No geometry issues found in feature: {self.input_features}")
        else:
            raise TypeError("input_features must be either a dictionary or a string.")

    def repair_geometry(self, delete_null="DELETE_NULL", validation_method="ESRI"):
        """Repair the geometry of the features identified with issues."""
        if not self.problematic_features:
            print("No problematic features to repair.")
            return

        for alias, path in self.problematic_features.items():
            arcpy.management.RepairGeometry(
                in_features=path,
                delete_null=delete_null,
                validation_method=validation_method,
            )
            print(f"Repaired geometry for feature: {alias}")

    @partition_io_decorator(
        input_param_names=["input_features"],
        output_param_names=None,
    )
    def check_repair_sequence(self, max_iterations=2):
        """Run the check-repair-check sequence until no issues remain or max iterations reached."""
        self.iteration = 0
        while self.iteration < max_iterations:
            print(f"--- Iteration {self.iteration + 1} ---")
            self.check_geometry()
            if not self.problematic_features:
                print("No further geometry issues detected.")
                break
            self.repair_geometry()
            self.iteration += 1

        if self.iteration == max_iterations:
            problematic_aliases = ", ".join(self.problematic_features.keys())
            print(
                f"Maximum iterations ({max_iterations}) reached. Manual inspection may be required for the following features: {problematic_aliases}"
            )


class _ConcreteLineAngleMode(str, Enum):
    WHOLE_LINE = "whole_line"
    START_SEGMENT = "start_segment"
    END_SEGMENT = "end_segment"
    START_TO_MIDPOINT = "start_to_midpoint"
    END_TO_MIDPOINT = "end_to_midpoint"


@dataclass(frozen=True)
class _RowAngleResult:
    angles_by_mode: dict[_ConcreteLineAngleMode, Optional[float]]
    issues: tuple[str, ...]
    is_supported: bool


class LineAngleTool:
    """
    Calculate line-angle measurements for requested modes and optionally
    write them to fields on an output feature class.

    Angle convention:
        - Range: [0, 360)
        - Zero direction: positive X axis (east)
        - Positive rotation: counterclockwise

    Important:
        - WHOLE_LINE always means canonical start -> end direction.
        - BOTH_ENDPOINT_SEGMENTS is a request convenience selector only.
          It expands to START_SEGMENT and END_SEGMENT and is never stored
          as its own output value.
    """

    def __init__(self, config: AngleToolConfig):
        self.config = config
        self.resolved_modes = self._resolve_requested_modes()
        self.field_name_by_mode = self._build_field_name_by_mode()
        self.issue_counts: dict[str, int] = {}

    def run(self) -> Optional[dict[int, dict]]:
        """
        Main entrypoint.

        Returns:
            A dict keyed by object id of the dataset actually processed:
            - input OID for return-only mode
            - output OID when write_fields=True and output_lines is used

            Or None when return_results=False.
        """
        self._validate_config()

        lines_fc = self._prepare_processing_feature_class()

        if self.config.write_fields:
            self._ensure_output_fields(lines_fc=lines_fc)

        results_by_oid: dict[int, dict] = {}

        field_names = ["OID@", "SHAPE@"]
        if self.config.write_fields:
            ordered_angle_fields = [
                self.field_name_by_mode[mode] for mode in self.resolved_modes
            ]
            field_names.extend(ordered_angle_fields)

            with arcpy.da.UpdateCursor(lines_fc, field_names) as cursor:
                for row in cursor:
                    oid = row[0]
                    polyline = row[1]

                    row_result = self._calculate_row_angles(polyline=polyline)
                    self._track_issues(row_result.issues)

                    self._write_row_values_to_cursor_row(
                        row=row,
                        row_result=row_result,
                    )
                    cursor.updateRow(row)

                    if self.config.return_results:
                        results_by_oid[oid] = self._serialize_row_result(row_result)

        else:
            with arcpy.da.SearchCursor(lines_fc, field_names) as cursor:
                for oid, polyline in cursor:
                    row_result = self._calculate_row_angles(polyline=polyline)
                    self._track_issues(row_result.issues)

                    if self.config.return_results:
                        results_by_oid[oid] = self._serialize_row_result(row_result)

        self._emit_summary_warnings()

        if self.config.return_results:
            return results_by_oid

        return None

    def _validate_config(self) -> None:
        if not self.config.angle_modes:
            raise ValueError(
                "AngleToolConfig.angle_modes must contain at least one mode."
            )

        if not self.config.return_results and not self.config.write_fields:
            raise ValueError(
                "At least one output behavior must be enabled: "
                "return_results or write_fields."
            )

        if self.config.write_fields and not self.config.output_lines:
            raise ValueError("output_lines is required when write_fields=True.")

        if self.config.field_name_by_mode is None:
            return

        for mode in self.config.field_name_by_mode:
            if mode == LineAngleMode.BOTH_ENDPOINT_SEGMENTS:
                raise ValueError(
                    "BOTH_ENDPOINT_SEGMENTS cannot be used in field_name_by_mode. "
                    "It is a convenience selector only."
                )

    def _resolve_requested_modes(self) -> tuple[_ConcreteLineAngleMode, ...]:
        requested = set()

        for mode in self.config.angle_modes:
            if mode == LineAngleMode.WHOLE_LINE:
                requested.add(_ConcreteLineAngleMode.WHOLE_LINE)
            elif mode == LineAngleMode.START_SEGMENT:
                requested.add(_ConcreteLineAngleMode.START_SEGMENT)
            elif mode == LineAngleMode.END_SEGMENT:
                requested.add(_ConcreteLineAngleMode.END_SEGMENT)
            elif mode == LineAngleMode.BOTH_ENDPOINT_SEGMENTS:
                requested.add(_ConcreteLineAngleMode.START_SEGMENT)
                requested.add(_ConcreteLineAngleMode.END_SEGMENT)
            elif mode == LineAngleMode.START_TO_MIDPOINT:
                requested.add(_ConcreteLineAngleMode.START_TO_MIDPOINT)
            elif mode == LineAngleMode.END_TO_MIDPOINT:
                requested.add(_ConcreteLineAngleMode.END_TO_MIDPOINT)
            else:
                raise ValueError(f"Unsupported angle mode: {mode}")

        ordered_modes = (
            _ConcreteLineAngleMode.WHOLE_LINE,
            _ConcreteLineAngleMode.START_SEGMENT,
            _ConcreteLineAngleMode.END_SEGMENT,
            _ConcreteLineAngleMode.START_TO_MIDPOINT,
            _ConcreteLineAngleMode.END_TO_MIDPOINT,
        )

        return tuple(mode for mode in ordered_modes if mode in requested)

    def _build_field_name_by_mode(self) -> dict[_ConcreteLineAngleMode, str]:
        default_field_name_by_mode = {
            _ConcreteLineAngleMode.WHOLE_LINE: "angle_whole",
            _ConcreteLineAngleMode.START_SEGMENT: "angle_start_seg",
            _ConcreteLineAngleMode.END_SEGMENT: "angle_end_seg",
            _ConcreteLineAngleMode.START_TO_MIDPOINT: "angle_start_mid",
            _ConcreteLineAngleMode.END_TO_MIDPOINT: "angle_end_mid",
        }

        resolved_field_name_by_mode = {
            mode: default_field_name_by_mode[mode] for mode in self.resolved_modes
        }

        if not self.config.field_name_by_mode:
            return resolved_field_name_by_mode

        public_to_private_mode = {
            LineAngleMode.WHOLE_LINE: _ConcreteLineAngleMode.WHOLE_LINE,
            LineAngleMode.START_SEGMENT: _ConcreteLineAngleMode.START_SEGMENT,
            LineAngleMode.END_SEGMENT: _ConcreteLineAngleMode.END_SEGMENT,
            LineAngleMode.START_TO_MIDPOINT: _ConcreteLineAngleMode.START_TO_MIDPOINT,
            LineAngleMode.END_TO_MIDPOINT: _ConcreteLineAngleMode.END_TO_MIDPOINT,
        }

        for public_mode, field_name in self.config.field_name_by_mode.items():
            private_mode = public_to_private_mode.get(public_mode)
            if private_mode in resolved_field_name_by_mode:
                resolved_field_name_by_mode[private_mode] = field_name

        return resolved_field_name_by_mode

    def _prepare_processing_feature_class(self) -> str:
        if not self.config.write_fields:
            return self.config.input_lines

        arcpy.management.CopyFeatures(
            self.config.input_lines,
            self.config.output_lines,
        )
        return self.config.output_lines

    def _ensure_output_fields(self, lines_fc: str) -> None:
        existing_fields = {field.name for field in arcpy.ListFields(lines_fc)}

        for mode in self.resolved_modes:
            field_name = self.field_name_by_mode[mode]
            if field_name in existing_fields:
                continue

            arcpy.management.AddField(
                in_table=lines_fc,
                field_name=field_name,
                field_type="DOUBLE",
            )

    def _calculate_row_angles(self, polyline) -> _RowAngleResult:
        if polyline is None:
            return self._unsupported_result(issue="null_geometry")

        if polyline.isMultipart:
            return self._unsupported_result(issue="multipart_not_supported")

        vertices = self._extract_vertices(polyline=polyline)
        if len(vertices) < 2:
            return self._unsupported_result(issue="too_few_vertices")

        if len(vertices) == 2:
            return self._calculate_two_vertex_result(vertices=vertices)

        return self._calculate_multivertex_result(
            polyline=polyline,
            vertices=vertices,
        )

    def _extract_vertices(self, polyline) -> list:
        vertices = []

        for part in polyline:
            for point in part:
                if point is None:
                    continue
                vertices.append(point)

        return vertices

    def _calculate_two_vertex_result(self, vertices: list) -> _RowAngleResult:
        start_point = vertices[0]
        end_point = vertices[1]

        base_angle = self._calculate_direction_angle(
            from_point=start_point,
            to_point=end_point,
        )

        reversed_angle = None
        if base_angle is not None:
            reversed_angle = self._reverse_angle(base_angle)

        angles_by_mode = {}
        for mode in self.resolved_modes:
            if mode == _ConcreteLineAngleMode.WHOLE_LINE:
                angles_by_mode[mode] = base_angle
            elif mode == _ConcreteLineAngleMode.START_SEGMENT:
                angles_by_mode[mode] = base_angle
            elif mode == _ConcreteLineAngleMode.START_TO_MIDPOINT:
                angles_by_mode[mode] = base_angle
            elif mode == _ConcreteLineAngleMode.END_SEGMENT:
                angles_by_mode[mode] = reversed_angle
            elif mode == _ConcreteLineAngleMode.END_TO_MIDPOINT:
                angles_by_mode[mode] = reversed_angle

        if base_angle is None:
            return _RowAngleResult(
                angles_by_mode=angles_by_mode,
                issues=("zero_length_line",),
                is_supported=False,
            )

        return _RowAngleResult(
            angles_by_mode=angles_by_mode,
            issues=(),
            is_supported=True,
        )

    def _calculate_multivertex_result(
        self, polyline, vertices: list
    ) -> _RowAngleResult:
        start_point = vertices[0]
        second_point = vertices[1]
        previous_to_end_point = vertices[-2]
        end_point = vertices[-1]
        midpoint = self._get_line_midpoint(polyline=polyline)

        angles_by_mode = {}

        for mode in self.resolved_modes:
            if mode == _ConcreteLineAngleMode.WHOLE_LINE:
                angles_by_mode[mode] = self._calculate_direction_angle(
                    from_point=start_point,
                    to_point=end_point,
                )
            elif mode == _ConcreteLineAngleMode.START_SEGMENT:
                angles_by_mode[mode] = self._calculate_direction_angle(
                    from_point=start_point,
                    to_point=second_point,
                )
            elif mode == _ConcreteLineAngleMode.END_SEGMENT:
                angles_by_mode[mode] = self._calculate_direction_angle(
                    from_point=end_point,
                    to_point=previous_to_end_point,
                )
            elif mode == _ConcreteLineAngleMode.START_TO_MIDPOINT:
                angles_by_mode[mode] = self._calculate_direction_angle(
                    from_point=start_point,
                    to_point=midpoint,
                )
            elif mode == _ConcreteLineAngleMode.END_TO_MIDPOINT:
                angles_by_mode[mode] = self._calculate_direction_angle(
                    from_point=end_point,
                    to_point=midpoint,
                )

        issues = []
        if all(value is None for value in angles_by_mode.values()):
            issues.append("no_requested_angles_available")

        return _RowAngleResult(
            angles_by_mode=angles_by_mode,
            issues=tuple(issues),
            is_supported=not issues,
        )

    def _get_line_midpoint(self, polyline):
        midpoint_geometry = polyline.positionAlongLine(0.5, use_percentage=True)
        if midpoint_geometry is None:
            return None
        return midpoint_geometry.firstPoint

    @staticmethod
    def _calculate_direction_angle(from_point, to_point) -> Optional[float]:
        if from_point is None or to_point is None:
            return None

        dx = to_point.X - from_point.X
        dy = to_point.Y - from_point.Y

        if dx == 0 and dy == 0:
            return None

        angle = degrees(atan2(dy, dx))
        return angle % 360.0

    @staticmethod
    def _reverse_angle(angle: float) -> float:
        return (angle + 180.0) % 360.0

    def _unsupported_result(self, issue: str) -> _RowAngleResult:
        return _RowAngleResult(
            angles_by_mode={mode: None for mode in self.resolved_modes},
            issues=(issue,),
            is_supported=False,
        )

    def _write_row_values_to_cursor_row(
        self,
        row: list,
        row_result: _RowAngleResult,
    ) -> None:
        start_index = 2

        for index, mode in enumerate(self.resolved_modes, start=start_index):
            row[index] = row_result.angles_by_mode.get(mode)

    def _serialize_row_result(self, row_result: _RowAngleResult) -> dict:
        public_mode_by_private_mode = {
            _ConcreteLineAngleMode.WHOLE_LINE: LineAngleMode.WHOLE_LINE,
            _ConcreteLineAngleMode.START_SEGMENT: LineAngleMode.START_SEGMENT,
            _ConcreteLineAngleMode.END_SEGMENT: LineAngleMode.END_SEGMENT,
            _ConcreteLineAngleMode.START_TO_MIDPOINT: LineAngleMode.START_TO_MIDPOINT,
            _ConcreteLineAngleMode.END_TO_MIDPOINT: LineAngleMode.END_TO_MIDPOINT,
        }

        return {
            "angles_by_mode": {
                public_mode_by_private_mode[mode]: value
                for mode, value in row_result.angles_by_mode.items()
            },
            "issues": row_result.issues,
            "is_supported": row_result.is_supported,
        }

    def _track_issues(self, issues: tuple[str, ...]) -> None:
        for issue in issues:
            self.issue_counts[issue] = self.issue_counts.get(issue, 0) + 1

    def _emit_summary_warnings(self) -> None:
        for issue, count in sorted(self.issue_counts.items()):
            arcpy.AddWarning(f"{count} feature(s) returned issue: {issue}")
