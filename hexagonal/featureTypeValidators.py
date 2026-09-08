# Libraries

import arcpy

from collections import Counter

from generalization.n10.arealdekke.parameters.parameter_worker import get_min_area
from hexagonal.geometryTypeValidators import LineValidator, PolygonValidator

##########################
# Classes
##########################


class RoadValidator(LineValidator):

    ##########################
    # Main functions
    ##########################

    def validate(self, fc: str) -> dict:
        r1 = super().validate(fc=fc)
        r2 = self.get_num_types(fc=fc)
        return {**r1, **r2}

    ##########################
    # Helper functions
    ##########################

    def get_num_types(self, fc: str) -> dict:
        field = "vegkategori"

        with arcpy.da.SearchCursor(fc, [field]) as cursor:
            counts = Counter([row[0] for row in cursor])

        print("Road stats collected")

        return {"road_categories": dict(counts)}


class RiverValidator(LineValidator):

    ##########################
    # Main functions
    ##########################

    def validate(self, fc: str) -> dict:
        r1 = super().validate(fc=fc)
        r2 = {}
        return {**r1, **r2}

    ##########################
    # Helper functions
    ##########################

    # ...


class LanduseValidator(PolygonValidator):

    ##########################
    # Main functions
    ##########################

    def validate(self, fc: str) -> dict:
        r1 = super().validate(fc=fc)
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

            print("Landuse stats collected")
        except Exception as e:
            print(f"Error collecting landuse stats: {e}")

        return {"landuse_categories": dict(field_count), "minimum_count": min_count}


##########################


if __name__ == "__main__":
    
    validator = LanduseValidator(scale="N10")
    for p in [path_1, path_2, path_3]:
        results = validator.validate(fc=p)
        validator.save_validation_results(results=results)
