# Imports

import arcpy

from pathlib import Path
from types import ModuleType

from config import input_data_folder
from input_data import input_n100, input_roads
from input_data.input_datasets import DatasetNamespace
from input_data.input_setup import EXPECTED, FolderSpec

# ========================
# InputDataOrchestrator
# ========================


class InputDataOrchestrator:
    """
    Orchestrator handling all input data by validating and fetching relevant data only.

    Params:
        path (Path): The path to the input data folder
        map_scale (str): The map scale to fetch data for, e.g. "n100"
        data (Path): The path to the input datasets
        symbology (Path): The path to the symbology files for the given map scale
        datasets (dict): A dictionary to store the fetched datasets
        symbology (dict): A dictionary to store the fetched symbology files
    """

    def __init__(self, map_scale: str):
        """
        Initialize the class and control that the path has the expected structure.
        If not, throw an error with details on what is missing or extra.

        Args:
            map_scale (str): The map scale to fetch data for, e.g. "n100"
        """
        self.path: Path = Path(input_data_folder)

        self.assert_valid_structure(self.path)

        self.map_scale: str = map_scale.lower()

        self.data: Path = Path.joinpath(self.path, "raw_data")
        self.symbology: Path = Path.joinpath(self.path, "symbology", self.map_scale)

        self.datasets: dict = {}
        self.symbology: dict = {}

    # ========================
    # Validation functions
    # ========================

    def assert_valid_structure(self, path: Path) -> None:
        """
        Checks that the folder structure is valid.

        Args:
            path (Path): The path to the folder to validate
        """
        # Check validation
        m, e = self.scan_folder_structure(path, EXPECTED)

        # If unvalid match, throw error:
        if m or e:
            raise RuntimeError(
                f"Folder structure validation failed.\n" f"Missing: {m}\n" f"Extra: {e}"
            )

    def scan_folder_structure(self, path: Path, spec: FolderSpec) -> tuple:
        """
        Checks that the folder structure in the given path matches the expected structure.

        Args:
            path (Path): The path to the folder to validate
            spec (FolderSpec): The expected folder structure

        Returns:
            missing (list): A list of missing files and folders
            extra (list): A list of extra files and folders
        """
        missing, extra = [], []

        # Fetch actual content
        actual_files, actual_folders = set(), set()
        for p in path.iterdir():
            (
                actual_files
                if p.suffix.lower() == ".gdb" or p.is_file()
                else actual_folders
            ).add(p.name)

        # Check for missing or extra data
        exp_files = spec.files
        exp_folders = spec.folders.keys()

        missing += [f for f in exp_files - actual_files]
        missing += [f"{d}/" for d in exp_folders - actual_folders]

        extra += [f for f in actual_files - exp_files]
        extra += [f"{d}/" for d in actual_folders - exp_folders]

        # Recursion for subfolders
        for dirname, sub_spec in spec.folders.items():
            if (path / dirname).exists():
                sub_missing, sub_extra = self.scan_folder_structure(
                    Path.joinpath(path, dirname), sub_spec
                )
                missing.extend(sub_missing)
                extra.extend(sub_extra)

        return missing, extra

    def validate_fc(self, fc: Path) -> bool:
        """
        Checks that the feature class actually exists.

        Args:
            fc (Path): The path to the feature class to validate

        Returns:
            bool: True if the feature class is valid, False otherwise
        """
        try:
            lyr = "temp_lyr"
            arcpy.management.MakeFeatureLayer(str(fc), lyr)
            arcpy.management.Delete(lyr)
            return True
        except:
            return False

    # ========================
    # Getters
    # ========================

    def get_dataset(self, dataset_name: str) -> DatasetNamespace:
        """
        Retrieve a dataset by name and return it as a DatasetNamespace object.

        This allows attribute-style access to feature classes, enabling usage such as:
            roads = orchestrator.get_dataset("ROADS")
            roads.elveg_and_sti

        Args:
            dataset_name (str): The name of the dataset group to retrieve,
                typically derived from the module name (e.g. "ROADS").

        Returns:
            DatasetNamespace: An object exposing feature classes as attributes
        """
        data = self.datasets.get(dataset_name)
        if data is None:
            raise KeyError(f"Dataset '{dataset_name}' not found in orchestrator.")
        return DatasetNamespace(data)

    # ========================
    # Setters
    # ========================

    def set_input_dataset(self, dataset: ModuleType) -> None:
        """
        Register all feature classes defined in an input module.

        The module must contain a DATA list with Path objects pointing to
        feature classes inside a file geodatabase. Each feature class is validated
        using `validate_fc()` before being added.

        Args:
            dataset (ModuleType): A module containing a DATA list of Path objects.
        """
        data_name = dataset.__name__.split("_")[-1].upper()
        data = dataset.DATA

        content = {}
        missing = set()

        for d in data:
            if self.validate_fc(d):
                content[d.name] = str(d)
            else:
                missing.add(str(d))

        if missing:
            raise RuntimeError(f"Missing datasets found: {missing}")

        self.datasets[data_name] = content


# ========================

if __name__ == "__main__":
    data_orc = InputDataOrchestrator(map_scale="N100")
    data_orc.set_input_dataset(input_roads)

    roads: DatasetNamespace = data_orc.get_dataset("ROADS")

    arcpy.management.MakeFeatureLayer(roads.elveg_and_sti, "elveg_and_sti_lyr")
    arcpy.management.Delete("elveg_and_sti_lyr")
