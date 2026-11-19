# Polygon feature-specific partition analyzer

from typing import Any

import arcpy

from partition_validation.feature_checker_base import FeatureChecker


class PolygonFeatureChecker(FeatureChecker):
    """Analyzer for polygon features in partition validation."""

    def analyze(self) -> dict[str, Any]:
        """
        Analyze polygon features against partition buffer.

        For polygon features, we count overlapping polygons and calculate
        overlap area.

        Returns:
            Dictionary with overlap_count and overlap_area keys
        """
        overlap_count = 0
        total_overlap_area = 0.0

        buffer_geom = self._get_buffer_geometry(self.buffer_fc)
        if buffer_geom is None:
            print("Buffer geometry could not be retrieved.")
            return {"overlap_count": 0, "overlap_area": 0.0}

        with arcpy.da.SearchCursor(self.feature_layer, ["SHAPE@"]) as cursor:
            for (geom,) in cursor:
                if buffer_geom.overlaps(geom) or buffer_geom.contains(geom):
                    overlap_count += 1
                    # Calculate intersection area
                    intersection = buffer_geom.intersect(geom, 2)  # 2 = Area dimension
                    if intersection:
                        total_overlap_area += intersection.area

        return {
            "overlap_count": overlap_count,
            "overlap_area": total_overlap_area,
        }
