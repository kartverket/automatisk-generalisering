# Libraries

import arcpy
import os

from collections.abc import Iterable
from pathlib import Path

from data_lookup import PIPELINE_INPUT
from data_names import DataNames as dn
from input_setup import FolderSpec, create_folder_spec
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

symbology_structure: dict[str] ={
    "n100": [
            "AnleggsLinje_maske_sort.lyrx",
            "begrensningskurve_buffer_water_features_n100.lyrx",
            "building_points_symbology_n100.lyrx",
            "building_polygons_drawn_from_points.lyrx",
            "grunnriss_symbology_n100.lyrx",
            "jernbanestasjon_square.lyrx",
            "M616_Samferdsel.lyrx",
            "N100_Arealdekke_grense_blå_maske.lyrx",
            "railway_buffer.lyrx",
        ],
    "n250": ["N250_Begrensningskurve.lyrx", "N250_Samferdsel.lyrx"],
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
        Checks that the folder structure for raw data and symbology is valid.
        """
        gdb_path = os.path.join(self.path, dn.raw_data)
        symbology_path = os.path.join(self.path, dn.symbology.lower())
        valid_structure = PIPELINE_INPUT[dn.raw_data]

        gdb_spec = create_folder_spec(
            path=self.path, map_scale=dn.raw_data, structure=valid_structure
        )
        symbology_spec = create_folder_spec(
            path=self.path, map_scale=dn.symbology.lower(), structure=symbology_structure, gdb=False
        )

        gdb_paths = {p for p in gdb_spec.all_files()}
        symbology_paths = {p for p in symbology_spec.all_files()}

        self.validate_folder_spec(spec=gdb_spec)
        self.validate_folder_spec(spec=symbology_spec)

        return



        m, e = self.scan_folder_structure(
            path=self.path,
            #spec=get_folder_spec(map_scale=dn.raw_data),
        )

        if m or e:
            raise RuntimeError(
                f"\nFolder structure validation failed.\n"
                f"Missing: {m}\n"
                f"Extra: {e}\n"
            )

    def pipeline_folder_validation(self) -> None:
        data_scale = dn.raw_data
        spec = create_folder_spec(
            path=self.path,
            map_scale=data_scale,
            structure=PIPELINE_INPUT[self.map_scale][self.pipeline],
        )
        self.validate_folder_spec(spec=spec)

    # Helper functions

    def validateInput(self, value: str, valid_set: Iterable[str], name: str) -> bool:
        """
        Evaluates the value depending on det valid values in iterable.
        """
        if value and value.lower() in valid_set:
            return True
        raise ValueError(
            f"\nInvalid {name} ({value}), must be one of: {', '.join(valid_set)}\n"
        )

    def validPipeline(self, pipeline: str = None) -> bool:
        return self.validateInput(pipeline, VALID_PIPELINES, "pipeline")

    def validScale(self, map_scale: str = None) -> bool:
        return self.validateInput(map_scale, VALID_SCALES, "map scale")

    def find_gdb(self, path: Path) -> Path | None:
        """
        Finds the first geodatabase in the given path.

        Args:
            path (Path): The path to search for a geodatabase

        Returns:
            Path | None: The path to the first geodatabase found, or None if not found
        """
        for parent in path.parents:
            if parent.suffix.lower() == ".gdb":
                return parent
        return None

    def validate_folder_spec(self, spec: FolderSpec) -> None:
        """
        Checks that the folder structure of gdb files and
        feature classes matches and that the files exist.

        Args:
            spec (FolderSpec): The folder specification to validate
        """
        seen_gdbs: set[str] = set()

        for path in spec.all_files():
            feature_class = Path(path)
            gdb = self.find_gdb(feature_class)
            if gdb and gdb not in seen_gdbs:
                if self.gdb_exists(Path(gdb)):
                    seen_gdbs.add(gdb)
            self.arcgis_object_exists(arcgis_path=feature_class)
            # TODO: Need to create a lookup for columns (if we want it)

    def gdb_exists(self, gdb_path: Path) -> bool:
        """
        Checks if the given gdb_path exists and is a valid geodatabase.

        Args:
            gdb_path (Path): The path to the geodatabase

        Returns:
            bool: True if the geodatabase exists and is valid
        """
        if gdb_path.exists() and gdb_path.is_dir():
            return True
        raise FileNotFoundError(f"\nGeodatabase not found: {str(gdb_path)}\n")

    def arcgis_object_exists(self, arcgis_path: Path) -> bool:
        """
        Checks if the given arcgis_path exists and is a valid ArcGIS object.

        Args:
            arcgis_path (Path): The path to the ArcGIS object

        Returns:
            bool: True if the ArcGIS object exists and is valid
        """
        if arcpy.Exists(str(arcgis_path)):
            return True
        raise FileNotFoundError(
            f"\nArcGIS object not found: {str(arcgis_path)}\n"
        )
    

    def scan_structure(self, root_path: Path, valid_paths: set[str]) -> tuple[set[str]]:
        """
        ...
        """
        root = Path(root_path).resolve()
        valid_set = {Path(p).resolve() for p in valid_paths}
        

    def scan_folder_structure(self, path: Path, spec: FolderSpec) -> tuple:
        """
        Checks that the folder structure for the raw data in the given path matches the excpected structure.

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

    validator.global_folder_validation()
    #validator.pipeline_folder_validation()
