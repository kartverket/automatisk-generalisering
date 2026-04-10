# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from pathlib import Path

from generalization.n10.arealdekke.category_tools.buff_small_polygon_segments import (
    buff_small_polygon_segments,
)
from composition_configs import core_config, logic_config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools.param_utils import initialize_params
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n10.arealdekke.category_tools.simplify_land_use import (
    simplify_and_smooth_polygon,
)
from generalization.n10.arealdekke.parameters.parameter_dataclasses import (
    LandUseParameters,
)

# ========================
# Class
# ========================


"""
Hierarchy of the order that the land use types must be expanded in:

1) ElvFlate # Det som er implementert rekkefølge

- ElvFlate # Det som er tenkt overordnet rekkefølge
- Innsjo
- InnsjoRegulert
- Kanal
- Hav
- Snøisbre
- LufthavnOmr
- Bane
- Samferdsel
- Parkering
- Høyblokkbebyggelse
- Industri
- Park
- GravUrnelund
- IdrettsOmr
- Bergverk (Steintipp / Grustak)
- Alpinbakke
- Golfbane
- Bebygd
- Jordbruk
- Innmarksbeite
- Myr
- Skog
- Snaumark
"""


class LandUse:
    """
    Land Use class that performs simplification and expansion of land use layers.

    The class iterates through all land use types that need to be taken care of,
    and follows a specific hierarchy in order to preserve more important features.

    The pipeline does the following:
        - Simplifies the input polygons
        - Smooths the geometries
        - Detects thin areas
        - Buffers thin areas
        - Adjusts the buffers to fit with locked / more important features
        - Merges edited polygons into the entire land use feature class
        - Removes overlap and fills holes

    Parameters:
        - ...
    """

    def __init__(self, land_use_config: logic_config.LandUseInitKwargs):
        """
        Creates an instance of the LandUse class.

        Args:
            land_use_config (LandUseInitKwargs):
                InitKwargs with initialization data for the class
        """
        self.input_fc = land_use_config.input_feature
        self.output_fc = land_use_config.output_feature

        self.map_scale = land_use_config.map_scale
        params_path = Path(__file__).parent / "parameters" / "parameters.yml"
        self.scale_parameters = initialize_params(
            params_path=params_path,
            class_name="ExpandLandUse",
            map_scale=self.map_scale,
            dataclass=LandUseParameters,
        )

        # self.locked_features = locked_features

    @timing_decorator
    def fetch_data() -> None:
        """
        ...
        """
        return

    @timing_decorator
    def run() -> None:
        """
        ...
        """
        return


# TODO:
"""
Klassen over skal:
    - Simplifisere og glatte ut
    - Finne smale områder
    - Buffre smale områder
    - Koble på igjen og bevare topologi
"""


class ExpansionController:
    """
    Expansion class that enlarges thin areas of land use
    iterative by locking fixed geometries.

    Different categories of land use are enlarged category
    by category in such a way that all features will be
    readable in current scale, and not overlapping previously
    edited geometries.

    Parameters:
        - input_fc (str): The feature class with the input parameters
        - output_fc (str): The feature class where the output will be saved
        - wfm (WorkFileManager): WorkFileManager taking care of temporary files
        - files (dict): Dictionary with all the files that are going to be used
        - locked_land_use (set): Set collecting locked land use types that should
            not be edited
        - parameter_handler (...): Instance taking care of all minimum limits
            that need to be taken care of during the process
    """

    def __init__(self, expansion_controller_config: logic_config.LandUseInitKwargs):
        """
        Creates an instance of the ExpansionController.

        Args:
            expansion_controller_config (ExpansionControllerInitKwargs):
                InitKwargs with initialization data for the class
        """
        self.input_fc = expansion_controller_config.input_feature
        self.output_fc = expansion_controller_config.output_feature
        self.wfm = WorkFileManager(expansion_controller_config.wfm_config)

        self.files = self.create_wfm_gdbs(wfm=self.wfm)

        self.map_scale = expansion_controller_config.map_scale
        params_path = Path(__file__).parent / "parameters" / "parameters.yml"
        self.scale_parameters = initialize_params(
            params_path=params_path,
            class_name="ExpandLandUse",
            map_scale=self.map_scale,
            dataclass=LandUseParameters,
        )

        self.locked_land_use = set()

    # ========================
    # Main functions
    # ========================

    def create_wfm_gdbs(self, wfm: WorkFileManager) -> dict:
        """
        Creates all the temporarily files that are going to be used
        during the process of expanding land use categories.

        Args:
            wfm (WorkFileManager): The WorkFileManager instance that are keeping the files
        """
        copy_of_input = wfm.build_file_path(file_name="copy_of_input", file_type="gdb")
        decreased_ElvFlate = wfm.build_file_path(
            file_name="decreased_ElvFlate", file_type="gdb"
        )
        return {
            "copy_of_input": copy_of_input,
            "decreased_ElvFlate": decreased_ElvFlate,
        }

    @timing_decorator
    def copy_fc(input_fc: str, output_fc: str) -> None:
        """
        Copies the input data to a new feature class.

        Args:
            input_fc (str): The feature class with the input data
            output_fc (str): The feature class where the data should be copied to
        """
        arcpy.management.CopyFeatures(in_features=input_fc, out_feature_class=output_fc)

    @timing_decorator
    def run(self) -> None:
        """
        Performes the entire expansion loop, type by type through
        all the land use classes that need to be taken care of.
        """
        self.copy_fc(input_fc=self.input_fc, output_fc=self.files["copy_of_input"])

        EXPANSIONS = [
            [  # ElvFlate
                self.files["copy_of_input"],
                self.files["decreased_ElvFlate"],
                "ElvFlate",
                self.scale_parameters.elvFlate,
            ],
        ]

        for input_fc, output_fc, attribute, parameter in EXPANSIONS:
            self.locked_land_use = buff_small_polygon_segments(
                input_fc=input_fc,
                output_fc=output_fc,
                locked_land_use=self.locked_land_use,
                attribute=attribute,
                min_size=parameter,
            )

        # Copy final output
        self.copy_fc(
            input_fc=self.files["decreased_ElvFlate"], output_fc=self.output_fc
        )

    # ========================
    # Helper functions
    # ========================


# ========================


@timing_decorator
def simplify_and_expand_land_use(input_fc: str, output_fc: str) -> None:
    """
    Main function that uses LandUse to simplify and blow up geometries.

    Args:
        input_fc (str): Feature class with the input data
        output_fc (str) The feature class were the final output will be stored
    """
    land_use_config = logic_config.LandUseInitKwargs(
        input_feature=input_fc, output_feature=output_fc
    )

    LandUse(land_use_config=land_use_config).run()
