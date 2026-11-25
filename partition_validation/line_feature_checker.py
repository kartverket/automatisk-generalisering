# Line feature-specific partition analyzer

from collections import defaultdict
from typing import Any

import arcpy

from partition_validation.feature_checker_base import FeatureChecker


class LineFeatureChecker(FeatureChecker):
    """Analyzer for line features in partition validation."""

    def analyze(self) -> dict[str, Any]:
        """
        Analyze line features against area geometry.

        **For line features, we detect:**
        - Dangles (line endpoints within the area)

        Returns:
            Dictionary with statistics for the analyzed feature class
        """
        end_points = {
            k: v for k, v in self._get_relevant_end_points().items() if len(v) == 1
        }

        line_dangle_count = {}
        for (line_id,) in end_points.values():
            line_dangle_count[line_id] = line_dangle_count.get(line_id, 0) + 1

        return {
            "total_dangle_count": len(end_points),
            "line_dangle_count": line_dangle_count,
            "line_dangle_ids": list(line_dangle_count.keys()),
        }

    def _get_relevant_end_points(self) -> defaultdict[tuple[float, float], list[Any]]:
        """
        Get start and end points of lines that fall within the area.

        Returns:
            Dictionary mapping (x, y) coordinates to list of line feature IDs
        """
        end_points: defaultdict[tuple[float, float], list[Any]] = defaultdict(list)

        geom = self._get_area_geometry()
        if geom is None:
            print("Feature class geometry could not be retrieved.")
            return end_points

        with arcpy.da.SearchCursor(
            self.feature_layer, ["SHAPE@", self.id_field]
        ) as cursor:
            for line_geom, id_value in cursor:
                start_point = line_geom.firstPoint
                end_point = line_geom.lastPoint

                start_geom = arcpy.PointGeometry(
                    start_point, line_geom.spatialReference
                )
                end_geom = arcpy.PointGeometry(end_point, line_geom.spatialReference)

                if geom.contains(start_geom):
                    end_points[(start_point.X, start_point.Y)].append(id_value)
                if geom.contains(end_geom):
                    end_points[(end_point.X, end_point.Y)].append(id_value)

        return end_points
