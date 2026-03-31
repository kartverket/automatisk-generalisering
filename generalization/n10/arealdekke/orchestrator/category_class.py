#Module imports:
import arcpy
from composition_configs import core_config
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10

#Category tools:
from generalization.n10.arealdekke.overall_tools.island_controller import island_controller
from generalization.n10.arealdekke.category_tools.buff_small_polygon_segments import buff_small_polygon_segments


class Category:

    def __init__(self, title:str, operations:list, accessibility:bool, order:int):

        #Extracts inputs and saves them within object
        self.title = title
        self.operations = [operations]
        self.accessibility = accessibility
        self.order = order


        #Dictionary with all tools available to the category objects
        self.cat_tools = {
            "remove_islands": island_controller, 
            "buff_small_segments":buff_small_polygon_segments
            }
        
        for operation in self.operations:
            
            #Checks if each operation is written correctly (test can be improved later)
            if operation not in self.cat_tools:
                raise f"Incorrect syntax in yml file. Object:{self.title}"
            
        #Creates layer for the category. Data inserted into it in setter function.
        self.lyr=f"{self.title}_lyr"

    
    # ========================
    # Main functions
    # ========================


    def process_category(
            self,
            input_data:str,
            locked_layers:str,
            processed_layer:str
            )->bool:

        reinsert=False

        #File that will be overwritten with new input for each iteration.
        output_lyr=f"{self.title}_output_lyr"

        if self.operations:
            #Inserts the arealdekke input data into the layer.
            self.set_layer(input_data)

            #Iterates through the operations needed for each category.
            for operation in self.operations:
                
                #Calls function from dictionary
                self.cat_tools[operation](
                    self.title,
                    self.lyr,
                    locked_layers,
                    output_lyr,
                    self.min_criteria
                    )
                
                #Updates the layer that will be passed on to the next operation to be the output.
                self.set_lyr(output_lyr)

            #Marks the process as completed and insert the final layer into the output layer.
            reinsert=True
            arcpy.management.MakeFeatureLayer(in_features=self.lyr, out_layer=processed_layer)
        
        #Once done, return if the layer should be reinserted into arealdekke.
        return reinsert
                

    # ========================
    # Setters
    # ========================


    def set_layer(self, data)->None:

        #Extracts data into feature layer initiated in object init
        arcpy.management.MakeFeatureLayer(data, self.lyr)   

    
    def set_accessibility(self, newStatus:bool)->None:
        self.accessibility=newStatus
    

    # ========================
    # Getters
    # ========================

    def get_title(self)->str:
        return self.title


    def get_order(self)->int:
        return self.order


    def get_accessibility(self)->bool:
        return self.accessibility


    def get_operations(self)->list:
        return self.operations
    

    def __str__(self)->str:
        return(
            f"Category(title='{self.title}', "
            f"accessibility={self.accessibility}, "
            f"order={self.order})"
        )