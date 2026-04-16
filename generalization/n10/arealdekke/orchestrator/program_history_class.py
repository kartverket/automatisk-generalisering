import yaml
import os
from pathlib import Path
from generalization.n10.arealdekke.orchestrator.category_class import Category

class Program_history_class:
    def __init__(self, file_path):

        self.__program_history_path: Path = Path(file_path)

        #Check if the program history exists. Creates new file if it does not.
        if not self.__program_history_path.is_file():
            self.reset_history()
            self.new_history_created: bool = True
        else:
            self.new_history_created: bool = False

    # ========================
    # Getters
    # ========================
    def get_new_history_created(self)->bool:
        return self.new_history_created

    def get_history_attribute_top_lvl(self, key):
        history=self.load_history()
        return history[key]
    
    def get_history_attribute_cat_lvl(self, title, key):
        history=self.load_history()
        
        for cat in history["category_history"]:
            if cat["title"] == title:
                return cat[key]


    def restore_arealdekke_attributes(self):
        history=self.load_history()

        # Check how far the preprocessing got. If at least one process was
        # completed, update paths etc.

        response: dict ={}

        if history.get("preprocessing_operations_completed", 0)>0:
            response["file_path"] = history["newest_version"]
            response["preprocessed"] = history["preprocessed"]
            response["preprocessing_operations_completed"] = history["preprocessing_operations_completed"]
            response["map_scale"] = history["map_scale"]
        

        return response
    
    def restore_arealdekke_categories(self):
        #Restores list of categories and true if categories have been added and processing have started.
        history =self.load_history()
        preprocessed=history["preprocessed"]
        cat_history=history.get("category_history", [])

        response={}

        if (
            preprocessed and
            cat_history and
            cat_history[0]["operations_completed"]
        ):
            # Extracts the data from the yml file into a category object.
            response["cats_exist"]=True
            response["cats"]=[]

            for category in history["category_history"]:
                category_obj = Category(**category)
                response["cats"].append(category_obj)
        
        else:
            response["cats_exist"]=False
        
        return response

    # ========================
    # Setters
    # ========================

    def save_history(self, data):
        with open(self.__program_history_path, "w") as file:
            yaml.dump(data, file, default_flow_style=False, allow_unicode=True)

    def load_history(self):
        with open(self.__program_history_path) as file:
            return yaml.safe_load(file)
        
    def update_history_top_lvl(self, key, value):
        data=self.load_history()
        data[key]=value
        self.save_history(data)

    def update_history_cat_lvl(self, title, key, value):
        data=self.load_history()
  
        for cat in data["category_history"]:
            if cat["title"] == title:
                cat[key] = value
                self.save_history(data)
                break

    def new_history_category(
            self, 
            title, 
            operations, 
            accessibility=True, 
            order=None,
            map_scale="N10"
            ):
        
        data = self.load_history()
        history = data["category_history"]

        new_entry = {
            "title": title,
            "operations": operations,
            "accessibility": accessibility,
            "order": order,
            "map_scale": map_scale,
            "last_processed": None,
            "operations_completed": 0,
        }

        history.append(new_entry)
        self.save_history(data)

    def reset_history(self):

        template = {
            "newest_version": None,
            "map_scale": None,
            "preprocessed": False,
            "preprocessing_operations_completed": 0,
            "category_history": []
        }

        data=template
        self.save_history(data) 