# Factory for selecting the appropriate feature checker based on geometry type

from typing import Literal

import arcpy

from partition_validation.feature_checker_base import FeatureChecker
from partition_validation.line_feature_checker import LineFeatureChecker
from partition_validation.point_feature_checker import PointFeatureChecker
from partition_validation.polygon_feature_checker import PolygonFeatureChecker


class FeatureCheckerFactory:
    """Factory for creating feature-type-specific checkers."""

    @staticmethod
    def create(
        feature_layer: str,
        fc: str,
        id_field: str,
        feature_type: Literal["point", "line", "polygon"] | None = None,
    ) -> FeatureChecker:
        """
        Create a feature checker based on feature type.

        Args:
            feature_layer: The feature layer to analyze
            fc: The feature class to intersect with
            id_field: The field used to identify features in the feature layer
            feature_type: Type of feature ("point", "line", "polygon").
                         If None, will be determined from the feature layer.

        Returns:
            Appropriate FeatureChecker subclass instance

        Raises:
            ValueError: If feature type is unknown or not supported
        """
        if feature_type is None:
            feature_type = FeatureCheckerFactory._detect_feature_type(feature_layer)

        checker_map = {
            "point": PointFeatureChecker,
            "line": LineFeatureChecker,
            "polygon": PolygonFeatureChecker,
        }

        if feature_type not in checker_map:
            raise ValueError(
                f"Unknown feature type: {feature_type}. "
                f"Supported types: {', '.join(checker_map.keys())}"
            )

        return checker_map[feature_type](feature_layer, fc, id_field)

    @staticmethod
    def _detect_feature_type(feature_layer: str) -> Literal["point", "line", "polygon"]:
        """
        Detect the geometry type of a feature class.

        Args:
            feature_layer: The feature layer to analyze

        Returns:
            String indicating geometry type ("point", "line", or "polygon")

        Raises:
            ValueError: If geometry type is not point, line, or polygon
        """
        describe = arcpy.Describe(feature_layer)
        geometry_type = describe.shapeType.lower()

        type_mapping = {
            "point": "point",
            "polyline": "line",
            "polygon": "polygon",
        }

        if geometry_type not in type_mapping:
            raise ValueError(
                f"Unsupported geometry type '{geometry_type}' in {feature_layer}"
            )

        return type_mapping[geometry_type]  # type: ignore
