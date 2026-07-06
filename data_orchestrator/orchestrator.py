# Imports

import arcpy

from pathlib import Path

from data_orchestrator.data_reader import DataReader
from data_orchestrator.data_validator import DataValidator

from data_orchestrator.datasets import DatasetNamespace
from data_orchestrator.features.input_symbology import get_symbology_paths

# ========================
# InputDataOrchestrator
# ========================


class InputDataOrchestrator:
    """
    Orchestrator handling all input data by validating and fetching relevant data only.

    Params:
        map_scale (str): The map scale to fetch data for, e.g. "n100"
        pipeline (str): The pipeline to use for data processing
        datasets (dict): Dictionary with all datasets for the combination of
                        relevant map scale and pipeline. Key is gdb file name,
                        value is a DatasetNamespace object with parameters
                        equal to the feature classes needed for this pipeline
        symbology (dict): A dictionary to store the fetched symbology files
    """

    def __init__(self, map_scale: str, pipeline: str):
        """
        Initialize the class and control that the path has the expected structure.
        If not, throw an error with details on what is missing or extra.

        Args:
            map_scale (str): The map scale to fetch data for, e.g. "n100"
            pipeline (str): The pipeline to use for data processing

        """
        # Sets parameters
        self.map_scale: str = map_scale.lower()
        self.pipeline: str = pipeline.lower()

        # Validates the expected / required folder and file
        # structure for the given map scale and pipeline
        DataValidator(
            map_scale=self.map_scale, pipeline=self.pipeline
        ).pipeline_folder_validation()

        # Fetches the relevant datasets for the given map scale and
        # pipeline, and store them as separate classes in a dict
        self.datasets: dict[str, DatasetNamespace] = DataReader(
            map_scale=self.map_scale, pipeline=self.pipeline
        ).fetch_relevant_datasets()

        self.set_symbology()

    # ========================
    # Validation functions
    # ========================

    def validate_symbology(self, sym_path: Path) -> bool:
        """
        Checks that the symbology file exists.

        Args:
            sym_path (Path): The path to the symbology file to validate

        Returns:
            bool: True if the symbology file is valid, False otherwise
        """
        try:
            if not sym_path.exists():
                return False
            # Attempt to load the layer file
            arcpy.mp.LayerFile(str(sym_path))
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
        dataset_name = dataset_name.upper()
        data: DatasetNamespace = self.datasets.get(dataset_name)
        if data is None:
            raise KeyError(f"Dataset '{dataset_name}' not found in orchestrator.")
        return data

    def get_symbology(self, symbology_name: str) -> str:
        """
        Retrieve the path to a symbology file by name.

        Args:
            symbology_name (str): The name of the symbology file to retrieve.

        Returns:
            str: The path to the symbology file.
        """
        symbology_name = symbology_name.lower()
        sym = self.symbology.get(symbology_name)
        if sym is None:
            raise KeyError(f"Symbology '{symbology_name}' not found in orchestrator.")
        return sym

    # ========================
    # Setters
    # ========================

    def set_symbology(self) -> None:
        """
        Register all symbology files defined for the current map scale.
        The symbology files are fetched using `get_symbology_paths()` and validated
        using `validate_symbology()` before being added.
        """
        symbologies = get_symbology_paths(self.map_scale)

        content = {}
        missing = set()

        for name, path in symbologies.items():
            if self.validate_symbology(path):
                content[name.lower()] = str(path)
            else:
                missing.add(str(path))

        if missing:
            raise RuntimeError(f"Missing symbologies found: {missing}")

        self.symbology = content


if __name__ == "__main__":
    data_orc = InputDataOrchestrator(map_scale="n100", pipeline="road")

    for key, value in data_orc.datasets.items():
        print(f"Dataset: {key}\nFeatures: {value}\n")

    print(data_orc.datasets["ROAD"].elveg_and_sti)
