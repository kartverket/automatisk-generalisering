# Module imports:
import arcpy
import inspect

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n10.arealdekke.orchestrator.enum_variables import (
    history_keys as keys,
)

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
        last_processed: str = None,
        operations_completed: int = None,
        reinserts_completed: int = None,
    ):
        # Setting up file manager w. dictionary for easy file access
        self.working_fc = Arealdekke_N10.category_class_in_progress__n10_land_use.value
        self.config = core_config.WorkFileConfig(root_file=self.working_fc)
        self.wfm = WorkFileManager(config=self.config)

        self.__title: str = title

        # Extracts inputs and saves them within object
        self.__operations: list[str] = operations or []
        self.__accessibility: bool = (
            accessibility if accessibility is not None else True
        )
        self.__order: int = order
        self.__map_scale: str = map_scale
        self.__last_processed: str = last_processed if last_processed else None
        self.__operations_completed: int = operations_completed or 0
        self.__reinserts_completed: int = reinserts_completed or 0

        if self.__operations:
            for item in self.__operations:

                # Checks if each operation is written correctly (test can be improved later)
                if item not in list(self.set_cat_tools()):
                    raise Exception(
                        f"\nIncorrect syntax in history yml file for arealdekke: {self.__title}.\nGo check history yml file and set_cat_tools in category class for tool name inconsistencies.\n"
                    )

        # Creates layer for the category. Data inserted into it in setter function.
        self.lyr = f"{self.__title}_lyr"

    # ========================
    # Main functions
    # ========================

    @timing_decorator
    def process_category(self, input_fc: str, locked_fc: str, processed_fc: str):

        cat_tools = self.set_cat_tools()

        # Iterates through the operations needed for each category.
        for operation in range(self.__operations_completed, len(self.__operations), 1):

            func = cat_tools[self.__operations[operation]]

            sig = inspect.signature(func)
            param_names = sig.parameters.keys()

            print("last_processed: ", self.__last_processed)

            available_args = {
                "target": self.__title,
                "input_fc": (
                    self.__last_processed
                    if self.__last_processed is not None
                    else input_fc
                ),
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
            cat_tools[self.__operations[operation]](**args_to_pass)

            # Updates the layer that will be passed on to the next operation to be the output.
            arcpy.management.CopyFeatures(
                in_features=processed_fc, out_feature_class=input_fc
            )

            # Saves the last edits made in case program stops.

            self.__last_processed=processed_fc

            # Updates program history
            self.__operations_completed += 1

            update: dict = {
                keys.last_processed.value : str(self.__last_processed),
                keys.operations_completed.value: self.__operations_completed,
            }

            yield update

    # ========================
    # Setters
    # ========================

    def set_accessibility(self, newStatus: bool) -> None:
        self.__accessibility = newStatus

    def update_reinsert_operations_completed(self) -> None:
        self.__reinserts_completed += 1

    def set_cat_tools(self) -> dict:
        return {
            "simplify_and_smooth": simplify_and_smooth_polygon,
            "buff_small_segments": buff_small_polygon_segments,
        }

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

    def get_reinserts_completed(self) -> int:
        return self.__reinserts_completed

    def __str__(self) -> str:
        return (
            f"Category title='{self.__title}', "
            f"accessibility={self.__accessibility}, "
            f"order={self.__order})"
        )
