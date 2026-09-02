# Libraries

import arcpy  # TODO: Til slutt skal ikke denne ha arcpy

##########################
# Classes
##########################

# TODO: Skal gå an å si "valider road", og så vet den road -> line -> vector
# TODO: Finn ut av hvordan det skal logges
# TODO: Gi en status hvis veldig stor endring
# TODO: Legg inn diff


class VectorValidator:

    ##########################
    # Main functions
    ##########################

    def validate(self, fc: str) -> dict:
        exists = self.data_exists(fc)

        object_count = self.get_num_obj(fc) if exists else 0
        vertex_count, null_count = self.get_geom_data(fc)

        return {
            "exists": exists,
            "is_valid": object_count > 0,
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
        total_vertices = 0
        null_obj = 0
        with arcpy.da.SearchCursor(fc, ["SHAPE@"]) as cursor:
            for (geom,) in cursor:
                if not geom:
                    null_obj += 1
                else:
                    total_vertices += geom.pointCount
        return total_vertices, null_obj


    ##########################
    

    def print_validation_results(self, results: dict, level: int = 0) -> None:
        """
        Print the validation results in a readable format.

        Args:
            results (dict): A dictionary containing validation results
            level (int): The current level of indentation for nested results
        """
        if level == 0:
            print(f"\n{'==='*20}\n\nValidation Results:\n")
        level_indicator = "   "
        for key, value in results.items():
            if isinstance(value, dict):
                print(f"{level_indicator * level}{key}")
                self.print_validation_results(value, level + 1)
            else:
                print(f"{level_indicator * level}- {key}: {value}")
        if level == 0:
            print(f"\n{'==='*20}\n")
