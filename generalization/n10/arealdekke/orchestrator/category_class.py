# Module imports:
import arcpy
import inspect

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10

# Category tools:
from generalization.n10.arealdekke.category_tools.simplify_land_use import (
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

        # Setting up file manager w. dictionary for easy file access
        self.working_fc = Arealdekke_N10.category_class_in_progress__n10_land_use.value
        self.config = core_config.WorkFileConfig(root_file=self.working_fc)
        self.wfm = WorkFileManager(config=self.config)

        self.files = {
            "last_edited_fc": self.wfm.build_file_path(
                file_name=f"last_edited_fc_{self.__title}", file_type="gdb"
            )
        }

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

    @timing_decorator
    def process_category(
        self, input_fc: str, locked_fc: str, processed_fc: str
    ) -> bool:

        reinsert = False

        # File that will be overwritten with new input for each iteration.

        if self.__operations:

            # Iterates through the operations needed for each category.
            for operation in self.__operations:
                func = self.cat_tools[operation]

                sig = inspect.signature(func)
                param_names = sig.parameters.keys()

                available_args = {
                    "target": self.__title,
                    "input_fc": input_fc,
                    "output_fc": processed_fc,
                    "locked_fc": locked_fc,
                    "map_scale": self.__map_scale,
                }

                args_to_pass = {
                    name: available_args[name]
                    for name in param_names
                    if name in available_args
                }

                # Calls function from dictionary
                self.cat_tools[operation](**args_to_pass)

                # Updates the layer that will be passed on to the next operation to be the output.
                arcpy.management.CopyFeatures(
                    in_features=processed_fc, out_feature_class=input_fc
                )

                # Saves the last edits made in case program stops.
                arcpy.management.CopyFeatures(
                    in_features=processed_fc,
                    out_feature_class=self.files["last_edited_fc"],
                )

            # Marks the process as completed.
            reinsert = True

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
