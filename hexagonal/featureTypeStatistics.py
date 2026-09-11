# Libraries

import arcpy

from collections import Counter

from generalization.n10.arealdekke.parameters.parameter_worker import get_min_area
from hexagonal.geometryTypeStatistics import LineStatistics, PolygonStatistics
from hexagonal.validationStatus import Rule, Severity

##########################
# Classes
##########################


class RoadStatistics(LineStatistics):

    RULES = [
        Rule(
            "road_categories",
            "ratio",
            [0.3, 0.6],
            [Severity.SUCCESS, Severity.WARNING, Severity.ERROR],
        ),
    ] + LineStatistics.RULES

    ##########################
    # Main functions
    ##########################

    def get_stats(self, fc: str) -> dict:
        r1 = super().get_stats(fc=fc)
        r2 = self.get_num_types(fc=fc)
        return {**r1, **r2}

    ##########################
    # Helper functions
    ##########################

    def get_num_types(self, fc: str) -> dict:
        field = "vegkategori"

        try:
            with arcpy.da.SearchCursor(fc, [field]) as cursor:
                counts = Counter([row[0] for row in cursor])
        except Exception as e:
            print(f"Error collecting landuse stats: {e}")
            counts = Counter()

        return {"road_categories": dict(counts)}


class RiverStatistics(LineStatistics):

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

    # ...


class LanduseStatistics(PolygonStatistics):

    RULES = [
        Rule(
            "landuse_categories",
            "ratio",
            [0.3, 0.6],
            [Severity.SUCCESS, Severity.WARNING, Severity.ERROR],
        ),
    ] + PolygonStatistics.RULES

    def __init__(self, scale: str):
        self.scale: str = scale

    ##########################
    # Main functions
    ##########################

    def get_stats(self, fc: str) -> dict:
        r1 = super().get_stats(fc=fc)
        r2 = self.get_landuse_stats(fc=fc)
        return {**r1, **r2}

    ##########################
    # Helper functions
    ##########################

    def get_landuse_stats(self, fc: str) -> dict:
        field = "arealdekke"
        min_count = 0
        field_count = Counter()

        try:
            minimum_area: dict = get_min_area(map_scale=self.scale).features

            with arcpy.da.SearchCursor(fc, ["SHAPE@", field]) as cursor:
                for g, f in cursor:
                    if g.area < minimum_area.get(f, 0):
                        min_count += 1
                    field_count[f] += 1
        except Exception as e:
            print(f"Error collecting landuse stats: {e}")

        return {"landuse_categories": dict(field_count), "minimum_count": min_count}
