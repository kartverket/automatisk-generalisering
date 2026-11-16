# Libraries

import arcpy

from collections import Counter

from data_orchestrator_2.constants.columns import ColumnName
from generalization.n10.arealdekke.parameters.parameter_worker import (
    get_min_area,
    MinArea,
)
from geometry_validation.geometryTypeStatistics import LineStatistics, PolygonStatistics
from geometry_validation.validationStatus import Rule, Severity

##########################
# Classes
##########################


class RoadStatistics(LineStatistics):
    """
    RoadStatistics class is responsible for gathering statistics for road datasets
    and defining the rules that all road datasets must satisfy to be considered valid.
    This data must also pass all the tests defined for line datasets.
    """

    RULES: list[Rule] = [
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
        r1 = super().get_stats(fc=fc)  # vector + line statistics
        r2 = self.get_num_types(fc=fc)  # road statistics
        return {**r1, **r2}

    ##########################
    # Helper functions
    ##########################

    def get_num_types(self, fc: str) -> dict:
        field = ColumnName.VEGKATEGORI.value
        counts = Counter()

        try:
            with arcpy.da.SearchCursor(fc, [field]) as cursor:
                counts = Counter(row[0] for row in cursor)
        except Exception as e:
            print(f"Error collecting road category stats: {e}")

        return {f"{field}": dict(counts)}


class RiverStatistics(LineStatistics):
    """
    RiverStatistics class is responsible for gathering statistics for river datasets
    and defining the rules that all river datasets must satisfy to be considered valid.
    This data must also pass all the tests defined for line datasets.
    """

    ##########################
    # Main functions
    ##########################

    def get_stats(self, fc: str) -> dict:
        r1 = super().get_stats(fc=fc)  # vector + line statistics
        r2 = {}  # river statistics
        return {**r1, **r2}

    ##########################
    # Helper functions
    ##########################

    # ...


class LanduseStatistics(PolygonStatistics):
    """
    LanduseStatistics class is responsible for gathering statistics for landuse datasets
    and defining the rules that all landuse datasets must satisfy to be considered valid.
    This data must also pass all the tests defined for polygon datasets.
    """

    RULES: list[Rule] = [
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
        r1 = super().get_stats(fc=fc)  # vector + polygon statistics
        r2 = self.get_landuse_stats(fc=fc)  # landuse statistics
        return {**r1, **r2}

    ##########################
    # Helper functions
    ##########################

    def get_landuse_stats(self, fc: str) -> dict:
        field = ColumnName.AREALDEKKE.value
        min_count = 0
        field_count = Counter()

        try:
            minimum_area: int | MinArea = get_min_area(map_scale=self.scale)

            if isinstance(minimum_area, int):
                raise ValueError(
                    "Expected minimum_area to be a MinArea instance, got int instead."
                )

            minimum_features: dict = minimum_area.features

            with arcpy.da.SearchCursor(fc, ["SHAPE@", field]) as cursor:
                for g, f in cursor:
                    if g.area < minimum_features.get(f, 0):
                        min_count += 1
                    field_count[f] += 1
        except Exception as e:
            print(f"Error collecting landuse stats: {e}")

        return {"landuse_categories": dict(field_count), "minimum_count": min_count}
