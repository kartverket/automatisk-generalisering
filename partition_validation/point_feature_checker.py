# Point feature-specific partition analyzer

from typing import Any

import arcpy

from partition_validation.feature_checker_base import FeatureChecker


class PointFeatureChecker(FeatureChecker):
    """Analyzer for point features in partition validation."""

    def analyze(self) -> dict[str, Any]:
        """
        Analyze point features against partition features.

        **For point features, we detect:**
        - Point count

        Returns:
            Dictionary with statistics for the relevant feature class
        """
        point_count = self._count_points_in_area()
        return {"point_count": point_count}

    def _count_points_in_area(self) -> int:
        """
        Count point features that fall within the area.

        Returns:
            Number of points within the area
        """
        geom = self._get_area_geometry()
        if geom is None:
            print("Feature class geometry could not be retrieved.")
            return 0

        point_count = 0
        with arcpy.da.SearchCursor(self.feature_layer, ["SHAPE@"]) as cursor:
            for (point_geom,) in cursor:
                if geom.contains(point_geom):
                    point_count += 1

        return point_count
