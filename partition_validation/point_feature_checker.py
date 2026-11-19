# Point feature-specific partition analyzer

from typing import Any

import arcpy

from partition_validation.feature_checker_base import FeatureChecker


class PointFeatureChecker(FeatureChecker):
    """Analyzer for point features in partition validation."""

    def analyze(self) -> dict[str, Any]:
        """
        Analyze point features against partition buffer.

        For point features, we count how many points fall within the buffer.

        Returns:
            Dictionary with point_count key
        """
        point_count = self._count_points_in_buffer()
        return {"point_count": point_count}

    def _count_points_in_buffer(self) -> int:
        """
        Count point features that fall within the buffer.

        Returns:
            Number of points within the buffer
        """
        buffer_geom = self._get_buffer_geometry(self.buffer_fc)
        if buffer_geom is None:
            print("Buffer geometry could not be retrieved.")
            return 0

        point_count = 0
        with arcpy.da.SearchCursor(self.feature_layer, ["SHAPE@"]) as cursor:
            for (geom,) in cursor:
                if buffer_geom.contains(geom):
                    point_count += 1

        return point_count
