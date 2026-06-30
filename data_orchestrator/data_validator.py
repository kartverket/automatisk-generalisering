# Libraries

import arcpy

from collections.abc import Iterable
from pathlib import Path

from data_lookup import PIPELINE_INPUT
from data_names import DataNames as dn
from input_setup import FolderSpec, create_folder_spec, get_folder_spec
from paths import GIS_FILES_ROOT

# ========================
# Constants
# ========================

VALID_PIPELINES: list[str] = [
    x.lower() for x in [dn.building, dn.object_arealdekke_flate, dn.road]
]
VALID_SCALES: list[str] = [
    dn.scale_n10,
    dn.scale_n50,
    dn.scale_n100,
    dn.scale_n250,
    dn.scale_n500,
]
INPUT_SCALE_MAPPING: dict[str] = {
    dn.scale_n10: dn.raw_data,
    dn.scale_n50: dn.scale_n10,
    dn.scale_n100: dn.scale_n50,
    dn.scale_n250: dn.scale_n100,
    dn.scale_n500: dn.scale_n250,
}

# ========================
# DataValidator
# ========================


class DataValidator:
    """
    Validation class that ensures that the relevant
    data for the specific pipeline is valid.

    Params:
        map_scale (str): The scale to be controlled
        path (Path): Path object to the main place to store GIS files
        pipeline (str): The pipeline to be controlled
                        (the data that should be generalized)
    """

    def __init__(self, map_scale: str = None, pipeline: str = None):
        self.validPipeline(pipeline)
        self.validScale(map_scale)

        self.map_scale: str = map_scale.lower()
        self.path: Path = GIS_FILES_ROOT
        self.pipeline: str = pipeline.lower()


    # Validators


    def global_folder_validation(self) -> None:
        """
        Checks that the folder structure is valid.
        """
        m, e = self.scan_folder_structure(
            path=self.path,
            spec=get_folder_spec(map_scale=dn.raw_data),
        )

        if m or e:
            raise RuntimeError(
                f"Folder structure validation failed.\n" f"Missing: {m}\n" f"Extra: {e}"
            )


    def pipeline_folder_validation(self) -> None:
        data_scale = dn.raw_data
        spec = create_folder_spec(map_scale=data_scale, structure=PIPELINE_INPUT[self.map_scale][self.pipeline])

        print(spec.name)
        print(spec.files)
        for key, val in spec.folders[data_scale].folders.items():
            print(f"{key}: {[str(v) for v in val.files]}")


    # Helper functions


    def _validate(self, value: str, valid_set: Iterable[str], name: str) -> bool:
        """
        Evaluates the value depending on det valid values in iterable.
        """
        if value and value.lower() in valid_set:
            return True
        raise ValueError(
            f"Invalid {name} ({value}), must be one of: {', '.join(valid_set)}"
        )


    def validPipeline(self, pipeline: str = None) -> bool:
        return self._validate(pipeline, VALID_PIPELINES, "pipeline")


    def validScale(self, map_scale: str = None) -> bool:
        return self._validate(map_scale, VALID_SCALES, "map scale")


    def scan_folder_structure(self, path: Path, spec: FolderSpec) -> tuple:
        """
        Checks that the folder structure in the given path matches the excpected structure.

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


if __name__ == "__main__":
    map_scale = dn.scale_n100
    pipeline = dn.road.lower()
    validator = DataValidator(map_scale=map_scale, pipeline=pipeline)

    #validator.global_folder_validation()
    validator.pipeline_folder_validation()
