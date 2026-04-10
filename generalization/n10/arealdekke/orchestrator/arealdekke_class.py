# Module imports:
import arcpy
import yaml
import os
from sqlalchemy import values
from pathlib import Path
from composition_configs import core_config
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from input_data import input_n10, input_test_data
from generalization.n10.arealdekke.orchestrator.category_class import Category

# Arealdekke tools:
from generalization.n10.arealdekke.overall_tools.arealdekke_dissolver import (
    partition_call as arealdekke_dissolver,
)
from generalization.n10.arealdekke.overall_tools.gangsykkel_dissolver import (
    partition_call as gangsykkel_dissolver,
)
from generalization.n10.arealdekke.overall_tools.eliminate_small_polygons import (
    partition_call as eliminate_small_polygons,
)
from generalization.n10.arealdekke.overall_tools.attribute_changer import (
    attribute_changer,
)
from generalization.n10.arealdekke.overall_tools.island_controller import (
    island_controller,
)
from generalization.n10.arealdekke.orchestrator.expansion_controller import (
    simplify_and_expand_land_use,
)
from generalization.n10.arealdekke.overall_tools.area_merger import area_merger
from generalization.n10.arealdekke.overall_tools.passability_layer import (
    create_passability_layer,
)

arcpy.env.overwriteOutput = True


class Arealdekke:

    def __init__(self, map_scale) -> None:

        # Setting up file manager w. dictionary for easy file access
        self.working_fc = (
            Arealdekke_N10.arealdekke_class_in_progress__n10_land_use.value
        )
        self.config = core_config.WorkFileConfig(root_file=self.working_fc)
        self.wfm = WorkFileManager(config=self.config)

        self.files = {
            "arealdekke_fc": self.wfm.build_file_path(
                file_name="arealdekke_fc", file_type="gdb"
            ),
            "category_fc": self.wfm.build_file_path(
                file_name="category_fc", file_type="gdb"
            ),
            "locked_fc": self.wfm.build_file_path(
                file_name="locked_fc", file_type="gdb"
            ),
            "processed_fc": self.wfm.build_file_path(
                file_name="processed_fc", file_type="gdb"
            ),
        }

        # Creates a variable to see if the data has been preprocessed.
        # Safety lock to make sure categories are not added before data is ok.
        self.preprocessed = None

        # Other attributes
        self.__map_scale = None
        self.__preprocessing_operations_completed = None
        self.categories= []

        # Program history
        self.__program_history_path = Path(__file__).parent / "arealdekke_history.yml"

        update=False

        #Check if the program history exists
        if self.__program_history_path.is_file():
        
            try:
                with open(self.__program_history_path, "r", encoding="utf-8") as yml:
                    data = yaml.safe_load(yml)

                    # Check how far the preprocessing got. If at least one process was
                    #  completed, update paths etc.
                    if data.get("preprocessing_operations_completed", 0)>0:
                        
                        update=True

                        self.files["arealdekke_fc"]=data["newest_version"]
                        self.preprocessed=data["preprocessed"]
                        self.__preprocessing_operations_completed=data["preprocessing_operations_completed"]
                        self.__map_scale=data["map_scale"]

                        # If preprocessed is false or the categories have not started
                        # processing, the categories will be added like normal.
                        category_history = data.get("category_history", [])

                        if (
                            self.preprocessed and 
                            category_history and 
                            category_history[0]["operations_completed"]
                        ):

                            # Extracts the data from the yml file into a category object.
                            for category in data["category_history"]:
                                category_obj = Category(**category)
                                self.categories.append(category_obj)

            except Exception as e:
                raise e

        if update==False:
            #reset history
            self.reset_history()

            # Update variables
            self.preprocessed = False
            self.__map_scale = map_scale

            # Extracts the data and saves it in the object
            arcpy.management.CopyFeatures(
                in_features=input_n10.Arealdekke_Buskerud,
                out_feature_class=self.files["arealdekke_fc"],
            )


    # ========================
    # Main functions
    # ========================

    def preprocess(self) -> None:

        output_fc = Arealdekke_N10.dissolve_gangsykkel.value

        preprocesses=[
            lambda: attribute_changer(
                input_fc=self.arealdekke_data,
                output_fc=Arealdekke_N10.attribute_changer_output__n10_land_use.value,
            ),

            lambda: create_passability_layer(
                input_fc=Arealdekke_N10.attribute_changer_output__n10_land_use.value,
                output_fc=Arealdekke_N10.passability__n10_land_use.value,
            ),
            
            lambda: arealdekke_dissolver(
                input_fc=Arealdekke_N10.attribute_changer_output__n10_land_use.value,
                output_fc=Arealdekke_N10.dissolve_arealdekke.value,
                map_scale=self.__map_scale,
            ),

            lambda: island_controller(
                input_fc=Arealdekke_N10.dissolve_arealdekke.value,
                output_fc=Arealdekke_N10.island_merger_output__n10_land_use.value,
            ),

            lambda: eliminate_small_polygons(
                input_fc=Arealdekke_N10.island_merger_output__n10_land_use.value,
                output_fc=Arealdekke_N10.elim_output.value,
                map_scale=self.__map_scale,
            ),

            lambda: gangsykkel_dissolver(
                input_fc=Arealdekke_N10.elim_output.value,
                output_fc=output_fc,
                map_scale=self.__map_scale,
            )
        ]

        # Pipeline from original orchistrator file. Preprocessing the arealdekke data.
        for preprocess in range(self.__preprocessing_operations_completed, len(preprocesses), 1):

            #Call process
            preprocesses[preprocess]()

            #Update history (operations completed)
            

        arcpy.management.CopyFeatures(
            in_features=output_fc, out_feature_class=self.files["arealdekke_fc"]
        )

        self.preprocessed = True

    def add_categories(self, categories_config_file) -> bool:

        completed = False

        # Checks if the data has been preprocessed.
        if self.preprocessed and not self.categories:

            try:
                with open(categories_config_file, "r", encoding="utf-8") as yml:
                    python_structured = yaml.safe_load(yml)

                    for category in python_structured["Categories"]:

                        # Extracts the data from the yml file into a category object.
                        category_obj = Category(**category)

                        # Adds it to the categories list/array if it has the same map scale as arealdekke.
                        if category_obj.get_map_scale() == self.__map_scale:
                            self.categories.append(category_obj)

                # Sorts the categories based on their order key.
                self.categories.sort(key=lambda obj: obj.get_order())

                # Updates completed variable.
                completed = True

            except Exception as e:
                raise e

        # Returns status of completion to user.
        return completed

    def process_categories(self) -> None:
        # Iterates through the categories that are true, meaning they are open.
        for category in list(
            filter(lambda cat: cat.get_accessibility(), self.categories)
        ):
            # Get the locked layers and the input layer
            self.get_locked_categories()
            self.get_category(category.get_title())

            # Process category.
            reinsert = category.process_category(
                input_data=self.files["category_fc"],
                locked_layers=self.files["locked_fc"],
                processed_layer=self.files["processed_fc"],
            )

            if reinsert:
                # Add the category back into the input layer.
                pass
                # area_merger()

            # Lock the layer
            category.set_accessibility(False)

        # Save processed data to final fc and delete the last files
        arcpy.management.CopyFeatures(
            in_features=self.files["processed_fc"],
            out_feature_class=Arealdekke_N10.arealdekke_class_final__n10_land_use.value,
        )

        self.wfm.delete_created_files()
        self.reset_history()

    # ========================
    # Getters
    # ========================

    def get_map_scale(self) -> str:
        return self.__map_scale

    def get_locked_categories(self) -> None:

        # List of titles of locked categories.
        locked_categories_titles = set()

        for category in self.categories:
            if not category.get_accessibility():
                locked_categories_titles.add(category.get_title())

        # Creates new layer with all the locked features
        values = ", ".join([f"'{v}'" for v in locked_categories_titles])
        where_clause = f"arealdekke IN ({values})"

        temp_lyr = "temp_lyr"

        arcpy.management.MakeFeatureLayer(
            in_features=self.files["arealdekke_fc"],
            out_layer=temp_lyr,
            where_clause=where_clause,
        )

        # Makes layer into fc
        arcpy.management.CopyFeatures(
            in_features=temp_lyr, out_feature_class=self.files["locked_fc"]
        )

    def get_category(self, category_title: str) -> None:

        # Extracts categorical data from arealdekke into feature layer
        temp_lyr = "temp_lyr"

        arcpy.management.MakeFeatureLayer(
            in_features=self.files["arealdekke_fc"],
            out_layer=temp_lyr,
            where_clause=f"arealdekke='{category_title}'",
        )

        arcpy.management.CopyFeatures(
            in_features=temp_lyr, out_feature_class=self.files["category_fc"]
        )

    # ========================
    # Setters
    # ========================

    def reset_history(self):
        if self.__program_history_path.is_file():
            os.remove(self.__program_history_path)

        template = {
            "newest_version": None,
            "map_scale": None,
            "preprocessed": None,
            "preprocessing_operations_completed": None,
            "category_history": []
        }

        with open(self.__program_history_path, "w", encoding="utf-8") as new_history:
            yaml.dump(template, new_history)