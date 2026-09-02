# Libraries

import arcpy

from collections import defaultdict

from hexagonal.dataTypeValidators import VectorValidator

##########################
# Classes
##########################


class PolygonValidator(VectorValidator):

    ##########################
    # Main functions
    ##########################

    def validate(self, fc: str) -> dict:
        r1 = super().validate(fc=fc)
        r2 = self.get_poly_stats(fc=fc)
        return {**r1, **r2}

    ##########################
    # Helper functions
    ##########################

    def get_poly_stats(self, fc: str) -> dict:
        count = 0
        total_area = 0.0
        min_area = float("inf")
        max_area = float("-inf")

        with arcpy.da.SearchCursor(fc, ["SHAPE@AREA"]) as cursor:
            for (area,) in cursor:
                count += 1
                total_area += area
                min_area = min(min_area, area)
                max_area = max(max_area, area)

        if count == 0:
            return {"total_area": 0, "min_area": 0, "max_area": 0, "avg_area": 0}

        return {
            "total_area": total_area,
            "min_area": min_area,
            "max_area": max_area,
            "avg_area": total_area / count,
        }


class LineValidator(VectorValidator):

    ##########################
    # Main functions
    ##########################

    def validate(self, fc: str) -> dict:
        r1 = super().validate(fc=fc)
        r2 = self.get_line_stats(fc=fc)
        return {**r1, **r2}

    ##########################
    # Helper functions
    ##########################

    def get_line_stats(self, fc: str) -> dict:
        count = 0
        total_length = 0.0
        min_length = float("inf")
        max_length = float("-inf")

        points = defaultdict(list)

        with arcpy.da.SearchCursor(fc, ["OID@", "SHAPE@", "SHAPE@LENGTH"]) as cursor:
            for oid, geom, length in cursor:
                count += 1
                total_length += length
                min_length = min(min_length, length)
                max_length = max(max_length, length)

                fp, lp = geom.firstPoint, geom.lastPoint

                for p in [fp, lp]:
                    point_key = (p.X, p.Y)
                    points[point_key].append(oid)

        if count == 0:
            return {"total_length": 0, "min_length": 0, "max_length": 0, "avg_length": 0, "dangle_count_absolute": 0, "dangle_count_relative": 0}
    
        # Estimate dangles
        abs_dangles = sum(1 for oids in points.values() if len(oids) == 1)

        return {
            "total_length": total_length,
            "min_length": min_length,
            "max_length": max_length,
            "avg_length": total_length / count,
            "dangle_count_absolute": abs_dangles,
            "dangle_count_relative": abs_dangles / count,
        }
