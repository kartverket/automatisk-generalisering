# Libraries

import arcpy

from hexagonal.validationStatus import Rule, Severity

##########################
# Classes
##########################


class VectorStatistics:

    ##########################
    # Rules
    ##########################

    RULES = [
        Rule("exists", "eqn", True, Severity.ERROR),
        Rule("has_data", "eqn", True, Severity.ERROR),
        Rule(
            "object_count",
            "ratio",
            [0.3, 0.6],
            [Severity.SUCCESS, Severity.WARNING, Severity.ERROR],
        ),
        Rule(
            "vertex_count",
            "ratio",
            [0.3, 0.6],
            [Severity.SUCCESS, Severity.WARNING, Severity.ERROR],
        ),
        Rule("null_count", "eqn", 0, Severity.ERROR),
    ]

    ##########################
    # Main functions
    ##########################

    def get_stats(self, fc: str) -> dict:
        exists = self.data_exists(fc)

        object_count = self.get_num_obj(fc) if exists else 0
        vertex_count, null_count = self.get_geom_data(fc) if exists else (0, 0)

        return {
            "exists": exists,
            "has_data": object_count > 0,
            "object_count": object_count,
            "vertex_count": vertex_count,
            "null_count": null_count,
        }

    ##########################
    # Helper functions
    ##########################

    def data_exists(self, data: str) -> bool:
        return arcpy.Exists(data)

    def feature_class_has_data(self, fc: str) -> bool:
        return self.get_num_obj(fc=fc) > 0

    def get_num_obj(self, fc: str) -> int:
        return int(arcpy.management.GetCount(fc)[0])

    def get_geom_data(self, fc: str) -> tuple[int, int]:
        total_vertices, null_obj = 0, 0
        with arcpy.da.SearchCursor(fc, ["SHAPE@"]) as cursor:
            for (geom,) in cursor:
                if not geom:
                    null_obj += 1
                else:
                    total_vertices += geom.pointCount
        return total_vertices, null_obj
