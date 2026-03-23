from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from math import atan2, ceil, degrees, floor
from typing import Optional, Union, Dict

import arcpy
import numpy as np

from composition_configs.logic_config import (
    AngleToolConfig,
    LineAngleMode,
    LineEndpointMode,
    LineEndpointToolConfig,
    LineZOrientConfig,
    LineZOrientMode,
    LineZValueFieldNameConfig,
    LineZValueMode,
    LineZValueToolConfig,
)
from composition_configs.type_defs import RasterFilePath

from xarray.backends.common import NONE_VAR_NAME

from custom_tools.general_tools import custom_arcpy, file_utilities
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
        - Selector modes are request conveniences only.
        - Selector modes expand internally and are never stored as their
          own output values.
    """

    def __init__(self, config: AngleToolConfig):
        self.config = config
        self._validate_config()

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

        selector_only_modes = {
            LineAngleMode.BOTH_ENDPOINT_SEGMENTS,
            LineAngleMode.BOTH_ENDPOINT_TO_MIDPOINT,
            LineAngleMode.ALL_ANGLES,
        }

        for mode in self.config.field_name_by_mode:
            if mode in selector_only_modes:
                raise ValueError(
                    f"{mode.value} cannot be used in field_name_by_mode. "
                    "It is a selector-only mode."
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

            elif mode == LineAngleMode.BOTH_ENDPOINT_TO_MIDPOINT:
                requested.add(_ConcreteLineAngleMode.START_TO_MIDPOINT)
                requested.add(_ConcreteLineAngleMode.END_TO_MIDPOINT)

            elif mode == LineAngleMode.ALL_ANGLES:
                requested.add(_ConcreteLineAngleMode.WHOLE_LINE)
                requested.add(_ConcreteLineAngleMode.START_SEGMENT)
                requested.add(_ConcreteLineAngleMode.END_SEGMENT)
                requested.add(_ConcreteLineAngleMode.START_TO_MIDPOINT)
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
        self,
        polyline,
        vertices: list,
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


class _ConcreteLineEndpointMode(str, Enum):
    START_POINT = "start_point"
    END_POINT = "end_point"


@dataclass(frozen=True)
class _RowEndpointResult:
    coordinates_by_mode: dict[_ConcreteLineEndpointMode, Optional[tuple[float, float]]]
    issues: tuple[str, ...]
    is_supported: bool


class LineEndpointTool:
    """
    Materialize line endpoint coordinates for requested endpoint modes and
    optionally write them to fields on an output feature class.

    Definitions:
        - START_POINT = first vertex of the line
        - END_POINT = last vertex of the line

    Important:
        - BOTH_ENDPOINTS is a selector-only request mode.
        - It expands internally to START_POINT and END_POINT.
        - It is never stored as its own output value.
    """

    def __init__(self, config: LineEndpointToolConfig):
        self.config = config
        self._validate_config()

        self.resolved_modes = self._resolve_requested_modes()
        self.issue_counts: dict[str, int] = {}

    def run(self) -> Optional[dict[int, dict]]:
        lines_fc = self._prepare_processing_feature_class()

        if self.config.write_fields:
            self._ensure_output_fields(lines_fc=lines_fc)

        results_by_oid: dict[int, dict] = {}

        field_names = ["OID@", "SHAPE@"]

        if self.config.write_fields:
            field_names.extend(self._ordered_output_field_names())

            with arcpy.da.UpdateCursor(lines_fc, field_names) as cursor:
                for row in cursor:
                    oid = row[0]
                    polyline = row[1]

                    row_result = self._calculate_row_endpoints(polyline=polyline)
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
                    row_result = self._calculate_row_endpoints(polyline=polyline)
                    self._track_issues(row_result.issues)

                    if self.config.return_results:
                        results_by_oid[oid] = self._serialize_row_result(row_result)

        self._emit_summary_warnings()

        if self.config.return_results:
            return results_by_oid

        return None

    def _validate_config(self) -> None:
        if not self.config.endpoint_modes:
            raise ValueError(
                "LineEndpointToolConfig.endpoint_modes must contain at least one mode."
            )

        if not self.config.return_results and not self.config.write_fields:
            raise ValueError(
                "At least one output behavior must be enabled: "
                "return_results or write_fields."
            )

        if self.config.write_fields and not self.config.output_lines:
            raise ValueError("output_lines is required when write_fields=True.")

    def _resolve_requested_modes(self) -> tuple[_ConcreteLineEndpointMode, ...]:
        requested = set()

        for mode in self.config.endpoint_modes:
            if mode == LineEndpointMode.START_POINT:
                requested.add(_ConcreteLineEndpointMode.START_POINT)

            elif mode == LineEndpointMode.END_POINT:
                requested.add(_ConcreteLineEndpointMode.END_POINT)

            elif mode == LineEndpointMode.BOTH_ENDPOINTS:
                requested.add(_ConcreteLineEndpointMode.START_POINT)
                requested.add(_ConcreteLineEndpointMode.END_POINT)

            else:
                raise ValueError(f"Unsupported endpoint mode: {mode}")

        ordered_modes = (
            _ConcreteLineEndpointMode.START_POINT,
            _ConcreteLineEndpointMode.END_POINT,
        )

        return tuple(mode for mode in ordered_modes if mode in requested)

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

        for field_name in self._required_field_names():
            if field_name in existing_fields:
                continue

            arcpy.management.AddField(
                in_table=lines_fc,
                field_name=field_name,
                field_type="DOUBLE",
            )

    def _required_field_names(self) -> list[str]:
        field_names = []

        if _ConcreteLineEndpointMode.START_POINT in self.resolved_modes:
            field_names.extend(
                [
                    self.config.field_names.start_x,
                    self.config.field_names.start_y,
                ]
            )

        if _ConcreteLineEndpointMode.END_POINT in self.resolved_modes:
            field_names.extend(
                [
                    self.config.field_names.end_x,
                    self.config.field_names.end_y,
                ]
            )

        return field_names

    def _ordered_output_field_names(self) -> list[str]:
        field_names = []

        for mode in self.resolved_modes:
            if mode == _ConcreteLineEndpointMode.START_POINT:
                field_names.extend(
                    [
                        self.config.field_names.start_x,
                        self.config.field_names.start_y,
                    ]
                )
            elif mode == _ConcreteLineEndpointMode.END_POINT:
                field_names.extend(
                    [
                        self.config.field_names.end_x,
                        self.config.field_names.end_y,
                    ]
                )

        return field_names

    def _calculate_row_endpoints(self, polyline) -> _RowEndpointResult:
        if polyline is None:
            return self._unsupported_result(issue="null_geometry")

        if polyline.isMultipart:
            return self._unsupported_result(issue="multipart_not_supported")

        vertices = self._extract_vertices(polyline=polyline)

        if len(vertices) < 2:
            return self._unsupported_result(issue="too_few_vertices")

        start_point = vertices[0]
        end_point = vertices[-1]

        coordinates_by_mode: dict[
            _ConcreteLineEndpointMode,
            Optional[tuple[float, float]],
        ] = {}

        for mode in self.resolved_modes:
            if mode == _ConcreteLineEndpointMode.START_POINT:
                coordinates_by_mode[mode] = (start_point.X, start_point.Y)

            elif mode == _ConcreteLineEndpointMode.END_POINT:
                coordinates_by_mode[mode] = (end_point.X, end_point.Y)

        return _RowEndpointResult(
            coordinates_by_mode=coordinates_by_mode,
            issues=(),
            is_supported=True,
        )

    def _extract_vertices(self, polyline) -> list:
        vertices = []

        for part in polyline:
            for point in part:
                if point is None:
                    continue
                vertices.append(point)

        return vertices

    def _unsupported_result(self, issue: str) -> _RowEndpointResult:
        return _RowEndpointResult(
            coordinates_by_mode={mode: None for mode in self.resolved_modes},
            issues=(issue,),
            is_supported=False,
        )

    def _write_row_values_to_cursor_row(
        self,
        row: list,
        row_result: _RowEndpointResult,
    ) -> None:
        write_values = []

        for mode in self.resolved_modes:
            xy = row_result.coordinates_by_mode.get(mode)

            if xy is None:
                write_values.extend([None, None])
            else:
                write_values.extend([xy[0], xy[1]])

        row[2:] = write_values

    def _serialize_row_result(self, row_result: _RowEndpointResult) -> dict:
        public_mode_by_private_mode = {
            _ConcreteLineEndpointMode.START_POINT: LineEndpointMode.START_POINT,
            _ConcreteLineEndpointMode.END_POINT: LineEndpointMode.END_POINT,
        }

        return {
            "coordinates_by_mode": {
                public_mode_by_private_mode[mode]: (
                    None if xy is None else {"x": xy[0], "y": xy[1]}
                )
                for mode, xy in row_result.coordinates_by_mode.items()
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


@dataclass
class RasterHandle:
    """
    An in-memory window of a raster tile with the coordinate metadata needed
    for O(1) point lookups.

    Built by build_raster_handle; queried by local_z_at_xy.

    Attributes:
        array: 2-D float array (rows top-to-bottom). NoData cells are nan.
        xmin:  west edge of the loaded window in map coordinates.
        ymax:  north edge of the loaded window in map coordinates.
        xmax:  east edge of the loaded window in map coordinates.
        ymin:  south edge of the loaded window in map coordinates.
        cell_w: cell width in map units.
        cell_h: cell height in map units.
    """

    array: np.ndarray
    xmin: float
    ymax: float
    xmax: float
    ymin: float
    cell_w: float
    cell_h: float


class _ConcreteLineZValueMode(str, Enum):
    START_POINT = "start_point"
    END_POINT = "end_point"


@dataclass(frozen=True)
class _RowZValueResult:
    z_by_slot: dict[tuple[int, _ConcreteLineZValueMode], Optional[float]]
    issues: tuple[str, ...]
    is_supported: bool


class LineZValueTool:
    """
    Sample raster Z values at line endpoints and optionally write them to
    fields on an output feature class.

    Definitions:
        - START_POINT = first vertex of the line
        - END_POINT   = last vertex of the line

    Important:
        - BOTH_ENDPOINTS is a selector-only request mode.
        - It expands internally to START_POINT and END_POINT.
        - Multiple rasters are supported; each raster produces its own pair
          of output fields.
        - Coordinates are passed to GetCellValue in the line feature's own
          spatial reference. A warning is emitted when that SR differs from
          a raster's SR, but no reprojection is performed.
    """

    def __init__(self, config: LineZValueToolConfig):
        self.config = config
        self._validate_config()

        self.resolved_modes = self._resolve_requested_modes()
        self.resolved_field_names = self._resolve_field_names()
        self.ordered_slots = self._build_ordered_slots()
        self.issue_counts: dict[str, int] = {}

    def run(self) -> Optional[dict[int, dict]]:
        """
        Main entrypoint.

        Two-pass design:
            Pass 1 (SearchCursor): collect all endpoint coordinates and
                record any geometry issues.
            Build: load each raster into a RasterHandle windowed to the
                bounding box of all collected points (one IO call per raster).
            Compute: look up Z values via in-memory array indexing.
            Pass 2 (UpdateCursor, when write_fields=True): write results.

        Returns:
            A dict keyed by OID with z_by_raster_by_mode, issues, and
            is_supported entries, or None when return_results=False.
        """
        self._check_spatial_reference()
        lines_fc = self._prepare_processing_feature_class()

        if self.config.write_fields:
            self._ensure_output_fields(lines_fc=lines_fc)

        valid_endpoints, issues_by_oid = self._collect_endpoints(lines_fc)

        for issue in issues_by_oid.values():
            self._track_issues((issue,))

        raster_handles = self._build_raster_handles_for_endpoints(valid_endpoints)
        z_by_oid = self._compute_z_values(valid_endpoints, raster_handles)

        results_by_oid: dict[int, dict] = {}

        if self.config.write_fields:
            field_names = ["OID@"] + self._build_output_field_names_ordered()

            with arcpy.da.UpdateCursor(lines_fc, field_names) as cursor:
                for row in cursor:
                    oid = row[0]
                    row_result = self._make_row_result(oid, z_by_oid, issues_by_oid)
                    self._write_row_values_to_cursor_row(row=row, row_result=row_result)
                    cursor.updateRow(row)

                    if self.config.return_results:
                        results_by_oid[oid] = self._serialize_row_result(row_result)

        elif self.config.return_results:
            all_oids = set(valid_endpoints.keys()) | set(issues_by_oid.keys())
            for oid in all_oids:
                row_result = self._make_row_result(oid, z_by_oid, issues_by_oid)
                results_by_oid[oid] = self._serialize_row_result(row_result)

        self._emit_summary_warnings()

        if self.config.return_results:
            return results_by_oid

        return None

    def _validate_config(self) -> None:
        if not self.config.endpoint_modes:
            raise ValueError(
                "LineZValueToolConfig.endpoint_modes must contain at least one mode."
            )

        if not self.config.input_rasters:
            raise ValueError(
                "LineZValueToolConfig.input_rasters must contain at least one raster."
            )

        if not self.config.return_results and not self.config.write_fields:
            raise ValueError(
                "At least one output behavior must be enabled: "
                "return_results or write_fields."
            )

        if self.config.write_fields and not self.config.output_lines:
            raise ValueError("output_lines is required when write_fields=True.")

        if self.config.field_names_per_raster is not None:
            if len(self.config.field_names_per_raster) != len(
                self.config.input_rasters
            ):
                raise ValueError(
                    "field_names_per_raster must have the same length as input_rasters."
                )

    def _resolve_requested_modes(self) -> tuple[_ConcreteLineZValueMode, ...]:
        requested = set()

        for mode in self.config.endpoint_modes:
            if mode == LineZValueMode.START_POINT:
                requested.add(_ConcreteLineZValueMode.START_POINT)

            elif mode == LineZValueMode.END_POINT:
                requested.add(_ConcreteLineZValueMode.END_POINT)

            elif mode == LineZValueMode.BOTH_ENDPOINTS:
                requested.add(_ConcreteLineZValueMode.START_POINT)
                requested.add(_ConcreteLineZValueMode.END_POINT)

            else:
                raise ValueError(f"Unsupported endpoint mode: {mode}")

        ordered_modes = (
            _ConcreteLineZValueMode.START_POINT,
            _ConcreteLineZValueMode.END_POINT,
        )

        return tuple(mode for mode in ordered_modes if mode in requested)

    def _resolve_field_names(self) -> tuple[LineZValueFieldNameConfig, ...]:
        if self.config.field_names_per_raster is not None:
            return self.config.field_names_per_raster

        n = len(self.config.input_rasters)

        if n == 1:
            return (LineZValueFieldNameConfig(),)

        return tuple(
            LineZValueFieldNameConfig(
                start_z=f"start_z_{i + 1}",
                end_z=f"end_z_{i + 1}",
            )
            for i in range(n)
        )

    def _build_ordered_slots(self) -> list[tuple[int, _ConcreteLineZValueMode]]:
        slots = []

        for raster_idx in range(len(self.config.input_rasters)):
            for mode in self.resolved_modes:
                slots.append((raster_idx, mode))

        return slots

    def _build_output_field_names_ordered(self) -> list[str]:
        field_names = []

        for raster_idx, mode in self.ordered_slots:
            fn_config = self.resolved_field_names[raster_idx]

            if mode == _ConcreteLineZValueMode.START_POINT:
                field_names.append(fn_config.start_z)
            else:
                field_names.append(fn_config.end_z)

        return field_names

    def _prepare_processing_feature_class(self) -> str:
        if not self.config.write_fields:
            return self.config.input_lines

        file_utilities.delete_feature(input_feature=self.config.output_lines)
        arcpy.management.CopyFeatures(
            self.config.input_lines,
            self.config.output_lines,
        )
        return self.config.output_lines

    def _ensure_output_fields(self, lines_fc: str) -> None:
        existing_fields = {field.name for field in arcpy.ListFields(lines_fc)}

        for field_name in self._build_output_field_names_ordered():
            if field_name in existing_fields:
                continue

            arcpy.management.AddField(
                in_table=lines_fc,
                field_name=field_name,
                field_type="DOUBLE",
            )

    def _check_spatial_reference(self) -> None:
        try:
            lines_sr = arcpy.Describe(self.config.input_lines).spatialReference
        except Exception:
            return

        for raster_path in self.config.input_rasters:
            try:
                raster_sr = arcpy.Describe(raster_path).spatialReference
            except Exception:
                continue

            if lines_sr.factoryCode == 0 or raster_sr.factoryCode == 0:
                continue

            if lines_sr.factoryCode != raster_sr.factoryCode:
                arcpy.AddWarning(
                    f"Spatial reference mismatch: input lines ({lines_sr.name}) vs "
                    f"raster ({raster_sr.name}): {raster_path}. "
                    "Z values are sampled using line coordinates without reprojection."
                )

    def _collect_endpoints(
        self,
        lines_fc: str,
    ) -> tuple[
        dict[int, dict[_ConcreteLineZValueMode, tuple[float, float]]],
        dict[int, str],
    ]:
        valid_endpoints: dict[int, dict[_ConcreteLineZValueMode, tuple[float, float]]] = {}
        issues_by_oid: dict[int, str] = {}

        with arcpy.da.SearchCursor(lines_fc, ["OID@", "SHAPE@"]) as cursor:
            for oid, polyline in cursor:
                if polyline is None:
                    issues_by_oid[oid] = "null_geometry"
                    continue

                if polyline.isMultipart:
                    issues_by_oid[oid] = "multipart_not_supported"
                    continue

                start_point, end_point = self._extract_endpoints(polyline)

                if start_point is None:
                    issues_by_oid[oid] = "too_few_vertices"
                    continue

                endpoints_for_oid: dict[_ConcreteLineZValueMode, tuple[float, float]] = {}

                for mode in self.resolved_modes:
                    if mode == _ConcreteLineZValueMode.START_POINT:
                        endpoints_for_oid[mode] = (start_point.X, start_point.Y)
                    else:
                        endpoints_for_oid[mode] = (end_point.X, end_point.Y)

                valid_endpoints[oid] = endpoints_for_oid

        return valid_endpoints, issues_by_oid

    def _build_raster_handles_for_endpoints(
        self,
        valid_endpoints: dict[int, dict[_ConcreteLineZValueMode, tuple[float, float]]],
    ) -> list[Optional[RasterHandle]]:
        all_xy = [
            xy
            for ep in valid_endpoints.values()
            for xy in ep.values()
        ]

        if not all_xy:
            return [None] * len(self.config.input_rasters)

        clip_xmin = min(xy[0] for xy in all_xy)
        clip_ymin = min(xy[1] for xy in all_xy)
        clip_xmax = max(xy[0] for xy in all_xy)
        clip_ymax = max(xy[1] for xy in all_xy)

        handles: list[Optional[RasterHandle]] = []

        for raster_path in self.config.input_rasters:
            try:
                handle = build_raster_handle(
                    raster_path=raster_path,
                    clip_xmin=clip_xmin,
                    clip_ymin=clip_ymin,
                    clip_xmax=clip_xmax,
                    clip_ymax=clip_ymax,
                )
                handles.append(handle)
            except Exception as exc:
                arcpy.AddWarning(
                    f"Could not load raster {raster_path}: {exc}. "
                    "Z values for this raster will be None."
                )
                handles.append(None)

        return handles

    def _compute_z_values(
        self,
        valid_endpoints: dict[int, dict[_ConcreteLineZValueMode, tuple[float, float]]],
        raster_handles: list[Optional[RasterHandle]],
    ) -> dict[int, dict[tuple[int, _ConcreteLineZValueMode], Optional[float]]]:
        z_by_oid: dict[int, dict[tuple[int, _ConcreteLineZValueMode], Optional[float]]] = {}

        for oid, endpoints_for_oid in valid_endpoints.items():
            z_by_slot: dict[tuple[int, _ConcreteLineZValueMode], Optional[float]] = {}

            for raster_idx, handle in enumerate(raster_handles):
                for mode in self.resolved_modes:
                    xy = endpoints_for_oid[mode]

                    if handle is None:
                        z_by_slot[(raster_idx, mode)] = None
                    else:
                        z_by_slot[(raster_idx, mode)] = local_z_at_xy(
                            [handle], xy[0], xy[1]
                        )

            z_by_oid[oid] = z_by_slot

        return z_by_oid

    def _make_row_result(
        self,
        oid: int,
        z_by_oid: dict[int, dict[tuple[int, _ConcreteLineZValueMode], Optional[float]]],
        issues_by_oid: dict[int, str],
    ) -> _RowZValueResult:
        if oid in issues_by_oid:
            return self._unsupported_result(issues_by_oid[oid])

        return _RowZValueResult(
            z_by_slot=z_by_oid.get(oid, {}),
            issues=(),
            is_supported=True,
        )

    def _extract_endpoints(self, polyline) -> tuple[Optional[object], Optional[object]]:
        vertices = []

        for part in polyline:
            for point in part:
                if point is not None:
                    vertices.append(point)

        if len(vertices) < 2:
            return None, None

        return vertices[0], vertices[-1]

    def _unsupported_result(self, issue: str) -> _RowZValueResult:
        return _RowZValueResult(
            z_by_slot={slot: None for slot in self.ordered_slots},
            issues=(issue,),
            is_supported=False,
        )

    def _write_row_values_to_cursor_row(
        self,
        row: list,
        row_result: _RowZValueResult,
    ) -> None:
        for index, slot in enumerate(self.ordered_slots, start=2):
            row[index] = row_result.z_by_slot.get(slot)

    def _serialize_row_result(self, row_result: _RowZValueResult) -> dict:
        public_mode_by_private = {
            _ConcreteLineZValueMode.START_POINT: LineZValueMode.START_POINT,
            _ConcreteLineZValueMode.END_POINT: LineZValueMode.END_POINT,
        }

        z_by_raster_by_mode: dict[str, dict[LineZValueMode, Optional[float]]] = {}

        for (raster_idx, mode), z_value in row_result.z_by_slot.items():
            raster_path = self.config.input_rasters[raster_idx]
            public_mode = public_mode_by_private[mode]

            if raster_path not in z_by_raster_by_mode:
                z_by_raster_by_mode[raster_path] = {}

            z_by_raster_by_mode[raster_path][public_mode] = z_value

        return {
            "z_by_raster_by_mode": z_by_raster_by_mode,
            "issues": row_result.issues,
            "is_supported": row_result.is_supported,
        }

    def _track_issues(self, issues: tuple[str, ...]) -> None:
        for issue in issues:
            self.issue_counts[issue] = self.issue_counts.get(issue, 0) + 1

    def _emit_summary_warnings(self) -> None:
        for issue, count in sorted(self.issue_counts.items()):
            arcpy.AddWarning(f"{count} feature(s) returned issue: {issue}")


def local_line_angle_at_xy(
    *,
    polyline,
    x: float,
    y: float,
    desired_half_window_m: float,
    min_half_window_percent: float = 0.01,
    max_half_window_percent: float = 0.25,
) -> Optional[float]:
    """
    Returns a local direction angle [0, 360) for the polyline near the nearest point
    to (x, y), using a small window around that measure.

    Pure geometry helper (no IO). Returns None if unsupported.
    """

    def _direction_angle(p0, p1) -> Optional[float]:
        if p0 is None or p1 is None:
            return None
        dx = p1.X - p0.X
        dy = p1.Y - p0.Y
        if dx == 0 and dy == 0:
            return None
        return degrees(atan2(dy, dx)) % 360.0

    def _query_measure_percent(polyline, pt_geom) -> Optional[float]:
        def _extract(q) -> Optional[float]:
            if not q or len(q) < 2 or q[1] is None:
                return None
            try:
                return float(q[1])
            except (TypeError, ValueError):
                return None

        # Prefer percentage along line (0..1)
        try:
            q = polyline.queryPointAndDistance(pt_geom, use_percentage=True)
            m = _extract(q)
            if m is not None:
                return m
        except TypeError:
            pass

        # Some versions accept positional boolean
        try:
            q = polyline.queryPointAndDistance(pt_geom, True)
            m = _extract(q)
            if m is not None:
                return m
        except TypeError:
            pass

        # Fallback: distance along line in map units -> convert to percent
        try:
            q = polyline.queryPointAndDistance(pt_geom)
            if not q or len(q) < 2 or q[1] is None:
                return None
            dist_along = float(q[1])

            length = float(getattr(polyline, "length", 0.0) or 0.0)
            if length <= 0.0:
                return None

            m = dist_along / length
            # clamp to [0,1]
            return max(0.0, min(1.0, float(m)))
        except Exception:
            return None

    def _position_along_percent(polyline, p: float):
        # Prefer keyword
        try:
            return polyline.positionAlongLine(float(p), use_percentage=True)
        except TypeError:
            # Some versions accept positional boolean
            return polyline.positionAlongLine(float(p), True)

    # 1) Validate geometry
    if polyline is None:
        return None
    if getattr(polyline, "isMultipart", False):
        return None
    length = float(getattr(polyline, "length", 0.0) or 0.0)
    if length <= 0.0:
        return None

    # 2) Convert length to meters if possible (fallback to dataset units)
    sr = getattr(polyline, "spatialReference", None)
    meters_per_unit = getattr(sr, "metersPerUnit", None) if sr is not None else None
    meters_per_unit = float(meters_per_unit) if meters_per_unit else 1.0
    length_m = length * meters_per_unit
    if length_m <= 0.0:
        return None

    # 3) Find measure (percentage) of nearest point along line
    pt_geom = arcpy.PointGeometry(arcpy.Point(float(x), float(y)), sr)
    m = _query_measure_percent(polyline, pt_geom)
    if m is None:
        return None

    # 4) Compute window as percent, clamp
    half_p = float(desired_half_window_m) / float(length_m)
    half_p = max(
        float(min_half_window_percent), min(float(max_half_window_percent), half_p)
    )

    start = max(0.0, m - half_p)
    end = min(1.0, m + half_p)

    # 5) Sample points and compute local direction; fallback to whole line
    def _whole_line_angle() -> Optional[float]:
        a0 = _position_along_percent(polyline, 0.0)
        a1 = _position_along_percent(polyline, 1.0)
        if a0 is None or a1 is None:
            return None
        return _direction_angle(a0.firstPoint, a1.firstPoint)

    if (end - start) < 1e-9:
        return _whole_line_angle()

    s0 = _position_along_percent(polyline, start)
    s1 = _position_along_percent(polyline, end)
    if s0 is None or s1 is None:
        return _whole_line_angle()

    angle = _direction_angle(s0.firstPoint, s1.firstPoint)
    if angle is None:
        angle = _whole_line_angle()

    return angle


def build_raster_handle(
    raster_path: str,
    clip_xmin: Optional[float] = None,
    clip_ymin: Optional[float] = None,
    clip_xmax: Optional[float] = None,
    clip_ymax: Optional[float] = None,
) -> RasterHandle:
    """
    Load a raster tile (or a clipped window of it) into a RasterHandle for
    fast in-memory point lookups via local_z_at_xy.

    When clip bounds are provided the loaded window is the intersection of
    those bounds with the tile extent, snapped outward to cell boundaries so
    that every point within the clip is covered.  When no clip bounds are
    given the full tile is loaded (use only for small rasters).

    NoData cells are stored as nan; callers receive None from local_z_at_xy
    for those cells.

    Args:
        raster_path: Path to the raster file.
        clip_xmin: West edge of the region of interest in map coordinates.
        clip_ymin: South edge of the region of interest in map coordinates.
        clip_xmax: East edge of the region of interest in map coordinates.
        clip_ymax: North edge of the region of interest in map coordinates.

    Returns:
        RasterHandle ready for local_z_at_xy queries.
    """
    desc = arcpy.Describe(raster_path)
    tile_xmin = desc.extent.XMin
    tile_ymin = desc.extent.YMin
    tile_xmax = desc.extent.XMax
    tile_ymax = desc.extent.YMax
    cell_w = desc.meanCellWidth
    cell_h = desc.meanCellHeight
    tile_ncols = int(round((tile_xmax - tile_xmin) / cell_w))
    tile_nrows = int(round((tile_ymax - tile_ymin) / cell_h))

    if all(v is not None for v in [clip_xmin, clip_ymin, clip_xmax, clip_ymax]):
        # Intersect clip with tile extent then snap outward to cell boundaries.
        effective_xmin = max(tile_xmin, clip_xmin)
        effective_ymin = max(tile_ymin, clip_ymin)
        effective_xmax = min(tile_xmax, clip_xmax)
        effective_ymax = min(tile_ymax, clip_ymax)

        col_start = max(0, floor((effective_xmin - tile_xmin) / cell_w))
        row_start = max(0, floor((tile_ymax - effective_ymax) / cell_h))
        col_end = min(tile_ncols, ceil((effective_xmax - tile_xmin) / cell_w))
        row_end = min(tile_nrows, ceil((tile_ymax - effective_ymin) / cell_h))

        ncols = max(1, col_end - col_start)
        nrows = max(1, row_end - row_start)

        window_xmin = tile_xmin + col_start * cell_w
        window_ymax = tile_ymax - row_start * cell_h
    else:
        ncols = tile_ncols
        nrows = tile_nrows
        window_xmin = tile_xmin
        window_ymax = tile_ymax

    window_xmax = window_xmin + ncols * cell_w
    window_ymin = window_ymax - nrows * cell_h

    array = arcpy.RasterToNumPyArray(
        in_raster=raster_path,
        lower_left_corner=arcpy.Point(window_xmin, window_ymin),
        ncols=ncols,
        nrows=nrows,
        nodata_to_value=np.nan,
    ).astype(float)

    return RasterHandle(
        array=array,
        xmin=window_xmin,
        ymax=window_ymax,
        xmax=window_xmax,
        ymin=window_ymin,
        cell_w=cell_w,
        cell_h=cell_h,
    )


def local_z_at_xy(
    raster_handles: list[RasterHandle],
    x: float,
    y: float,
) -> Optional[float]:
    """
    Return the raster Z value at (x, y) from the first handle whose window
    covers the point.

    Pure function — no IO.  Mirrors local_line_angle_at_xy in intent: it is
    designed to be called on demand inside a processing loop after handles
    have been built once with build_raster_handle.

    Returns None when the point falls outside all handles, lands on a NoData
    cell, or the index computation produces an out-of-bounds result.

    Args:
        raster_handles: Ordered list of RasterHandle objects to search.
        x: X coordinate in the same spatial reference as the handles.
        y: Y coordinate in the same spatial reference as the handles.

    Returns:
        Z value as float, or None.
    """
    for handle in raster_handles:
        if not (handle.xmin <= x < handle.xmax and handle.ymin < y <= handle.ymax):
            continue

        col = int((x - handle.xmin) / handle.cell_w)
        row = int((handle.ymax - y) / handle.cell_h)

        nrows, ncols = handle.array.shape
        if not (0 <= row < nrows and 0 <= col < ncols):
            continue

        z = handle.array[row, col]
        if np.isnan(z):
            return None

        return float(z)

    return None


def find_rasters_for_vector_extent(
    raster_dir: str,
    input_features: Union[str, list[str]],
) -> list[RasterFilePath]:
    """
    Return paths of all .tif files in raster_dir whose extents intersect
    the combined extent of the given input feature classes.

    The directory is treated as flat — subdirectories are not searched.
    Auxiliary sidecar files (.aux.xml, .ovr, etc.) are ignored.

    Extent comparison is done in each dataset's own coordinate system.
    A warning is emitted if the vector SR differs from the raster SR, but
    no reprojection is performed.

    Args:
        raster_dir: Path to a flat directory containing .tif raster files.
        input_features: One or more feature class paths whose combined extent
            defines the area of interest.

    Returns:
        Sorted list of .tif file paths that intersect the vector extent.
    """
    if isinstance(input_features, str):
        input_features = [input_features]

    tif_paths = sorted(
        os.path.join(raster_dir, f)
        for f in os.listdir(raster_dir)
        if f.lower().endswith(".tif")
    )

    if not tif_paths:
        return []

    union_xmin = float("inf")
    union_ymin = float("inf")
    union_xmax = float("-inf")
    union_ymax = float("-inf")
    vector_sr = None

    for fc in input_features:
        try:
            desc = arcpy.Describe(fc)
            ext = desc.extent
            union_xmin = min(union_xmin, ext.XMin)
            union_ymin = min(union_ymin, ext.YMin)
            union_xmax = max(union_xmax, ext.XMax)
            union_ymax = max(union_ymax, ext.YMax)
            if vector_sr is None:
                vector_sr = desc.spatialReference
        except Exception:
            arcpy.AddWarning(f"Could not read extent of feature class: {fc}. Skipping.")

    if union_xmin == float("inf"):
        return []

    sr_warning_emitted = False
    matched = []

    for tif_path in tif_paths:
        try:
            raster_desc = arcpy.Describe(tif_path)
            raster_ext = raster_desc.extent
            raster_sr = raster_desc.spatialReference

            if (
                not sr_warning_emitted
                and vector_sr is not None
                and raster_sr is not None
                and vector_sr.factoryCode != 0
                and raster_sr.factoryCode != 0
                and vector_sr.factoryCode != raster_sr.factoryCode
            ):
                arcpy.AddWarning(
                    f"Spatial reference mismatch: input features ({vector_sr.name}) vs "
                    f"raster ({raster_sr.name}). "
                    "Extent intersection is compared without reprojection."
                )
                sr_warning_emitted = True

            if (
                raster_ext.XMax > union_xmin
                and raster_ext.XMin < union_xmax
                and raster_ext.YMax > union_ymin
                and raster_ext.YMin < union_ymax
            ):
                matched.append(RasterFilePath(tif_path))

        except Exception:
            arcpy.AddWarning(f"Could not read extent of raster: {tif_path}. Skipping.")

    return matched


# ---------------------------------------------------------------------------
# Endpoint key type used throughout LineZOrientTool.
# A snapped integer grid coordinate pair — two endpoints that fall on the
# same cell are treated as connected.
# ---------------------------------------------------------------------------
_EndpointKey = tuple[int, int]


class LineZOrientTool:
    """
    Orient line features so that the start vertex is upstream (higher Z) and
    the end vertex is downstream (lower Z).

    Two modes are supported, controlled by LineZOrientConfig.orientation_mode:

    INDIVIDUAL
        Each line is oriented in isolation.  If start_z < end_z the line is
        flipped.  Lines where either endpoint has no raster coverage are left
        unchanged and produce a warning.

    NETWORK
        Lines that share endpoints are treated as a connected network.  Within
        each connected component the endpoint with the lowest sampled Z is
        identified as the outlet.  All lines in the component are then
        oriented so that flow runs toward the outlet, regardless of each
        individual line's Z drop.  This corrects single outlier segments that
        would otherwise point against the network's predominant direction.
        Components where no Z values can be sampled are skipped with a warning.

    The method modifies input_lines in-place (no output feature class is
    created).  It is designed to be called on a working copy inside
    FillLineGaps.
    """

    def __init__(self, config: LineZOrientConfig) -> None:
        self.config = config
        self._tol_grid = max(1e-9, float(config.connectivity_tolerance_meters))

    def run(self) -> None:
        handles = self._build_raster_handles()
        z_by_oid = self._sample_z_values(handles)

        if self.config.orientation_mode == LineZOrientMode.INDIVIDUAL:
            oids_to_flip = self._compute_individual_flips(z_by_oid)
        else:
            oids_to_flip = self._compute_network_flips(z_by_oid)

        if oids_to_flip:
            self._flip_lines(oids_to_flip)

    # ------------------------------------------------------------------
    # Raster handles
    # ------------------------------------------------------------------

    def _build_raster_handles(self) -> list[RasterHandle]:
        desc = arcpy.Describe(self.config.input_lines)
        ext = desc.extent
        handles: list[RasterHandle] = []
        for raster_path in self.config.raster_paths:
            try:
                handle = build_raster_handle(
                    raster_path,
                    clip_xmin=ext.XMin,
                    clip_ymin=ext.YMin,
                    clip_xmax=ext.XMax,
                    clip_ymax=ext.YMax,
                )
                handles.append(handle)
            except Exception as exc:
                arcpy.AddWarning(
                    f"LineZOrientTool: could not load raster {raster_path}: {exc}"
                )
        return handles

    # ------------------------------------------------------------------
    # Z sampling
    # ------------------------------------------------------------------

    def _sample_z_values(
        self,
        handles: list[RasterHandle],
    ) -> dict[int, tuple[Optional[float], Optional[float]]]:
        """Return {oid: (start_z, end_z)} for every line in input_lines."""
        oid_field = arcpy.Describe(self.config.input_lines).OIDFieldName
        z_by_oid: dict[int, tuple[Optional[float], Optional[float]]] = {}

        with arcpy.da.SearchCursor(
            self.config.input_lines, [oid_field, "SHAPE@"]
        ) as cursor:
            for oid, polyline in cursor:
                if polyline is None or polyline.partCount == 0:
                    arcpy.AddWarning(
                        f"LineZOrientTool: OID {oid} has null or empty geometry. Skipping."
                    )
                    continue

                first = polyline.firstPoint
                last = polyline.lastPoint

                if first is None or last is None:
                    arcpy.AddWarning(
                        f"LineZOrientTool: OID {oid} has no first/last point. Skipping."
                    )
                    continue

                start_z = local_z_at_xy(handles, first.X, first.Y)
                end_z = local_z_at_xy(handles, last.X, last.Y)
                z_by_oid[int(oid)] = (start_z, end_z)

        return z_by_oid

    # ------------------------------------------------------------------
    # INDIVIDUAL mode
    # ------------------------------------------------------------------

    def _compute_individual_flips(
        self,
        z_by_oid: dict[int, tuple[Optional[float], Optional[float]]],
    ) -> set[int]:
        oids_to_flip: set[int] = set()
        no_data_count = 0

        for oid, (start_z, end_z) in z_by_oid.items():
            if start_z is None or end_z is None:
                no_data_count += 1
                continue
            if start_z < end_z:
                oids_to_flip.add(oid)

        if no_data_count:
            arcpy.AddWarning(
                f"LineZOrientTool (INDIVIDUAL): {no_data_count} line(s) had no raster "
                "coverage at one or both endpoints and were left unchanged."
            )

        return oids_to_flip

    # ------------------------------------------------------------------
    # NETWORK mode
    # ------------------------------------------------------------------

    def _build_endpoint_graph(
        self,
    ) -> tuple[
        dict[int, tuple[_EndpointKey, _EndpointKey]],
        dict[_EndpointKey, list[int]],
    ]:
        """
        Read all line geometries and return two complementary dicts:

        oid_to_eps   : {oid: (start_key, end_key)}
        ep_to_oids   : {endpoint_key: [oid, ...]}

        Endpoint keys are integer grid coordinates snapped to
        connectivity_tolerance_meters so that nearby endpoints are
        treated as shared.
        """
        scale = 1.0 / self._tol_grid
        oid_field = arcpy.Describe(self.config.input_lines).OIDFieldName

        oid_to_eps: dict[int, tuple[_EndpointKey, _EndpointKey]] = {}
        ep_to_oids: dict[_EndpointKey, list[int]] = {}

        with arcpy.da.SearchCursor(
            self.config.input_lines, [oid_field, "SHAPE@"]
        ) as cursor:
            for oid, polyline in cursor:
                if polyline is None or polyline.partCount == 0:
                    continue
                first = polyline.firstPoint
                last = polyline.lastPoint
                if first is None or last is None:
                    continue

                oid = int(oid)
                start_key: _EndpointKey = (
                    int(round(first.X * scale)),
                    int(round(first.Y * scale)),
                )
                end_key: _EndpointKey = (
                    int(round(last.X * scale)),
                    int(round(last.Y * scale)),
                )

                oid_to_eps[oid] = (start_key, end_key)
                ep_to_oids.setdefault(start_key, []).append(oid)
                ep_to_oids.setdefault(end_key, []).append(oid)

        return oid_to_eps, ep_to_oids

    def _find_components(
        self,
        oid_to_eps: dict[int, tuple[_EndpointKey, _EndpointKey]],
        ep_to_oids: dict[_EndpointKey, list[int]],
    ) -> list[set[int]]:
        """Return a list of connected components as sets of OIDs."""
        visited_oids: set[int] = set()
        components: list[set[int]] = []

        for seed_oid in oid_to_eps:
            if seed_oid in visited_oids:
                continue

            component: set[int] = set()
            queue = [seed_oid]

            while queue:
                oid = queue.pop()
                if oid in visited_oids:
                    continue
                visited_oids.add(oid)
                component.add(oid)

                for ep_key in oid_to_eps[oid]:
                    for neighbor_oid in ep_to_oids.get(ep_key, []):
                        if neighbor_oid not in visited_oids:
                            queue.append(neighbor_oid)

            components.append(component)

        return components

    def _orient_component(
        self,
        component: set[int],
        oid_to_eps: dict[int, tuple[_EndpointKey, _EndpointKey]],
        ep_to_oids: dict[_EndpointKey, list[int]],
        z_by_oid: dict[int, tuple[Optional[float], Optional[float]]],
    ) -> set[int]:
        """
        BFS from the lowest-Z endpoint in the component.  Returns the set of
        OIDs within this component that need to be flipped.
        """
        # Collect all endpoint keys and their sampled Z values for this component.
        ep_z: dict[_EndpointKey, float] = {}
        for oid in component:
            if oid not in z_by_oid:
                continue
            start_z, end_z = z_by_oid[oid]
            start_key, end_key = oid_to_eps[oid]
            if start_z is not None:
                if start_key not in ep_z or start_z < ep_z[start_key]:
                    ep_z[start_key] = start_z
            if end_z is not None:
                if end_key not in ep_z or end_z < ep_z[end_key]:
                    ep_z[end_key] = end_z

        if not ep_z:
            return set()

        outlet_ep = min(ep_z, key=lambda k: ep_z[k])

        # BFS from outlet endpoint, orienting lines so their END is toward the outlet.
        oids_to_flip: set[int] = set()
        visited_eps: set[_EndpointKey] = {outlet_ep}
        visited_oids: set[int] = set()
        queue: list[_EndpointKey] = [outlet_ep]

        while queue:
            current_ep = queue.pop(0)

            for oid in ep_to_oids.get(current_ep, []):
                if oid not in component or oid in visited_oids:
                    continue
                visited_oids.add(oid)

                start_key, end_key = oid_to_eps[oid]

                if end_key == current_ep:
                    # END is on the outlet side — correctly oriented.
                    other_ep = start_key
                else:
                    # START is on the outlet side — needs flipping.
                    oids_to_flip.add(oid)
                    other_ep = end_key

                if other_ep not in visited_eps:
                    visited_eps.add(other_ep)
                    queue.append(other_ep)

        return oids_to_flip

    def _compute_network_flips(
        self,
        z_by_oid: dict[int, tuple[Optional[float], Optional[float]]],
    ) -> set[int]:
        oid_to_eps, ep_to_oids = self._build_endpoint_graph()
        components = self._find_components(oid_to_eps, ep_to_oids)

        oids_to_flip: set[int] = set()
        skipped_components = 0

        for component in components:
            flips = self._orient_component(
                component, oid_to_eps, ep_to_oids, z_by_oid
            )
            if not flips and all(
                z_by_oid.get(oid, (None, None)) == (None, None) for oid in component
            ):
                skipped_components += 1
                continue
            oids_to_flip.update(flips)

        if skipped_components:
            arcpy.AddWarning(
                f"LineZOrientTool (NETWORK): {skipped_components} connected component(s) "
                "had no raster coverage and were left unchanged."
            )

        return oids_to_flip

    # ------------------------------------------------------------------
    # Shared flip helper
    # ------------------------------------------------------------------

    def _flip_lines(self, oids_to_flip: set[int]) -> None:
        """Reverse the geometry of every OID in oids_to_flip in-place."""
        oid_field = arcpy.Describe(self.config.input_lines).OIDFieldName

        with arcpy.da.UpdateCursor(
            self.config.input_lines, [oid_field, "SHAPE@"]
        ) as cursor:
            for row in cursor:
                if int(row[0]) not in oids_to_flip:
                    continue

                polyline: arcpy.Polyline = row[1]
                if polyline is None:
                    continue

                reversed_parts = arcpy.Array()
                for part_idx in range(polyline.partCount):
                    part = polyline.getPart(part_idx)
                    points = [part.getObject(i) for i in range(part.count)]
                    reversed_part = arcpy.Array(reversed(points))
                    reversed_parts.add(reversed_part)

                row[1] = arcpy.Polyline(reversed_parts, polyline.spatialReference)
                cursor.updateRow(row)
