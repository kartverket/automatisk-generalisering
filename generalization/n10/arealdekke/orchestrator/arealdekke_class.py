# Module imports:
import arcpy
import yaml
from pathlib import Path
from custom_tools.decorators.timing_decorator import timing_decorator
from composition_configs import core_config
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n10.arealdekke.orchestrator.category_class import Category
from generalization.n10.arealdekke.orchestrator.program_history_class import (
    Program_history_class as History_class,
)
from generalization.n10.arealdekke.orchestrator.enum_variables import (
    history_keys as keys,
)

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
    postprocess_passability_layer,
)
from generalization.n10.arealdekke.overall_tools.overlap_remover import (
    remove_overlaps,
)
from generalization.n10.arealdekke.overall_tools.fill_holes import fill_holes
from generalization.n10.arealdekke.overall_tools.small_features_changer import (
    change_attribute_value_main,
)

arcpy.env.overwriteOutput = True


class Arealdekke:

    def __init__(self, input_data: str, map_scale: str) -> None:

        '''
        What:
        Object initialisation. Collects data from the history file connected to the class, 
        and loads the content into the new object if it meets some criteria:
        
        1. The file path to The history file must have existed before program start.
        2. The arealdekke preprocess must have completed at least one operation during previous run.
        
        This load does not include the arealdekke categories. They will be added from the history 
        file if:
        1. All preprocessing is completed.
        2. At least one category processing was completed.
        
        After categories from the history file are loaded into category objects, the program will
        not allow more category objects to be added.

        Dictionary with file paths used throughout the pipeline is created. Additionally, variables 
        directing to arealdekke file manager for preserving the final output are established.
    '''

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

        self.program_history: History_class = History_class(
            file_path=Path(__file__).parent / "arealdekke_history.yml"
        )

        top_lvl_info: dict = self.program_history.restore_arealdekke_attributes()

        if (
            top_lvl_info["file_path"] is not None
            and top_lvl_info[keys.preprocessing_operations_completed.value] is not None
            and top_lvl_info[keys.preprocessing_operations_completed.value] > 0
        ):

            self.files["arealdekke_fc"] = top_lvl_info["file_path"]

            self.__preprocessed: bool = top_lvl_info.get(keys.preprocessed.value, False)
            self.__preprocesses_completed: int = top_lvl_info[
                keys.preprocessing_operations_completed.value
            ]
            self.__postprocesses_completed: int = top_lvl_info[
                keys.postprocessing_operations_completed.value
            ]
            self.__map_scale: str = (
                top_lvl_info.get(keys.map_scale.value, None) or map_scale
            )

        else:

            self.get_arealdekke_data(input_data=input_data)

            self.program_history.update_history_top_lvl(
                key=keys.newest_version.value, value=str(self.files["arealdekke_fc"])
            )

            self.__preprocessed: bool = False
            self.__preprocesses_completed: int = 0
            self.__postprocesses_completed: int = 0
            self.__map_scale: str = map_scale or None

        cat_lvl_info: dict = self.program_history.restore_arealdekke_categories()

        self.categories: list[Category] = cat_lvl_info.get("cats", None) or []

        if cat_lvl_info["cats_exist"]:

            category: Category
            for category in cat_lvl_info["cats"]:
                last_processed = category.get_last_processed()

                if (
                    (last_processed is not None)
                    and (
                        len(category.get_operations())
                        == category.get_operations_completed()
                    )
                    and (
                        category.get_reinserts_completed()
                        < self.get_num_postprocessors()
                    )
                ):
                    arcpy.management.CopyFeatures(
                        in_features=last_processed,
                        out_feature_class=self.files["processed_fc"],
                    )
                    break

        self.final_categories_fc = (
            Arealdekke_N10.arealdekke_processed_categories__n10_land_use.value
        )
        self.final_output_fc = Arealdekke_N10.arealdekke_class_final__n10_land_use.value

    # ========================
    # Main functions
    # ========================

    @timing_decorator
    def preprocess(self) -> None:
        
        '''
        What:
	        Iterates through the preprocess operations defined in set_preprocesses in arealdekke.
            After each operation completion, the preprocessing_operations_completed field in the 
            history file is updated. Once all operations are done, preprocessed is set to True 
            in the history file and within the arealdekke object.
        '''

        preprocesses = self.set_preprocesses()

        output_fc = Arealdekke_N10.dissolve_gangsykkel.value

        if not self.__preprocessed:
            for preprocess in range(
                (self.__preprocesses_completed), len(preprocesses), 1
            ):

                preprocesses[preprocess]()
                self.__preprocesses_completed += 1

                self.program_history.update_history_top_lvl(
                    key=keys.preprocessing_operations_completed.value,
                    value=self.__preprocesses_completed,
                )

            arcpy.management.CopyFeatures(
                in_features=output_fc, out_feature_class=self.files["arealdekke_fc"]
            )

            self.__preprocessed = True

            self.program_history.update_history_top_lvl(
                key=keys.preprocessed.value, value=True
            )

    @timing_decorator
    def add_categories(self, categories_config_file: Path) -> None:

        '''
        What:
	        Checks if preprocessing is completed and category processing has not begun.
            When true, arealdekke_categories_config is opened, made into category objects 
            and saved to Arealdekke's categories array. 
            
            *Note that only categories with corresponding map_scale to arealdekke are added
            and registered in the history file. 
            
            After all categories are added, all category objects are sorted based on their 
            order attribute. Ideally, this key should be unique. If not, the categories 
            in question will be sorted alphabetically.
        '''

        if self.__preprocessed and not self.categories:
            self.program_history.update_history_top_lvl(
                key=keys.category_history.value, value=[]
            )

            try:
                with open(categories_config_file, "r", encoding="utf-8") as yml:
                    python_structured = yaml.safe_load(yml)

                    for category in python_structured["Categories"]:

                        category_obj = Category(**category)

                        if category_obj.get_map_scale() == self.__map_scale:
                            self.categories.append(category_obj)

                            self.program_history.new_history_category(
                                title=category_obj.get_title(),
                                operations=category_obj.get_operations(),
                                accessibility=category_obj.get_accessibility(),
                                order=category_obj.get_order(),
                                map_scale=category_obj.get_map_scale(),
                            )

                self.categories.sort(key=lambda obj: obj.get_order())

            except Exception as e:
                raise e

    @timing_decorator
    def process_categories(self) -> None:

        '''
        What:
	        Iterates through categories that are open (accessibility=True). For each 
            category, title is collected and category_fc and locked_fc within files 
            dictionary is updated to fit. Program checks if the category has 
            operations registered, and iterates through the operations if true. Each 
            operation yields data used to update the program history file. 
            
            Once the iteration is done, the program collects the titles of the locked 
            categories and how many reinsert operations have been completed. This is
            used to reinsert the processed category back into the arealdekke. Lastly, 
            the category is locked (accessibility=False).

            When all categories are processed and locked, the arealdekke_fc is copied
            to another path and all the paths in the files dictionary are deleted.
        '''

        open_cats = list(filter(lambda cat: cat.get_accessibility(), self.categories))

        for category in open_cats:
            cat_title = category.get_title()
            self.get_locked_categories()
            self.get_category(cat_title)

            cat_operations = category.get_operations()

            if cat_operations:

                for operation in category.process_category(
                    input_fc=self.files["category_fc"],
                    locked_fc=self.files["locked_fc"],
                    processed_fc=self.files["processed_fc"],
                ):
                    for key, value in operation.items():
                        self.program_history.update_history_cat_lvl(
                            title=cat_title, key=key, value=value
                        )

                reinserts_completed = category.get_reinserts_completed()

                locked_cat_titles = self.get_locked_categories_titles()

                reinsert_operations = [
                    lambda: remove_overlaps(
                        input_fc=self.files["arealdekke_fc"],
                        buffered_fc=self.files["processed_fc"],
                        locked_fc=self.files["locked_fc"],
                        output_fc=self.files["intermediate_fc"],
                        changed_area=cat_title,
                    ),
                    lambda: fill_holes(
                        input_fc=self.files["arealdekke_fc"],
                        output_fc=self.files["intermediate_fc"],
                        target=cat_title,
                        locked_categories=locked_cat_titles,
                    ),
                ]

                for index in range(reinserts_completed, len(reinsert_operations)):

                    reinsert_operations[index]()

                    arcpy.management.CopyFeatures(
                        in_features=self.files["intermediate_fc"],
                        out_feature_class=self.files["arealdekke_fc"],
                    )

                    self.program_history.update_history_top_lvl(
                        key=keys.newest_version.value,
                        value=str(self.files["arealdekke_fc"]),
                    )

                    reinserts_completed_updated = (
                        category.update_reinsert_operations_completed()
                    )

                    self.program_history.update_history_cat_lvl(
                        title=cat_title,
                        key=keys.reinserts_completed.value,
                        value=reinserts_completed_updated,
                    )

            category.set_accessibility(False)

            self.program_history.update_history_cat_lvl(
                title=cat_title,
                key=keys.accessibility.value,
                value=category.get_accessibility(),
            )

        if open_cats:
            arcpy.management.CopyFeatures(
                in_features=self.files["arealdekke_fc"],
                out_feature_class=self.final_categories_fc,
            )

            self.program_history.update_history_top_lvl(
                key=keys.newest_version.value, value=str(self.final_categories_fc)
            )

        self.wfm.delete_created_files()

    @timing_decorator
    def finish_results(self) -> None:
        
        '''
        What:
            Performes a final clean-up of the results by adjusting any misalignments of geometries.
        '''
        postprocesses = self.set_postprocesses()

        for process in range(self.__postprocesses_completed, len(postprocesses), 1):
            postprocesses[process]()

            self.__postprocesses_completed += 1

            self.program_history.update_history_top_lvl(
                key=keys.postprocessing_operations_completed.value,
                value=self.__postprocesses_completed,
            )

        self.program_history.delete_history()

    # ========================
    # Getters
    # ========================

    def get_map_scale(self) -> str:
        return self.__map_scale

    def get_locked_categories(self) -> None:

        locked_categories_titles = set()

        for category in self.categories:
            if not category.get_accessibility():
                locked_categories_titles.add(category.get_title())

        if locked_categories_titles:
            values = ", ".join([f"'{v}'" for v in locked_categories_titles])
            where_clause = f"arealdekke IN ({values})"
        else:
            where_clause = (
                "1=0"  # No categories are locked, so we create an empty layer.
            )

        temp_lyr = "temp_lyr"

        arcpy.management.MakeFeatureLayer(
            in_features=self.files["arealdekke_fc"],
            out_layer=temp_lyr,
            where_clause=where_clause,
        )

        arcpy.management.CopyFeatures(
            in_features=temp_lyr, out_feature_class=self.files["locked_fc"]
        )

    def get_category(self, category_title: str) -> None:

        temp_lyr = "temp_lyr"

        arcpy.management.MakeFeatureLayer(
            in_features=self.files["arealdekke_fc"],
            out_layer=temp_lyr,
            where_clause=f"arealdekke='{category_title}'",
        )

        arcpy.management.CopyFeatures(
            in_features=temp_lyr, out_feature_class=self.files["category_fc"]
        )

    def get_arealdekke_data(self, input_data: str) -> None:
        arcpy.management.CopyFeatures(
            in_features=input_data,
            out_feature_class=self.files["arealdekke_fc"],
        )

    def get_locked_categories_titles(self) -> set:
        return set(
            map(
                lambda cat: cat.get_title(),
                filter(
                    lambda cat: not cat.get_accessibility(),
                    self.categories,
                ),
            )
        )

    def get_num_postprocessors(self) -> int:
        return len(self.set_postprocesses())

    def __str__(self) -> str:
        return (
            f"preprocessed: {self.__preprocessed} "
            + f"preprocessings completed: {self.__preprocesses_completed} "
            + f"map scale: {self.__map_scale}"
        )

    # ========================
    # Setters
    # ========================

    def set_preprocesses(self) -> list:
        return [
            lambda: attribute_changer(
                input_fc=self.files["arealdekke_fc"],
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
            lambda: change_attribute_value_main(
                working_fc=Arealdekke_N10.elim_output.value,
            ),
            lambda: gangsykkel_dissolver(
                input_fc=Arealdekke_N10.elim_output.value,
                output_fc=Arealdekke_N10.dissolve_gangsykkel.value,
                map_scale=self.__map_scale,
            ),
        ]

    def set_postprocesses(self) -> list:
        return [
            lambda: postprocess_passability_layer(
                final_fc=self.final_categories_fc,
                passability_fc=Arealdekke_N10.passability__n10_land_use.value,
            ),
            lambda: arealdekke_dissolver(
                input_fc=self.final_categories_fc,
                output_fc=self.final_output_fc,
                map_scale=self.__map_scale,
            ),
        ]
