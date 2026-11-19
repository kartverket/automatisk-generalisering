# Line feature-specific partition analyzer

from collections import defaultdict
from typing import Any

import arcpy

from partition_validation.feature_checker_base import FeatureChecker


class LineFeatureChecker(FeatureChecker):
    """Analyzer for line features in partition validation."""

    def analyze(self) -> dict[str, Any]:
        """
        Analyze line features against partition buffer.

        For line features, we detect dangles (line endpoints within the buffer).

        Returns:
            Dictionary with dangle_count key
        """
        end_points = self._get_relevant_end_points()
        return {"dangle_count": len(end_points)}

    def _get_relevant_end_points(self) -> defaultdict:
        """
        Get start and end points of lines that fall within the buffer.

        Returns:
            Dictionary mapping (x, y) coordinates to list of line OIDs
        """
        end_points = defaultdict(list)

        buffer_geom = self._get_buffer_geometry(self.buffer_fc)
        if buffer_geom is None:
            print("Buffer geometry could not be retrieved.")
            return end_points

        with arcpy.da.SearchCursor(self.feature_layer, ["OID@", "SHAPE@"]) as cursor:
            for oid, geom in cursor:
                start_point = geom.firstPoint
                end_point = geom.lastPoint

                start_geom = arcpy.PointGeometry(start_point, geom.spatialReference)
                end_geom = arcpy.PointGeometry(end_point, geom.spatialReference)

                if buffer_geom.contains(start_geom):
                    end_points[(start_point.X, start_point.Y)].append(oid)
                if buffer_geom.contains(end_geom):
                    end_points[(end_point.X, end_point.Y)].append(oid)

        return end_points
