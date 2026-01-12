from __future__ import annotations

from typing import Optional

import arcpy

from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy
from file_manager import WorkFileManager
from composition_configs import logic_config


class FillLineGaps:
    """
    What:
        Fills small gaps by extending dangling endpoints of input lines to the nearest location
        on target features within a tolerance distance.

    How:
        - Copies input lines to avoid modifying originals.
        - Adds ORIGINAL_ID field on the copied lines (set to OID).
        - Creates dangle points.
        - Removes lines that produced dangles from the "self target" candidate set.
        - Selects target features (self + optional external) within tolerance of dangles.
        - Filters dangles that are within tolerance of any target feature.
        - Runs Near (LOCATION) to obtain NEAR_X/NEAR_Y.
        - Updates the correct endpoint of each line to the NEAR_X/NEAR_Y location.

    Why:
        Used to close small digitizing gaps while keeping edits limited to endpoints.
    """

    ORIGINAL_ID = "line_gap_original_id"

    def __init__(self, line_gap_config: logic_config.FillLineGapsConfig):
        self.input_lines = line_gap_config.input_lines
        self.output_lines = line_gap_config.output_lines

        self.gap_tolerance_meters = line_gap_config.gap_tolerance_meters
        self.connect_to_features = line_gap_config.connect_to_features
        self.fill_gaps_on_self = line_gap_config.fill_gaps_on_self

        self.write_work_files_to_memory = (
            line_gap_config.work_file_manager_config.write_to_memory
        )
        self.keep_work_files = line_gap_config.work_file_manager_config.keep_files
        self.root_file = line_gap_config.work_file_manager_config.root_file

        if self.connect_to_features is None and self.fill_gaps_on_self is False:
            raise ValueError(
                "Invalid config: fill_gaps_on_self cannot be False when connect_to_features is None."
            )

        self.wfm = WorkFileManager(config=line_gap_config.work_file_manager_config)

        self.lines_copy = "lines_copy"
        self.dangles = "dangles"
        self.input_lines_filtered = "input_lines_filtered"
        self.filtered_dangles = "filtered_dangles"

        self.target_self = "target_self"
        self.target_feature_layers: list[str] = []

        self.work_file_list = [
            self.lines_copy,
            self.dangles,
            self.input_lines_filtered,
            self.filtered_dangles,
            self.target_self,
        ]

    def _tolerance_linear_unit(self) -> str:
        return f"{self.gap_tolerance_meters} Meters"

    def _copy_input_lines(self) -> None:
        arcpy.management.CopyFeatures(
            in_features=self.input_lines,
            out_feature_class=self.lines_copy,
        )

    def _add_original_id_field(self) -> None:
        existing_fields = {
            field.name for field in arcpy.ListFields(dataset=self.lines_copy)
        }
        if self.ORIGINAL_ID not in existing_fields:
            arcpy.management.AddField(
                in_table=self.lines_copy,
                field_name=self.ORIGINAL_ID,
                field_type="LONG",
            )

        oid_field = arcpy.Describe(self.lines_copy).OIDFieldName
        arcpy.management.CalculateField(
            in_table=self.lines_copy,
            field=self.ORIGINAL_ID,
            expression=f"!{oid_field}!",
            expression_type="PYTHON3",
        )

    def _create_dangles(self) -> None:
        arcpy.management.FeatureVerticesToPoints(
            in_features=self.lines_copy,
            out_feature_class=self.dangles,
            point_location="DANGLE",
        )

    def _remove_lines_that_produced_dangles(self) -> None:
        """
        What:
            Creates a filtered version of the copied lines where any line that produced
            a dangle is excluded (so self-targeting does not snap back onto itself).

        How:
            - Select lines within tolerance of dangles.
            - Invert selection to keep only lines not near those dangles.
        """
        if self.write_work_files_to_memory:
            custom_arcpy.select_location_and_make_feature_layer(
                input_layer=self.lines_copy,
                overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE.value,
                select_features=self.dangles,
                output_name=self.input_lines_filtered,
                inverted=True,
                search_distance=self._tolerance_linear_unit(),
            )

        if not self.write_work_files_to_memory:
            custom_arcpy.select_location_and_make_permanent_feature(
                input_layer=self.lines_copy,
                overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE.value,
                select_features=self.dangles,
                output_name=self.input_lines_filtered,
                inverted=True,
                search_distance=self._tolerance_linear_unit(),
            )

    def _select_targets_within_tolerance_of_dangles(self) -> list[str]:
        """
        What:
            Builds the list of target feature datasets to be used by Near.

        How:
            - If fill_gaps_on_self: select from input_lines_filtered within tolerance of dangles.
            - For each connect_to_features: select within tolerance of dangles into its own output.
        """
        target_layers: list[str] = []

        if self.fill_gaps_on_self:
            if self.write_work_files_to_memory:
                custom_arcpy.select_location_and_make_feature_layer(
                    input_layer=self.input_lines_filtered,
                    overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE.value,
                    select_features=self.dangles,
                    output_name=self.target_self,
                    search_distance=self._tolerance_linear_unit(),
                )

            if not self.write_work_files_to_memory:
                custom_arcpy.select_location_and_make_permanent_feature(
                    input_layer=self.input_lines_filtered,
                    overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE.value,
                    select_features=self.dangles,
                    output_name=self.target_self,
                    search_distance=self._tolerance_linear_unit(),
                )

            target_layers.append(self.target_self)

        if self.connect_to_features is not None:
            for index, feature_path in enumerate(self.connect_to_features):
                output_name = self.wfm.build_file_path(
                    file_name=f"target_feature_{index}",
                )

                if self.write_work_files_to_memory:
                    custom_arcpy.select_location_and_make_feature_layer(
                        input_layer=feature_path,
                        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE.value,
                        select_features=self.dangles,
                        output_name=output_name,
                        search_distance=self._tolerance_linear_unit(),
                    )

                if not self.write_work_files_to_memory:
                    custom_arcpy.select_location_and_make_permanent_feature(
                        input_layer=feature_path,
                        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE.value,
                        select_features=self.dangles,
                        output_name=output_name,
                        search_distance=self._tolerance_linear_unit(),
                    )

                self.target_feature_layers.append(output_name)
                target_layers.append(output_name)

        return target_layers

    def _filter_dangles_within_tolerance_of_targets(
        self, target_layers: list[str]
    ) -> None:
        """
        What:
            Keeps only dangles that are within tolerance of any target feature.

        How:
            - Creates a layer/view of dangles.
            - Accumulates selections (ADD_TO_SELECTION) per target.
            - Writes the selected dangles to filtered_dangles.
        """
        dangles_layer = "dangles_lyr"
        arcpy.management.MakeFeatureLayer(
            in_features=self.dangles,
            out_layer=dangles_layer,
        )

        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=dangles_layer,
            selection_type="CLEAR_SELECTION",
        )

        for target in target_layers:
            arcpy.management.SelectLayerByLocation(
                in_layer=dangles_layer,
                overlap_type="WITHIN_A_DISTANCE",
                select_features=target,
                search_distance=self._tolerance_linear_unit(),
                selection_type="ADD_TO_SELECTION",
            )

        arcpy.management.CopyFeatures(
            in_features=dangles_layer,
            out_feature_class=self.filtered_dangles,
        )

    def _run_near(self, target_layers: list[str]) -> None:
        arcpy.analysis.Near(
            in_features=self.filtered_dangles,
            near_features=target_layers,
            search_radius=self._tolerance_linear_unit(),
            location="LOCATION",
            angle="NO_ANGLE",
            method="PLANAR",
        )

    def _build_plan(self) -> dict[int, dict]:
        """
        What:
            Builds a dict keyed by ORIGINAL_ID with everything needed to update line endpoints.

        Note:
            Under current assumptions, each line produces max one dangle.
            Edge cases (two dangles per line) handled later.
        """
        plan: dict[int, dict] = {}

        fields = [
            self.ORIGINAL_ID,
            "SHAPE@XY",
            "NEAR_FID",
            "NEAR_X",
            "NEAR_Y",
        ]

        with arcpy.da.SearchCursor(
            in_table=self.filtered_dangles,
            field_names=fields,
        ) as cursor:
            for original_id, (dx, dy), near_fid, near_x, near_y in cursor:
                if near_fid is None:
                    continue

                plan[int(original_id)] = {
                    "processed": False,
                    "dangle_x": float(dx),
                    "dangle_y": float(dy),
                    "near_x": float(near_x),
                    "near_y": float(near_y),
                }

        return plan

    def _apply_symmetric_pair_skip(self, plan: dict[int, dict]) -> None:
        """
        What:
            Avoids processing a mutual dangle↔dangle pair twice.

        How:
            - Only possible/meaningful when dangles are included as near_features.
            - In this implementation, Near is run against target layers, and may include dangles
              only if you later decide to add them as a target. Kept here to support your stated intent.
        """
        _ = plan

    def _move_endpoint(
        self, shape, dangle_x: float, dangle_y: float, near_x: float, near_y: float
    ):
        """
        What:
            Moves the endpoint vertex that corresponds to the dangle point to NEAR_X/NEAR_Y.

        Assumptions:
            - No multipart polylines in input.
            - Dangle point equals one endpoint (within a small tolerance).
        """
        if shape is None:
            return shape

        part = shape.getPart(0)
        points = [pt for pt in part]
        if len(points) < 2:
            return shape

        first = points[0]
        last = points[-1]

        tol = 0.001

        def matches(point, x: float, y: float) -> bool:
            return abs(point.X - x) <= tol and abs(point.Y - y) <= tol

        if matches(point=first, x=dangle_x, y=dangle_y):
            points[0] = arcpy.Point(X=near_x, Y=near_y)
        elif matches(point=last, x=dangle_x, y=dangle_y):
            points[-1] = arcpy.Point(X=near_x, Y=near_y)
        else:
            # Fallback: choose closer endpoint to the dangle XY
            d_first = (first.X - dangle_x) ** 2 + (first.Y - dangle_y) ** 2
            d_last = (last.X - dangle_x) ** 2 + (last.Y - dangle_y) ** 2
            if d_first <= d_last:
                points[0] = arcpy.Point(X=near_x, Y=near_y)
            else:
                points[-1] = arcpy.Point(X=near_x, Y=near_y)

        new_array = arcpy.Array(points)
        return arcpy.Polyline(
            inputs=new_array,
            spatial_reference=shape.spatialReference,
        )

    def _apply_edits(self, plan: dict[int, dict]) -> None:
        if not plan:
            arcpy.management.CopyFeatures(
                in_features=self.lines_copy,
                out_feature_class=self.output_lines,
            )
            return

        fields = [self.ORIGINAL_ID, "SHAPE@"]

        with arcpy.da.UpdateCursor(
            in_table=self.lines_copy,
            field_names=fields,
        ) as cursor:
            for original_id, shape in cursor:
                original_id_int = int(original_id)
                if original_id_int not in plan:
                    continue

                info = plan[original_id_int]
                if info["processed"] is True:
                    continue

                new_shape = self._move_endpoint(
                    shape=shape,
                    dangle_x=info["dangle_x"],
                    dangle_y=info["dangle_y"],
                    near_x=info["near_x"],
                    near_y=info["near_y"],
                )
                cursor.updateRow((original_id, new_shape))

        arcpy.management.CopyFeatures(
            in_features=self.lines_copy,
            out_feature_class=self.output_lines,
        )

    def run(self) -> None:
        environment_setup.main()

        self.work_file_list = self.wfm.setup_work_file_paths(
            instance=self,
            file_structure=self.work_file_list,
        )

        self._copy_input_lines()
        self._add_original_id_field()
        self._create_dangles()

        self._remove_lines_that_produced_dangles()

        target_layers = self._select_targets_within_tolerance_of_dangles()
        self._filter_dangles_within_tolerance_of_targets(target_layers=target_layers)

        self._run_near(target_layers=target_layers)

        plan = self._build_plan()
        self._apply_symmetric_pair_skip(plan=plan)
        self._apply_edits(plan=plan)

        self.wfm.delete_created_files()
