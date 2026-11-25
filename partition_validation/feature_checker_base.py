# Libraries

from abc import ABC, abstractmethod
from typing import Any

import arcpy

##########################
# Class
##########################


class FeatureChecker(ABC):
    """Base class for feature type-specific partition analysis."""

    def __init__(
        self,
        feature_layer: str,
        area_fc: str,
        id_field: str,
        temp_layer_name: str = "temp_layer",
    ) -> None:
        """
        Initialize the feature checker.

        Args:
            feature_layer: The feature layer to analyze
            area_fc: Feature class with buffer geometry
            id_field: The field used to identify features in the feature layer
            temp_layer_name: Name for temporary layers
        """
        self.feature_layer = feature_layer
        self.area_fc = area_fc
        self.id_field = id_field
        self.temp_layer_name = temp_layer_name

    @abstractmethod
    def analyze(self) -> dict[str, Any]:
        """
        Analyze the feature layer against the area geometry.

        Returns:
            Dictionary containing analysis results specific to feature type
        """
        pass

    def _get_area_geometry(self) -> Any | None:
        """Retrieve the geometry from the area feature class."""
        try:
            with arcpy.da.SearchCursor(self.area_fc, ["SHAPE@"]) as cursor:
                geom = next(cursor)[0]
                return geom
        except StopIteration:
            print("Feature class is empty.")
            return None
