##########################
# Constants
##########################


first_level_features = {1: "vector", 2: "raster"}

second_level_features = {
    # second level feature id: (feature_type, first level feature id)
    1: ("point", 1),
    2: ("line", 1),
    3: ("polygon", 1),
}

third_level_features = {
    # feature_type: second level feature id
    "admin": 3,
    "building": 3,
    "facility": 1,
    "land_use": 3,
    "landforms": 2,
    "railway": 2,
    "river": 2,
    "road": 2,
}


##########################
# Classes
##########################


class FeatureDependencies:
    def __init__(self, feature: str):
        self.feature = feature

    ##########################
    # Main functions
    ##########################

    def get_dependencies(self) -> list[str]:
        """
        Find all features, geometry types and data types associated with the given feature.
        The return from this function is a list of str / list[str] with the following structure:
            - First element: first level feature (str), e.i. data type
            - Second element: second level feature (str | list[str]), e.i. geometry type
            - Third element: third level features (str | list[str]), e.i. specific feature

        Returns:
            list[str]: A list of dependencies for the given feature
        """
        if self.feature in third_level_features:
            return self._get_upward_dependencies(
                feature=self.feature, second_level_id=third_level_features[self.feature]
            )
        second_level = {
            f: [id_down, id_up] for id_down, (f, id_up) in second_level_features.items()
        }
        if self.feature in second_level:
            return self._get_ladder_dependencies(
                feature=self.feature, ladder_info=second_level[self.feature]
            )
        first_level = {f: f_id for f_id, f in first_level_features.items()}
        if self.feature in first_level:
            return self._get_downward_dependencies(
                feature=self.feature, first_level_id=first_level[self.feature]
            )
        raise ValueError(f"Feature '{self.feature}' is not a valid feature type.")

    ##########################
    # Helper functions
    ##########################

    def _get_upward_dependencies(self, feature: str, second_level_id: int) -> list[str]:
        """
        Get dependencies higher in the data type hierarchy for the given feature.

        Args:
            feature (str): Feature in the third level of the hierarchy (e.g., "building", "road", etc.)
            second_level_id (int): The ID of the second level feature associated with the given feature

        Returns:
            list[str]: A list of dependencies for the given feature
        """
        second_feature, second_cat = second_level_features.get(second_level_id)
        first_feature = first_level_features.get(second_cat)
        return [first_feature, second_feature, feature]

    def _get_ladder_dependencies(
        self, feature: str, ladder_info: list[int]
    ) -> list[str]:
        """
        Get dependencies higher and lower in the data type hierarchy for the given feature.

        Args:
            feature (str): Feature in the second level of the hierarchy (e.g., "line", "polygon", etc.)
            ladder_info (list[int]): A list containing the IDs to connected features in the hierarchy (downward and upward) for the feature

        Returns:
            list[str]: A list of dependencies for the given feature
        """
        id_down, id_up = ladder_info
        third_features = [
            f for f, f_id in third_level_features.items() if f_id == id_down
        ]
        first_feature = first_level_features.get(id_up)
        return [first_feature, feature, third_features]

    def _get_downward_dependencies(
        self, feature: str, first_level_id: int
    ) -> list[str]:
        """
        Get dependencies lower in the data type hierarchy for the given feature.

        Args:
            feature (str): Feature in the first level of the hierarchy (e.g., "vector", "raster", etc.)
            first_level_id (int): The ID for the first level feature

        Returns:
            list[str]: A list of dependencies for the given feature
        """
        second_to_first = {
            f: f_id
            for f_id, (f, first_id) in second_level_features.items()
            if first_id == first_level_id
        }
        second_features = list(second_to_first.keys())
        third_level_keys = set(second_to_first.values())
        third_features = [
            f for f, f_id in third_level_features.items() if f_id in third_level_keys
        ]
        return [feature, second_features, third_features]
