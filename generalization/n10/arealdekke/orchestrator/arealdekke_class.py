#Module imports:
import arcpy
import yaml
from composition_configs import core_config
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n10.arealdekke.orchestrator.category_class import Category

#Arealdekke tools:
from generalization.n10.arealdekke.overall_tools.arealdekke_dissolver import (partition_call as arealdekke_dissolver,)
from generalization.n10.arealdekke.overall_tools.gangsykkel_dissolver import (partition_call as gangsykkel_dissolver,)
from generalization.n10.arealdekke.overall_tools.eliminate_small_polygons import (partition_call as eliminate_small_polygons,)
from generalization.n10.arealdekke.attribute_changer import attribute_changer
from generalization.n10.arealdekke.overall_tools.island_controller import island_controller
from generalization.n10.arealdekke.orchestrator.expansion_controller import simplify_and_expand_land_use

arcpy.env.overwriteOutput = True

class Arealdekke:


    def __init__(self, input_data, min_criteria)->None:
        
        #Setting up file manager
        self.working_fc = Arealdekke_N10.buffed_polygon_segments__n10_land_use.value
        self.config = core_config.WorkFileConfig(root_file=self.working_fc)
        self.wfm = WorkFileManager(config=self.config)

        #Extracts the data and saves it in the object
        self.arealdekke_data = self.wfm.build_file_path(file_name="arealdekke", file_type="gdb")
        arcpy.management.CopyFeatures(in_features=input_data, out_feature_class=self.arealdekke_data)

        #Creates a variable to see if the data has been preprocessed.
        #Safety lock to make sure categories are not added before data is ok.
        self.preprocessed=False

        #Criteria to the arealdekke
        self.min_criteria=min_criteria
        self.MAP_SCALE="N10" #This should be in min_criteria yml file


    # ========================
    # Main functions
    # ========================


    def preprocess(self)->None:
        
        #Pipeline from original orchistrator file. Preprocessing the arealdekke data.
        attribute_changer(
            input_fc=self.arealdekke_data,
            output_fc=Arealdekke_N10.attribute_changer_output__n10_land_use.value,
        )

        arealdekke_dissolver(
            input_fc=Arealdekke_N10.attribute_changer_output__n10_land_use.value,
            output_fc=Arealdekke_N10.dissolve_arealdekke.value,
            map_scale=self.MAP_SCALE,
        )

        island_controller(
            input_fc=Arealdekke_N10.dissolve_arealdekke.value,
            output_fc=Arealdekke_N10.island_merger_output__n10_land_use.value,
        )

        eliminate_small_polygons(
            input_fc=Arealdekke_N10.island_merger_output__n10_land_use.value,
            output_fc=Arealdekke_N10.elim_output.value,
            map_scale=self.MAP_SCALE,
        )
        
        gangsykkel_dissolver(
            input_fc=Arealdekke_N10.elim_output.value,
            output_fc=Arealdekke_N10.dissolve_gangsykkel.value,
            map_scale=self.MAP_SCALE,
        )

        simplify_and_expand_land_use(
            input_fc=Arealdekke_N10.dissolve_gangsykkel.value,
            output_fc=Arealdekke_N10.expansion_controller_output__n10_land_use.value,
        )

        self.preprocessed=True


    def add_categories(self, categories_config_file)->bool:
        
        completed=False

        #Checks if the data has been preprocessed.
        if self.preprocessed:
            
            #List with all categories in arealdekke.
            self.categories=[]

            try:    
                with open(categories_config_file,"r", encoding="utf-8") as yml:
                    python_structured=yaml.safe_load(yml)

                    for category in python_structured["Categories"]:
                        
                        #Extracts the data from the yml file into a category object.
                        category_obj = Category(**category)

                        #Adds it to the categories list/array.
                        self.categories.append(category_obj)

                #Sorts the categories based on their order key.
                self.categories.sort(key=lambda obj: obj.get_order())
                
                #Updates completed variable.
                completed=True

            except Exception as e:
                raise e
        
        #Returns status of completion to user.
        return completed


    def process_categories(self)->None:

        #Iterates through the categories that are true, meaning they are open.
        for category in list(filter(lambda cat: cat.get_accessibility(), self.categories)):
            
            #Get the locked layers and the input layer
            currently_locked_layers="currently_locked_layers"
            open_layer="open_layer"

            self.get_locked_categories(currently_locked_layers)
            self.get_category(category.get_title(), open_layer)

            #Layer that will save the output.
            processed_layer="processed_layer"

            #Process category.
            reinsert=category.process_category(
                input_data=open_layer,
                locked_layers=currently_locked_layers,
                processed_layer=processed_layer
                )

            if reinsert:
                #Add the category back into the input layer.
                self.add_back_to_lyr(processed_layer)
            
            #Lock the layer
            category.set_accessibility(True)

            #Delete the output layer (just in case).
            del processed_layer
    
    
    def add_back_to_lyr(self, output)->None:
        pass
                    

    # ========================
    # Getters
    # ========================


    def get_locked_categories(self, locked_lyr)->None:

        #List of titles of locked categories.
        locked_categories_titles=set()

        for category in self.categories:
            if not category.get_accessibility():
                locked_categories_titles.add(category.get_title())

        #Creates new layer with all the locked features
        arcpy.management.MakeFeatureLayer(
            in_features=self.arealdekke_data, 
            out_layer=locked_lyr,
            where_clause=f"arealdekke IN {tuple(locked_categories_titles)}")
    

    def get_category(self, category_title:str, open_lyr)->None:

        #Extracts categorical data from arealdekke into feature layer
        arcpy.management.MakeFeatureLayer(self.arealdekke_data, open_lyr, where_clause=f"arealdekke='{category_title}'")   


    # ========================
    # Setters
    # ========================


    def set_arealdekke_input(self, new_data)->None:
        self.arealdekke_data=new_data