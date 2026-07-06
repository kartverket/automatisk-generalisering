# Libraries

import arcpy

from pathlib import Path

from data_orchestrator.data_lookup import PIPELINE_INPUT
from data_orchestrator.data_names import DataNames as dn
from data_orchestrator.datasets import DatasetNamespace
from data_orchestrator.input_setup import FolderSpec, create_folder_spec
from paths import GIS_FILES_ROOT

# ========================
# DataReader
# ========================


class DataReader:
    """
    Class that reads and fetches the relevant data for the specific pipeline.

    Params:
        map_scale (str): The working scale
        path (Path): Path object to the main place to fetch GIS files
        pipeline (str): The pipeline to the data that should be generalized
    """

    def __init__(self, map_scale: str = None, pipeline: str = None):
        self.map_scale: str = map_scale.lower()
        self.path: Path = GIS_FILES_ROOT
        self.pipeline: str = pipeline.lower()

    # ========================
    # Fetchers
    # ========================

    def fetch_relevant_datasets(self) -> dict[str, DatasetNamespace]:
        """
        Fetches the relevant datasets for the specific pipeline and scale,
        and returns them as a dictionary of DatasetNamespace objects.
        """
        relevant_datasets: dict[str, list] = PIPELINE_INPUT[self.map_scale][
            self.pipeline
        ]
        datasets = {}

        for dataset_name, dataset_structure in relevant_datasets.items():
            folder_spec: FolderSpec = create_folder_spec(
                path=self.path,
                map_scale=dn.raw_data,
                structure={dataset_name: dataset_structure},
            )  # TODO: Change to dynamical choice of map_scale
            data = {Path(p).name: Path(p) for p in folder_spec.all_files()}
            datasets[dataset_name] = DatasetNamespace(data)

        return datasets
