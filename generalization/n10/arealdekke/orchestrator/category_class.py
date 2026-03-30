import arcpy

class Category:

    def __init__(self, title:str, operations:list, accessibility:bool, order:int):
        self.title = title
        self.operations = [operations]
        self.accessibility = accessibility
        self.order = order

    # ========================
    # Setters
    # ========================

    def set_layer(self, arealdekke_data)->None:
        self.open_lyr=f"{self.title}_lyr"
        arcpy.management.MakeFeatureLayer(arealdekke_data, self.open_lyr, where_clause=f"arealdekke='{self.title}'")

    
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
    

    # ========================
    # Generalisation tools
    # ========================

    def buff_segments(self):
        fsfs
    
    def __str__(self)->str:
        return(
            f"Category(title='{self.title}', "
            f"accessibility={self.accessibility}, "
            f"order={self.order})"
        )