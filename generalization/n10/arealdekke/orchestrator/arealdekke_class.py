import arcpy
from category_class import Category
import yaml

from arealdekke.island_controller import island_controller
from arealdekke.buff_small_polygon_segments import buff_small_polygon_segments

from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator

class Arealdekke:

    def __init__(self, input_data)->None:
        self.arealdekke_data = input_data
        
        self.tools={"remove_islands": island_controller, "buff_small_segments":buff_small_polygon_segments}



    def add_categories(self, categories_config_file)->None:
        self.categories=[]

        try:    
            with open(categories_config_file,"r", encoding="utf-8") as yml:
                python_structured=yaml.safe_load(yml)

                for category in python_structured["Categories"]:
                    
                    #Extracts the data from the yml file into a category object
                    category_obj = Category(**category)

                    #Adds it to the categories list/array.
                    self.categories.append(category_obj)

            #Sorts the categories based on their order key.
            self.categories.sort(key=lambda obj: obj.get_order())

        except Exception as e:
            raise e



    def get_locked_categories(self)->list:
        #Returns list of titles of locked categories.

        locked_categories_titles=set()

        for category in self.categories:
            if not category.get_accessibility():
                locked_categories_titles.add(category.get_title())

        return locked_categories_titles



    def set_arealdekke_input(self, new_data)->None:
        self.arealdekke_data=new_data



    def process_categories(self)->None:
        
        for category in self.categories:

            if category.get_accessibility:
                #Retrieves the currently locked categories
                currently_locked=self.get_locked_categories()

                #Iterates through the operations needed for each category
                if operation:
                    for operation in category.get_operations():
                        
                        #Checks if each operation is written correctly (test can be improved later)
                        if operation not in self.tools:
                            raise f"Incorrect syntax in yml file. Object:{category.__str__()}"
                        
                        else:
                            self.tools[operation](
                                currently_locked,
                                input_fc,
                                output_fc,
                                criteria_yml_file
                            )

                    #Add the category back into the input layer
                    