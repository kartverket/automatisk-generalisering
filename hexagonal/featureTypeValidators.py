# Libraries

import arcpy

from collections import Counter

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
        r2 = self.get_num_types(fc=fc)
        return {**r1, **r2}

    ##########################
    # Helper functions
    ##########################

    def get_num_types(self, fc: str) -> dict:
        field = "arealdekke"

        try:
            with arcpy.da.SearchCursor(fc, [field]) as cursor:
                counts = Counter([row[0] for row in cursor])
            print("Landuse stats collected")
        except Exception as e:
            print(f"Error collecting landuse stats: {e}")
            counts = Counter()

        return {"landuse_categories": dict(counts)}


##########################


if __name__ == "__main__":
    
    validator = LanduseValidator()
    for p in [path_1, path_2, path_3]:
        results = validator.validate(fc=p)
        validator.save_validation_results(results=results)
