# ========================
# Libraries
# ========================


import arcpy

arcpy.env.overwriteOutput = True

from custom_tools.decorators.timing_decorator import timing_decorator


# ========================
# Program
# ========================


@timing_decorator
def aggregate_areas(input_data: str, feature: str) -> None:
    """
    Function that aggregates small polygons located near each other and dissolves it into one larger feature.

    Process:
    1) Fetches the features of the relevant feature type and select the small ones
    2) Identify close, topologically relations between features
    If any:
    3) Aggregate the near features together into larger, like taking a rubber band around them

    Args:
        input_data (str): Feature class to be edited
        feature (str): The feature / land use type to be edited
    """
    return


# ========================

if __name__ == "__main__":
    aggregate_areas()
