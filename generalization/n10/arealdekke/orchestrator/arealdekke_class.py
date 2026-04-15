# Module imports:
import arcpy
import yaml
import os
from sqlalchemy import values
from pathlib import Path
from custom_tools.decorators.timing_decorator import timing_decorator
from composition_configs import core_config
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from input_data import input_n10 #input_test_data
from generalization.n10.arealdekke.orchestrator.category_class import Category
from generalization.n10.arealdekke.orchestrator.program_history_class import Program_history_class as History_class


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
from generalization.n10.arealdekke.overall_tools.passability_layer import (
    create_passability_layer,
)
from generalization.n10.arealdekke.overall_tools.overlap_remover import (
    remove_overlaps,
)
from generalization.n10.arealdekke.overall_tools.fill_holes import fill_holes

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
            "intermediate_fc": self.wfm.build_file_path(
                file_name="intermediate_fc", file_type="gdb"
            ),
            "intermediate_fixed_fc": self.wfm.build_file_path(
                file_name="intermediate_fixed_fc", file_type="gdb"
            ),
        }

        # TODO: IKKE LEGG BARE TIL FILSTI!!!!!!!!!!

        # Program history
        self.program_history: History_class = History_class(file_path=Path(__file__).parent / "arealdekke_history.yml")

        #Check preprocessing
        top_lvl_info=self.program_history.restore_arealdekke_attributes()

        #Update attributes
        if top_lvl_info["file_path"] is not None and top_lvl_info["preprocessings_completed"]>0:
            self.files["arealdekke_fc"] = top_lvl_info["file_path"]
        else:
            # Extracts the data and saves it in the object
            arcpy.management.CopyFeatures(
                in_features=input_n10.Arealdekke_Buskerud,
                out_feature_class=self.files["arealdekke_fc"],
            )
        
        #TODO HELE BITEN MÅ ENDRES FOR AT MAN IKKE SKAL LEGGE TIL FILSTI BARE FORDI DEN VAR DER I SISTE KJØRING.
        self.__preprocessed: bool = top_lvl_info["preprocessed"] or False
        self.__preprocessings_completed: int = top_lvl_info["preprocessings_completed"] or 0
        self.__map_scale: str = top_lvl_info["map_scale"] or map_scale

        #Get categories
        cat_lvl_info: dict =self.program_history.restore_arealdekke_categories()

        self.categories: list[Category] = cat_lvl_info["cats"] or [Category]

            
    # ========================
    # Main functions
    # ========================

    @timing_decorator
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

        # TODO: LEGG TIL IF NOT PROCESSED DONE

        # Pipeline from original orchistrator file. Preprocessing the arealdekke data.
        for preprocess in range((
            self.__preprocessings_completed if self.__preprocessings_completed==0 else (self.__preprocessings_completed+1)
            ), len(preprocesses), 1):

            #Call process
            preprocesses[preprocess]()

            #Update __preprocessings_completed
            self.__preprocessings_completed+=1

            #Update history (operations completed)
            self.program_history.update_history_top_lvl(
                key="preprocessing_operations_completed",
                value=self.__preprocessings_completed
            )
            
        arcpy.management.CopyFeatures(
            in_features=output_fc, out_feature_class=self.files["arealdekke_fc"]
        )

        self.__preprocessed = True

    def add_categories(self, categories_config_file):

        # Checks if the data has been preprocessed.
        if self.__preprocessed and not self.categories:

            try:
                with open(categories_config_file, "r", encoding="utf-8") as yml:
                    python_structured = yaml.safe_load(yml)

                    for category in python_structured["Categories"]:

                        # Extracts the data from the yml file into a category object.
                        category_obj = Category(**category)

                        # Adds it to the categories list/array if it has the same map scale as arealdekke.
                        if category_obj.get_map_scale() == self.__map_scale:
                            self.categories.append(category_obj)

                        #Adds category to the history file
                        self.program_history.new_history_category(
                            title=category_obj.get_title(),
                            operations=category_obj.get_operations(),
                            accessibility=category_obj.get_accessibility(),
                            order=category_obj.get_order(),
                            map_scale=category_obj.get_map_scale()
                        )

                # Sorts the categories based on their order key.
                self.categories.sort(key=lambda obj: obj.get_order())

            except Exception as e:
                raise e

    def process_categories(self) -> None:
        # Iterates through the categories that are true, meaning they are open.
        for category in list(
            filter(lambda cat: cat.get_accessibility(), self.categories)
        ):
            # Get the locked layers and the input layer
            self.get_locked_categories()
            self.get_category(category.get_title())

            # Iterates through operations for each category
            cat_operations=category.get_operations()

            if cat_operations:
                
                # Process category.
                for operation in category.process_category(
                    input_data=self.files["category_fc"],
                    locked_layers=self.files["locked_fc"],
                    processed_layer=self.files["processed_fc"],
                    program_history=self.program_history
                ):
                    for key, value in operation:
                        self.program_history.update_history_cat_lvl(
                            key=key,
                            value=value
                        )
                    
                # Add the category back into the input layer.
                remove_overlaps(
                    input_fc=self.files["arealdekke_fc"],
                    buffered_fc=self.files["processed_fc"],
                    locked_fc=self.files["locked_fc"],
                    output_fc=self.files["intermediate_fc"],
                    changed_area=category.get_title(),
                )

                fill_holes(
                    input_fc=self.files["intermediate_fc"],
                    output_fc=self.files["intermediate_fixed_fc"],
                    target=category.get_title(),
                    locked_categories=set(
                        map(
                            lambda cat: cat.get_title(),
                            filter(
                                lambda cat: not cat.get_accessibility(), self.categories
                            ),
                        )
                    ),
                )

                arcpy.management.CopyFeatures(
                    in_features=self.files["intermediate_fixed_fc"],
                    out_feature_class=self.files["arealdekke_fc"],
                )

            # Lock the layer
            category.set_accessibility(False)

            self.program_history.update_history_cat_lvl(
                title=category.get_title(),
                key="accessibility",
                value=category.get_accessibility()
            )

        # Save processed data to final fc and delete the last files
        arcpy.management.CopyFeatures(
            in_features=self.files["arealdekke_fc"],
            out_feature_class=Arealdekke_N10.arealdekke_class_final__n10_land_use.value,
        )

        self.wfm.delete_created_files()

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