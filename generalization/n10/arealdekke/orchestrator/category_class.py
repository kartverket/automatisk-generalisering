# Module imports:
import inspect

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n10.arealdekke.category_tools.buff_small_polygon_segments import (
    buff_small_polygon_segments,
)

# Category tools:
from generalization.n10.arealdekke.category_tools.simplify_polygon import (
    simplify_and_smooth_polygon,
)
from generalization.n10.arealdekke.orchestrator.enum_variables import (
    history_keys as keys,
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
        """
        What:
            Creates a new arealdekke category object. Includes a check that ensures that all operations
            in operations array exist within the tool dictionary defined in set_cat_tools.
        """

        self.working_fc = Arealdekke_N10.category_class_in_progress__n10_land_use.value
        self.config = core_config.WorkFileConfig(root_file=self.working_fc)
        self.wfm = WorkFileManager(config=self.config)

        self.__title: str = title

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

                if item not in list(self.set_cat_tools()):
                    raise Exception(
                        f"\nIncorrect syntax in history yml file for arealdekke: {self.__title}.\nGo check history yml file and set_cat_tools in category class for tool name inconsistencies.\n"
                    )

        self.lyr = f"{self.__title}_lyr"

    # ========================
    # Main functions
    # ========================

    @timing_decorator
    def process_category(self, input_fc: str, locked_fc: str, processed_fc: str):
        """
        What:
                Iterates through each operation, unless some of the operations were previously completed.
            For each operation, the tool is called from the set_cat_tools dictionary with tailored arguments.
            Afterwards, the last_processed attribute is updated to include the path to the previous output,
            operations_completed is updated, and information to be saved in the program history file is sent
            back to the arealdekke class in a dictionary.
        """

        cat_tools = self.set_cat_tools()

        # Iterate through operations specified for this category not applied yet
        for operation in range(self.__operations_completed, len(self.__operations), 1):

            func = cat_tools[self.__operations[operation]]

            # Get required number of arguments
            sig = inspect.signature(func)
            param_names = sig.parameters.keys()

            available_args = {
                "target": self.__title,
                "input_fc": (
                    self.__last_processed
                    if (
                        self.__last_processed is not None
                        or self.__operations_completed > 0
                    )
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

            cat_tools[self.__operations[operation]](**args_to_pass)

            # Update history log
            self.__last_processed = processed_fc
            self.__operations_completed += 1
            update: dict = {
                keys.last_processed.value: str(self.__last_processed),
                keys.operations_completed.value: self.__operations_completed,
            }

            yield update

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

    def get_last_processed(self) -> str:
        return self.__last_processed

    def get_operations_completed(self) -> int:
        return self.__operations_completed

    def __str__(self) -> str:
        return (
            f"Category title='{self.__title}', "
            f"accessibility={self.__accessibility}, "
            f"order={self.__order})"
        )

    # ========================
    # Setters
    # ========================

    def set_accessibility(self, newStatus: bool) -> None:
        self.__accessibility = newStatus

    def update_reinsert_operations_completed(self) -> int:
        self.__reinserts_completed += 1
        return self.__reinserts_completed

    def set_cat_tools(self) -> dict:
        """
        What:
            All functions that can be used on the arealdekke categories.
        """

        return {
            "simplify_and_smooth": simplify_and_smooth_polygon,
            "buff_small_segments": buff_small_polygon_segments,
        }
