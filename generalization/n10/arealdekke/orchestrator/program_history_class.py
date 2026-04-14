import yaml
import os
from pathlib import Path
from generalization.n10.arealdekke.orchestrator.category_class import Category

class Program_history_class:
    def __init__(self, file_path)->bool:

        self.__program_history_path=file_path

        #Check if the program history exists. Creates new file if it does not.
        if not Path.is_file():
            self.reset_history()
            
            #Returns false if a new file was created.
            return False
        else:
            return True

    # ========================
    # Getters
    # ========================


    def restore_arealdekke_attributes(self):
        history=self.load_history()

        # Check how far the preprocessing got. If at least one process was
        # completed, update paths etc.
        response={}

        if history.get("preprocessing_operations_completed", 0)>0:
            response["update"]=True
            response["file_path"] = history["newest_version"]
            response["preprocessed"] = history["preprocessed"]
            response["preprocessings_completed"] = history["preprocessings_completed"]
            response["map_scale"] = history["map_scale"]
            
        else:
            response["update"]=True

        return response
    
    def restore_arealdekke_categories(self):
        #Restores list of categories and true if categories have been added and processing have started.
        history=self.load_history()
        preprocessed=history["preprocessed"]
        cat_history=history.get("category_history", [])

        response={}

        if (
            preprocessed and
            cat_history and
            cat_history[0]["operations_completed"]
        ):
            # Extracts the data from the yml file into a category object.
            response["cats_exists"]=True
            response["cats"]=[]

            for category in history["category_history"]:
                category_obj = Category(**category)
                response["cats"].append(category_obj)
        
        else:
            response["cats_exists"]=False
        
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
                break
        self.save(data)

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
            "operations_completed": None,
        }

        history.append(new_entry)
        self.save_history(data)

    def reset_history(self):

        template = {
            "newest_version": None,
            "map_scale": None,
            "preprocessed": None,
            "preprocessing_operations_completed": None,
            "category_history": []
        }

        data=template
        self.save(data)