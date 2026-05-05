import yaml
import os
from pathlib import Path
from generalization.n10.arealdekke.orchestrator.category_class import Category
from generalization.n10.arealdekke.orchestrator.enum_variables import (
    history_keys as keys,
)


class Program_history_class:
    def __init__(self, file_path):
        """
        What:
                Creates a new program history object. Checks if the history file path recieved exists.
            If not, a new history yaml file is created with the same file path.
        """

        self.__program_history_path: str = str(file_path)

        if not Path(self.__program_history_path).is_file():
            self.reset_history()
            self.new_history_created: bool = True
        else:
            self.new_history_created: bool = False

    # ========================
    # Getters
    # ========================

    def get_new_history_created(self) -> bool:
        return self.new_history_created

    def get_history_attribute_top_lvl(self, key):
        """
        What:
                Used to extract arealdekke attributes from the history yaml file, e.g. newest_version,
            map_scale or preprocessing_operations_completed.
        """
        history = self.load_history()
        return history[key]

    def get_history_attribute_cat_lvl(self, title, key):
        """
        What:
                Used to extract arealdekke category attributes from the history yaml file, e.g.
            last_processed (file path), title or accessibility.
        """
        history = self.load_history()

        for cat in history[keys.category_history.value]:
            if cat[keys.title.value] == title:
                return cat[key]

    def restore_arealdekke_attributes(self) -> dict:
        """
        What:
            Checks how far the processing got in the previous run.
        """

        history = self.load_history()

        response: dict = {}

        if history.get(keys.preprocessing_operations_completed.value, 0) > 0:
            response["file_path"] = history[keys.newest_version.value]
            response[keys.preprocessed.value] = history[keys.preprocessed.value]
            response[keys.preprocessing_operations_completed.value] = history[
                keys.preprocessing_operations_completed.value
            ]
            response[keys.postprocessing_operations_completed.value] = history[
                keys.postprocessing_operations_completed.value
            ]
            response[keys.map_scale.value] = history[keys.map_scale.value]

        else:
            response["file_path"] = None

        return response

    def restore_arealdekke_categories(self):
        """
        What:
                Checks at least one of the categories stored in the history yaml file have begun
            processing. If true, it returns a dictionary that states that worthy categories did
            exist, and a list of said categories. If false, a dictionary that states that no
            worthy categories existed is returned.
        """

        history = self.load_history()
        preprocessed = history[keys.preprocessed.value]
        cat_history = history.get(keys.category_history.value, [])

        response = {}

        if (
            preprocessed
            and cat_history
            and cat_history[0][keys.operations_completed.value]
        ):
            response["cats_exist"] = True
            response["cats"] = []

            for category in history[keys.category_history.value]:
                category_obj = Category(**category)
                response["cats"].append(category_obj)

        else:
            response["cats_exist"] = False

        return response

    # ========================
    # Setters
    # ========================

    def save_history(self, data):
        """
        Write history log to the YAML file.
        """
        with open(Path(self.__program_history_path), "w") as file:
            yaml.dump(data, file, default_flow_style=False, allow_unicode=True)

    def load_history(self):
        """
        Load history log from YAML file.
        """
        with open(str(self.__program_history_path), "r") as file:
            return yaml.safe_load(file)

    def update_history_top_lvl(self, key, value):
        """
        Update key in the history log outside category overview to value.
        """
        data = self.load_history()
        data[key] = value
        self.save_history(data)

    def update_history_cat_lvl(self, title, key, value):
        """
        Update parameter key for category with title to value.
        """
        data = self.load_history()

        for cat in data[keys.category_history.value]:
            if cat[keys.title.value] == title:
                cat[key] = value
                self.save_history(data)
                break

    def new_history_category(
        self, title, operations, accessibility=True, order=None, map_scale="N10"
    ):

        data = self.load_history()
        history = data[keys.category_history.value]

        new_entry = {
            keys.title.value: title,
            keys.operations.value: operations,
            keys.accessibility.value: accessibility,
            keys.order.value: order,
            keys.map_scale.value: map_scale,
            keys.last_processed.value: None,
            keys.operations_completed.value: 0,
            keys.reinserts_completed.value: 0,
        }

        history.append(new_entry)
        self.save_history(data)

    def reset_history(self):

        template = {
            keys.newest_version.value: None,
            keys.map_scale.value: None,
            keys.preprocessed.value: False,
            keys.preprocessing_operations_completed.value: 0,
            keys.postprocessing_operations_completed.value: 0,
            keys.category_history.value: [],
        }

        data = template
        self.save_history(data)

    def delete_history(self):
        if Path(self.__program_history_path).is_file():
            os.remove(self.__program_history_path)
