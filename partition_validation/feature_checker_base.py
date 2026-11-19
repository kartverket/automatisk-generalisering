# Base class for feature type-specific partition analysis

from abc import ABC, abstractmethod
from typing import Any

import arcpy


class FeatureChecker(ABC):
    """Base class for feature type-specific partition analysis."""

    def __init__(
        self,
        feature_layer: str,
        buffer_fc: str,
        temp_layer_name: str = "temp_layer",
    ) -> None:
        """
        Initialize the feature checker.

        Args:
            feature_layer: The feature layer to analyze
            buffer_fc: The buffer feature class to intersect with
            temp_layer_name: Name for temporary layers
        """
        self.feature_layer = feature_layer
        self.buffer_fc = buffer_fc
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
    def _get_buffer_geometry(buffer_fc: str) -> Any | None:
        """Retrieve the geometry from the buffer feature class."""
        try:
            with arcpy.da.SearchCursor(buffer_fc, ["SHAPE@"]) as buffer_cursor:
                buffer_geom = next(buffer_cursor)[0]
                return buffer_geom
        except StopIteration:
            print("Buffer feature class is empty.")
            return None
