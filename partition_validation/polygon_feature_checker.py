# Polygon feature-specific partition analyzer

from typing import Any

import arcpy

from partition_validation.feature_checker_base import FeatureChecker


class PolygonFeatureChecker(FeatureChecker):
    """Analyzer for polygon features in partition validation."""

    def analyze(self) -> dict[str, Any]:
        """
        Analyze polygon features against area geometry.

        **For polygon features, we detect:**
        - Count overlapping polygons
        - Calculate overlap area

        Returns:
            Dictionary with statistics for the analyzed feature class
        """
        overlap_count = 0
        total_overlap_area = 0.0

        geom = self._get_area_geometry()
        if geom is None:
            print("Feature class geometry could not be retrieved.")
            return {"overlap_count": 0, "overlap_area": 0.0}

        with arcpy.da.SearchCursor(self.feature_layer, ["SHAPE@"]) as cursor:
            for (poly_geom,) in cursor:
                if geom.overlaps(poly_geom) or geom.contains(poly_geom):
                    overlap_count += 1
                    # Calculate intersection area
                    intersection = geom.intersect(poly_geom, 2)  # 2 = Area dimension
                    if intersection:
                        total_overlap_area += intersection.area

        return {
            "overlap_count": overlap_count,
            "overlap_area": total_overlap_area,
        }
