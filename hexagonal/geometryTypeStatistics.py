# Libraries

import arcpy

from collections import defaultdict

from hexagonal.dataTypeStatistics import VectorStatistics
from hexagonal.validationStatus import Rule, Severity

##########################
# Classes
##########################


class PolygonStatistics(VectorStatistics):

    RULES = [
        Rule("total_area", "eqd", 0, Severity.ERROR),
        Rule(
            "min_area",
            "ratio",
            [0.3, 0.6],
            [Severity.SUCCESS, Severity.WARNING, Severity.ERROR],
        ),
        Rule(
            "max_area",
            "ratio",
            [0.3, 0.6],
            [Severity.SUCCESS, Severity.WARNING, Severity.ERROR],
        ),
        Rule(
            "avg_area",
            "ratio",
            [0.3, 0.6],
            [Severity.SUCCESS, Severity.WARNING, Severity.ERROR],
        ),
    ] + VectorStatistics.RULES

    ##########################
    # Main functions
    ##########################

    def get_stats(self, fc: str) -> dict:
        r1 = super().get_stats(fc=fc)
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


class LineStatistics(VectorStatistics):

    RULES = [
        Rule(
            "total_length",
            "ratio",
            [0.3, 0.6],
            [Severity.SUCCESS, Severity.WARNING, Severity.ERROR],
        ),
        Rule(
            "min_length",
            "ratio",
            [0.3, 0.6],
            [Severity.SUCCESS, Severity.WARNING, Severity.ERROR],
        ),
        Rule(
            "max_length",
            "ratio",
            [0.3, 0.6],
            [Severity.SUCCESS, Severity.WARNING, Severity.ERROR],
        ),
        Rule(
            "avg_length",
            "ratio",
            [0.3, 0.6],
            [Severity.SUCCESS, Severity.WARNING, Severity.ERROR],
        ),
        Rule(
            "dangle_count_absolute",
            "ratio",
            [0.3, 0.6],
            [Severity.SUCCESS, Severity.WARNING, Severity.ERROR],
        ),
        Rule(
            "dangle_count_relative",
            "ratio",
            [0.3, 0.6],
            [Severity.SUCCESS, Severity.WARNING, Severity.ERROR],
        ),
    ] + VectorStatistics.RULES

    ##########################
    # Main functions
    ##########################

    def get_stats(self, fc: str) -> dict:
        r1 = super().get_stats(fc=fc)
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
                if length:
                    total_length += length
                    min_length = min(min_length, length)
                    max_length = max(max_length, length)

                if geom:
                    fp, lp = geom.firstPoint, geom.lastPoint

                    for p in [fp, lp]:
                        point_key = (p.X, p.Y)
                        points[point_key].append(oid)

        if count == 0:
            return {
                "total_length": 0,
                "min_length": 0,
                "max_length": 0,
                "avg_length": 0,
                "dangle_count_absolute": 0,
                "dangle_count_relative": 0,
            }

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


class PointStatistics(VectorStatistics):

    ##########################
    # Main functions
    ##########################

    def get_stats(self, fc: str) -> dict:
        r1 = super().get_stats(fc=fc)
        r2 = {}
        return {**r1, **r2}

    ##########################
    # Helper functions
    ##########################
