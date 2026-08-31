# Libraries

import arcpy

from collections import defaultdict


##########################
# Class
##########################


class DataValidator:
    def __init__(self, feature: str, geometry_type: str):
        self.feature = feature
        self.geometry_type = geometry_type

        self.feature_validators = {
            "building": [],
            "land_use": [],
            "river": [],
            "road": [],
        }

        self.geometry_validators = {
            "polygon": [self.validate_polygon_data],
            "line": [self.validate_line_data],
            "point": [self.validate_point_data],
        }


    ##########################
    # Main functions
    ##########################


    def feature_class_exists(self, fc: str) -> bool:
        """
        Check if the input feature class exists in the geodatabase.

        Args:
            fc (str): The path to the input feature class

        Returns:
            bool: True if the feature class exists, False otherwise
        """
        return arcpy.Exists(fc)

    def feature_class_has_data(self, fc: str) -> bool:
        """
        Check if the input feature class contains any features.

        Args:
            fc (str): The path to the input feature class

        Returns:
            bool: True if the feature class contains any features, False otherwise
        """
        return self._get_num_obj(fc) > 0

    def validation_orchestrator(
        self, output_fc: str, input_fc: str | None = None
    ) -> None:
        """
        Orchestrates the validation process for the given combination of feature and geometry type.

        Args:
            output_fc (str): The path to the output feature class
            input_fc (str | None): The path to the input feature class (optional)
        """
        validations = [self.validate_vector]

        validations.extend(self.geometry_validators.get(self.feature_type, []))
        validations.extend(self.feature_validators.get(self.feature, []))

        feature_classes = (
            {"input": input_fc, "output": output_fc}
            if input_fc
            else {"output": output_fc}
        )

        results = defaultdict(dict)

        for key, fc in feature_classes.items():
            for validation in validations:
                results[key][validation.__name__] = validation(fc)

        print(f"Validation results:\n{dict(results)}")

    ##########################
    # Helper functions
    ##########################

    def validate_vector(self, fc: str) -> dict:
        exists = self.feature_class_exists(fc)

        if exists:
            object_count = self._get_num_obj(fc)
            vertex_count = self._get_num_vertices(fc)
        else:
            object_count = 0
            vertex_count = 0

        return {
            "exists": exists,
            "is_valid": object_count > 0,
            "object_count": object_count,
            "vertex_count": vertex_count,
        }

    def validate_polygon_data(self, fc: str) -> dict:
        return self._get_polygon_area_stats(fc)

    def validate_line_data(self, fc: str) -> dict:
        return {}

    def validate_point_data(self, fc: str) -> dict:
        return {}

    ##########################
    # Toolbox
    ##########################

    def _get_num_obj(self, fc: str) -> int:
        """
        Get the number of objects in the feature class.

        Args:
            fc (str): The path to the feature class

        Returns:
            int: The number of objects in the feature class
        """
        return int(arcpy.management.GetCount(fc)[0])

    def _get_num_vertices(self, fc: str) -> int:
        """
        Get the number of vertices in the feature class.

        Args:
            fc (str): The path to the feature class

        Returns:
            int: The number of vertices in the feature class
        """
        total_vertices = 0

        with arcpy.da.SearchCursor(fc, ["SHAPE@"]) as cursor:
            for (geometry,) in cursor:
                if geometry:
                    total_vertices += geometry.pointCount

        return total_vertices

    def _get_polygon_area_stats(self, fc: str) -> dict:
        """
        Get statistics about the areas of polygons in the feature class.

        Args:
            fc (str): The path to the feature class

        Returns:
            dict: A dictionary containing area statistics
        """
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
            return {"min_area": 0, "max_area": 0, "avg_area": 0}

        return {
            "min_area": min_area,
            "max_area": max_area,
            "avg_area": total_area / count,
        }


##########################


if __name__ == "__main__":

    feature = "land_use"
    geometry_type = "polygon"
    output_fc = r"C:\Users\hjejak\Documents\ArcGIS\Projects\Automatisk_Generalisering\AG_test.gdb\Arealdekke"
    input_fc = r"C:\Users\hjejak\Documents\ArcGIS\Projects\Automatisk_Generalisering\AG_test.gdb\Arealdekke_input"

    validator = DataValidator(feature=feature, geometry_type=geometry_type)

    validator.validation_orchestrator(output_fc=output_fc, input_fc=input_fc)
