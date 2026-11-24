# Base class for feature type-specific partition analysis

from abc import ABC, abstractmethod
from typing import Any

import arcpy


class FeatureChecker(ABC):
    """Base class for feature type-specific partition analysis."""

    def __init__(
        self,
        feature_layer: str,
        fc: str,
        id_field: str,
        temp_layer_name: str = "temp_layer",
    ) -> None:
        """
        Initialize the feature checker.

        Args:
            feature_layer: The feature layer to analyze
            fc: Feature class with buffer geometry
            id_field: The field used to identify features in the feature layer
            temp_layer_name: Name for temporary layers
        """
        self.feature_layer = feature_layer
        self.fc = fc
        self.id_field = id_field
        self.temp_layer_name = temp_layer_name

    @abstractmethod
    def analyze(self) -> dict[str, Any]:
        """
        Analyze the feature layer against the partition buffer.

        Returns:
            Dictionary containing analysis results specific to feature type
        """
        pass

    @staticmethod
    def _get_geometry(fc: str) -> Any | None:
        """Retrieve the geometry from the feature class."""
        try:
            with arcpy.da.SearchCursor(fc, ["SHAPE@"]) as cursor:
                geom = next(cursor)[0]
                return geom
        except StopIteration:
            print("Feature class is empty.")
            return None
