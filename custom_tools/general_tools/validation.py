############################
# Libraries
############################

import arcpy

############################
# Functionality
############################

def check_valid_feature_class(feature_class: str, level: int) -> bool:
    """
    Checks if the given feature class is valid.

    Args:
        feature_class (str): The path to the feature class to check
        level (int): The level of validation to perform, need to pass #level of controls
    
    Returns:
        bool: True if the feature class is valid, False otherwise
    """
    levels = [
        feature_class_exists(feature_class),
        has_data(feature_class),
    ]

    if level > len(levels):
        raise ValueError(
            f"Invalid level: {level}. Level must be between 1 and {len(levels)}"
        )

    return all(levels[:level])

############################
# Helpers
############################

def feature_class_exists(feature_class: str) -> bool:
    """
    Checks if the given feature class exists.

    Args:
        feature_class (str): The path to the feature class to check

    Returns:
        bool: True if the feature class exists, False otherwise
    """
    try:
        return arcpy.Exists(dataset=feature_class)
    except:
        return False

def has_data(feature_class: str) -> bool:
    """
    Checks if the given feature class has any features.

    Args:
        feature_class (str): The path to the feature class to check

    Returns:
        bool: True if the feature class has data, False otherwise
    """
    try:
        return int(arcpy.management.GetCount(feature_class)[0]) > 0
    except:
        return False
