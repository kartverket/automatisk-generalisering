# Module imports:
import arcpy
from composition_configs import core_config
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10

# Category tools:
from generalization.n10.arealdekke.orchestrator.simplify_land_use import (
    simplify_and_smooth_polygon,
)
from generalization.n10.arealdekke.category_tools.buff_small_polygon_segments import (
    buff_small_polygon_segments,
)


class Category:

    def __init__(
        self,
        title: str,
        operations: list,
        accessibility: bool,
        order: int,
        map_scale: str,
    ):

        # Extracts inputs and saves them within object
        self.__title = title
        self.__operations = operations or []
        self.__accessibility = accessibility
        self.__order = order
        self.__map_scale = map_scale

        # Dictionary with all tools available to the category objects
        self.cat_tools = {
            "simplify_and_smooth": simplify_and_smooth_polygon,
            "buff_small_segments": buff_small_polygon_segments,
        }

        for item in self.__operations:

            # Checks if each operation is written correctly (test can be improved later)
            if item not in list(self.cat_tools.keys()):
                raise Exception(f"Incorrect syntax in yml file. Object:{self.__title}")

        # Creates layer for the category. Data inserted into it in setter function.
        self.lyr = f"{self.__title}_lyr"

    # ========================
    # Main functions
    # ========================

    def process_category(
        self, input_data: str, locked_layers: str, processed_layer: str
    ) -> bool:

        reinsert = False

        # File that will be overwritten with new input for each iteration.
        output_lyr = f"{self.__title}_output_lyr"

        if self.__operations:
            # Inserts the arealdekke input data into the layer.
            arcpy.management.MakeFeatureLayer(input_data, self.lyr)

            # Iterates through the operations needed for each category.
            for operation in self.__operations:

                # Calls function from dictionary
                self.cat_tools[operation](
                    self.__title, self.lyr, output_lyr, locked_layers, self.__map_scale
                )

                # Updates the layer that will be passed on to the next operation to be the output.
                arcpy.management.MakeFeatureLayer(output_lyr, self.lyr)

            # Marks the process as completed and insert the final layer into the output layer.
            reinsert = True
            arcpy.management.MakeFeatureLayer(
                in_features=self.lyr, out_layer=processed_layer
            )

        # Once done, return if the layer should be reinserted into arealdekke.
        return reinsert

    # ========================
    # Setters
    # ========================

    def set_accessibility(self, newStatus: bool) -> None:
        self.__accessibility = newStatus

    # ========================
    # Getters
    # ========================

    def get_title(self) -> str:
        return self.__title

    def get_order(self) -> int:
        return self.__order

    def get_accessibility(self) -> bool:
        return self.__accessibility

    def get_operations(self) -> list:
        return self.__operations

    def get_map_scale(self) -> str:
        return self.__map_scale

    def __str__(self) -> str:
        return (
            f"Category title='{self.__title}', "
            f"accessibility={self.__accessibility}, "
            f"order={self.__order})"
        )
